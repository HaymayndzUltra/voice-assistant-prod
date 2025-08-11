#!/usr/bin/env python3
"""
sync_inventory.py — Reconcile local Docker images with GHCR for a user.

Capabilities (safe by default):
- Dry-run (default): list missing remote tags and digest mismatches for ghcr.io/<user>/* images
- Optional: push missing local tags to GHCR when --push-missing is provided

Auth assumptions:
- Env GH_USERNAME and GH_TOKEN (GitHub PAT with read:packages, write:packages)
- We will exchange PAT for a registry bearer token for GHCR manifest access

Usage examples:
  GH_USERNAME=haymayndzultra GH_TOKEN=ghp_xxx \
  python3 scripts/sync_inventory.py --dry-run

  GH_USERNAME=haymayndzultra GH_TOKEN=ghp_xxx \
  python3 scripts/sync_inventory.py --push-missing
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error


def run(cmd: List[str]) -> Tuple[int, str, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return p.returncode, p.stdout, p.stderr


def docker_login(username: str, token: str) -> bool:
    code, _, _ = run(["docker", "logout", "ghcr.io"])
    p = subprocess.Popen(["docker", "login", "ghcr.io", "-u", username, "--password-stdin"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(token + "\n")
    return p.returncode == 0


def get_local_images(username: str) -> Dict[Tuple[str, str], Dict[str, str]]:
    res: Dict[Tuple[str, str], Dict[str, str]] = {}
    code, out, err = run([
        "docker", "image", "ls", "--all", "--digests", "--no-trunc", "--format", "{{json .}}",
    ])
    if code != 0:
        return res
    for line in out.splitlines():
        try:
            obj = json.loads(line)
        except Exception:
            continue
        repo = (obj.get("Repository") or "").strip()
        tag = (obj.get("Tag") or "").strip()
        if not repo or repo == "<none>" or not tag or tag == "<none>":
            continue
        if not repo.startswith(f"ghcr.io/{username}/"):
            continue
        # Resolve digest via inspect RepoDigests
        digest = ""
        code2, out2, _ = run(["docker", "inspect", "--format", "{{json .RepoDigests}}", f"{repo}:{tag}"])
        if code2 == 0:
            try:
                arr = json.loads(out2.strip())
                if isinstance(arr, list):
                    for rd in arr:
                        if rd.startswith(repo + "@"):  # exact repo match
                            digest = rd.split("@", 1)[1]
                            break
                    if not digest and arr:
                        digest = arr[0].split("@", 1)[1]
            except Exception:
                pass
        res[(repo, tag)] = {"digest": digest}
    return res


def fetch_registry_token(username: str, pat: str, repo_path: str) -> Optional[str]:
    url = f"https://ghcr.io/token?service=ghcr.io&scope=repository:{repo_path}:pull"
    basic = base64.b64encode(f"{username}:{pat}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Basic {basic}",
        "Accept": "application/json",
        "User-Agent": "sync-inventory-script",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("token") or data.get("access_token")
    except Exception:
        return None


def get_remote_digest(username: str, package: str, tag: str, token: str) -> Optional[str]:
    repo_path = f"{username}/{package}"
    accept = ", ".join([
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ])
    url = f"https://ghcr.io/v2/{repo_path}/manifests/{tag}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "User-Agent": "sync-inventory-script",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            # Prefer Docker-Content-Digest header if present
            headers = {k: v for k, v in resp.getheaders()}
            digest = headers.get("Docker-Content-Digest")
            return digest
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return None
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile local Docker images with GHCR")
    parser.add_argument("--username", default=os.environ.get("GH_USERNAME", ""))
    parser.add_argument("--token", default=os.environ.get("GH_TOKEN", ""))
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--push-missing", action="store_true", default=False)
    args = parser.parse_args()

    username = args.username.strip()
    token = args.token.strip()
    dry_run = args.dry_run or (not args.push_missing)

    if not username or not token:
        print("Missing GH_USERNAME or GH_TOKEN", file=sys.stderr)
        return 2

    # Optional login for pushes
    if args.push_missing:
        if not docker_login(username, token):
            print("docker login ghcr.io failed", file=sys.stderr)
            return 3

    local = get_local_images(username)
    missing: List[str] = []
    mismatched: List[Tuple[str, str, str]] = []  # (ref, local_digest, remote_digest)

    for (repo, tag), info in sorted(local.items()):
        package = repo.split("/", 3)[-1]  # ghcr.io/<user>/<package>
        repo_path = f"{username}/{package}"
        reg_token = fetch_registry_token(username, token, repo_path)
        remote_digest = get_remote_digest(username, package, tag, reg_token) if reg_token else None
        ref = f"{repo}:{tag}"
        local_digest = (info.get("digest") or "").strip()

        if remote_digest is None:
            missing.append(ref)
        else:
            # Compare if both available
            if local_digest and remote_digest and (local_digest != remote_digest):
                mismatched.append((ref, local_digest, remote_digest))

    print(f"Local tracked ghcr images: {len(local)}")
    print(f"Missing on GHCR: {len(missing)}")
    print(f"Digest mismatches: {len(mismatched)}")

    if missing:
        print("\nMissing on GHCR:")
        for ref in missing:
            print(" -", ref)
        if args.push_missing and not dry_run:
            for ref in missing:
                code, out, err = run(["docker", "push", ref])
                if code != 0:
                    print(f"Push failed: {ref}: {err.strip()}", file=sys.stderr)

    if mismatched:
        print("\nDigest mismatches:")
        for ref, ld, rd in mismatched:
            print(f" - {ref}\n   local:  {ld}\n   remote: {rd}")
        print("\nRecommendation: rebuild with --no-cache and re-push, or align tags.")

    return 0


if __name__ == "__main__":
    sys.exit(main())