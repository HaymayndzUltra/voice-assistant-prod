#!/usr/bin/env python3
"""
Docker Image Inventory and Comparison Tool

Features:
- Enumerates local Docker images with columns: REPOSITORY, TAG, IMAGE ID, CREATED, SIZE, DIGEST (if available)
- Enumerates GHCR images for a GitHub user with same columns (IMAGE ID is N/A for remote)
- Compares LOCAL vs GHCR (same repo:tag in both, digest differences, only-in-local, only-in-GHCR)
- Lists images with same name but different tags
- Identifies unused images (local: not used by any container; GHCR: untagged versions)
- Outputs results as structured Markdown tables to a file

Usage:
  GH_USERNAME=<github_username> GH_TOKEN=<github_pat_with_read:packages> \
  python3 scripts/docker_inventory_compare.py --output docker_image_inventory.md

Notes:
- Requires Docker CLI available for local enumeration
- Uses stdlib urllib for API calls; no external deps required
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import urllib.request
import urllib.error
import base64


# ----------------------- Utilities -----------------------


def run_command(command: List[str], check: bool = False) -> Tuple[int, str, str]:
    """Run a shell command and return (code, stdout, stderr)."""
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as e:
        return 127, "", str(e)


def to_iso8601(created_at: str) -> str:
    """Best-effort parse of Docker/GitHub time strings to ISO8601 Z."""
    if not created_at:
        return ""
    # Common Docker format: '2024-08-09 10:19:50 +0000 UTC'
    s = created_at.strip()
    s = s.replace(" UTC", "")
    try:
        # Try with explicit tz offset
        dt_obj = dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z")
        return dt_obj.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    # Try ISO-like
    try:
        dt_obj = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt_obj.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    # Fallback: return original
    return created_at


def human_bytes(num_bytes: Optional[int]) -> str:
    if num_bytes is None:
        return "N/A"
    try:
        n = float(num_bytes)
    except Exception:
        return "N/A"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{int(n)}{units[i]}"
    return f"{n:.2f}{units[i]}"


def parse_http_date(s: str) -> Optional[str]:
    """Parse GitHub REST timestamps to ISO8601Z."""
    try:
        dt_obj = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt_obj.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def iso_to_datetime(s: str) -> Optional[dt.datetime]:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except Exception:
        return None


# ----------------------- Local Docker -----------------------


class LocalImage(Dict[str, Any]):
    pass


def _docker_available() -> bool:
    code, out, _ = run_command(["docker", "version", "--format", "{{json .}}"])
    return code == 0


def _extract_inspect_repo_digests(image_ref: str) -> List[str]:
    code, out, err = run_command(["docker", "inspect", "--format", "{{json .RepoDigests}}", image_ref])
    if code != 0:
        return []
    try:
        data = json.loads(out.strip())
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _choose_digest_for_repo(repo: str, repo_digests: List[str]) -> Optional[str]:
    # repo_digests are like 'ghcr.io/owner/name@sha256:...'
    for rd in repo_digests:
        if rd.startswith(repo + "@"):
            return rd.split("@", 1)[1]
    # fallback to first digest if any
    if repo_digests:
        return repo_digests[0].split("@", 1)[1]
    return None


def get_local_images() -> Tuple[List[LocalImage], List[str]]:
    """Return (local_images, used_image_ids)."""
    images: List[LocalImage] = []
    used_image_ids: List[str] = []

    if not _docker_available():
        return images, used_image_ids

    # Collect used image IDs by containers
    code, out, _ = run_command(["docker", "ps", "-aq"])
    container_ids = [cid for cid in out.strip().splitlines() if cid.strip()]
    used_set: set[str] = set()
    if container_ids:
        for cid in container_ids:
            code_i, out_i, _ = run_command(["docker", "inspect", "-f", "{{.Image}}", cid])
            if code_i == 0:
                img_id = out_i.strip()
                if img_id:
                    used_set.add(img_id)
    used_image_ids = sorted(used_set)

    # Enumerate images
    code, out, err = run_command([
        "docker",
        "image",
        "ls",
        "--all",
        "--digests",
        "--no-trunc",
        "--format",
        "{{json .}}",
    ])
    if code != 0:
        return images, used_image_ids

    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue

        repo = obj.get("Repository") or "<none>"
        tag = obj.get("Tag") or "<none>"
        image_id = obj.get("ID") or obj.get("ImageID") or ""
        created_at_raw = obj.get("CreatedAt") or ""
        created_at = to_iso8601(created_at_raw)
        size = obj.get("Size") or ""
        digest = obj.get("Digest") or ""
        if digest in ("<none>", "<none>:<none>"):
            digest = ""

        if not digest:
            # Try to resolve via docker inspect
            inspect_digests = []
            if tag and tag != "<none>" and repo and repo != "<none>":
                inspect_digests = _extract_inspect_repo_digests(f"{repo}:{tag}")
            if not inspect_digests and image_id:
                inspect_digests = _extract_inspect_repo_digests(image_id)
            digest_candidate = _choose_digest_for_repo(repo, inspect_digests)
            if digest_candidate:
                digest = digest_candidate

        images.append(
            LocalImage(
                repository=repo,
                tag=tag,
                image_id=image_id,
                created=created_at,
                size=size,
                digest=digest,
            )
        )

    return images, used_image_ids


# ----------------------- GHCR (Remote) -----------------------


class RemoteImage(Dict[str, Any]):
    pass


class GHCRClient:
    def __init__(self, username: str, token: str, timeout: int = 30):
        self.username = username
        self.token = token
        self.timeout = timeout
        self.api_headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "docker-inventory-compare-script",
        }
        self.registry_headers_base = {
            "User-Agent": "docker-inventory-compare-script",
        }
        self.registry_token_cache: Dict[str, str] = {}

    def _http_get_json(self, url: str) -> Any:
        req = urllib.request.Request(url, headers=self.api_headers, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def list_packages(self) -> List[Dict[str, Any]]:
        packages: List[Dict[str, Any]] = []
        page = 1
        while True:
            url = f"https://api.github.com/users/{self.username}/packages?package_type=container&per_page=100&page={page}"
            try:
                data = self._http_get_json(url)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break
                raise
            if not isinstance(data, list) or not data:
                break
            packages.extend(data)
            if len(data) < 100:
                break
            page += 1
        return packages

    def list_package_versions(self, package_name: str) -> List[Dict[str, Any]]:
        versions: List[Dict[str, Any]] = []
        page = 1
        while True:
            url = f"https://api.github.com/users/{self.username}/packages/container/{package_name}/versions?per_page=100&page={page}"
            try:
                data = self._http_get_json(url)
            except urllib.error.HTTPError as e:
                if e.code in (404, 403):
                    break
                raise
            if not isinstance(data, list) or not data:
                break
            versions.extend(data)
            if len(data) < 100:
                break
            page += 1
        return versions

    def _registry_get(self, url: str, bearer_token: str, accept: Optional[str] = None) -> Tuple[bytes, Dict[str, str]]:
        headers = dict(self.registry_headers_base)
        if accept:
            headers["Accept"] = accept
        headers["Authorization"] = f"Bearer {bearer_token}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = resp.read()
            headers_out = {k: v for k, v in resp.getheaders()}
            return data, headers_out

    def _fetch_registry_token(self, repo_path: str) -> Optional[str]:
        # GHCR token endpoint
        token_url = f"https://ghcr.io/token?service=ghcr.io&scope=repository:{repo_path}:pull"
        basic = base64.b64encode(f"{self.username}:{self.token}".encode("utf-8")).decode("ascii")
        headers = {
            "Authorization": f"Basic {basic}",
            "User-Agent": "docker-inventory-compare-script",
            "Accept": "application/json",
        }
        req = urllib.request.Request(token_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tok = data.get("token") or data.get("access_token")
                return tok
        except urllib.error.HTTPError as e:
            # 401/403 likely indicates insufficient scopes or private visibility without access
            return None
        except Exception:
            return None

    def get_registry_token(self, repo_path: str) -> Optional[str]:
        if repo_path in self.registry_token_cache:
            return self.registry_token_cache[repo_path]
        token = self._fetch_registry_token(repo_path)
        if token:
            self.registry_token_cache[repo_path] = token
        return token

    def fetch_manifest_info(
        self, package_name: str, tag: str, prefer_arch: str = "amd64", prefer_os: str = "linux"
    ) -> Dict[str, Any]:
        """
        Returns manifest info dict with keys:
        - index_digest: Optional[str]
        - arch_digest: Optional[str]
        - created: Optional[str] (ISO8601Z)
        - size_bytes: Optional[int]
        - content_type: str
        """
        repo_path = f"{self.username}/{package_name}"
        base = f"https://ghcr.io/v2/{repo_path}"
        accept_any = ", ".join(
            [
                "application/vnd.oci.image.index.v1+json",
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.docker.distribution.manifest.v2+json",
            ]
        )
        reg_token = self.get_registry_token(repo_path)
        if not reg_token:
            return {
                "index_digest": None,
                "arch_digest": None,
                "created": None,
                "size_bytes": None,
                "content_type": "",
            }
        try:
            body, headers = self._registry_get(f"{base}/manifests/{tag}", bearer_token=reg_token, accept=accept_any)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {
                    "index_digest": None,
                    "arch_digest": None,
                    "created": None,
                    "size_bytes": None,
                    "content_type": "",
                }
            raise

        content_type = headers.get("Content-Type", "")
        index_digest = headers.get("Docker-Content-Digest")
        created_iso: Optional[str] = None
        size_bytes: Optional[int] = None
        arch_digest: Optional[str] = None

        try:
            manifest = json.loads(body.decode("utf-8"))
        except Exception:
            manifest = {}

        if content_type in (
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.oci.image.index.v1+json",
        ):
            # Multi-arch index; choose preferred platform
            manifests = manifest.get("manifests") or []
            chosen = None
            for m in manifests:
                plat = (m.get("platform") or {})
                if plat.get("os") == prefer_os and plat.get("architecture") == prefer_arch:
                    chosen = m
                    break
            if chosen is None and manifests:
                chosen = manifests[0]
            if chosen is not None:
                arch_digest = chosen.get("digest")
                # Fetch the arch-specific image manifest
                if arch_digest:
                    arch_body, arch_headers = self._registry_get(
                        f"{base}/manifests/{arch_digest}",
                        bearer_token=reg_token,
                        accept=", ".join(
                            [
                                "application/vnd.oci.image.manifest.v1+json",
                                "application/vnd.docker.distribution.manifest.v2+json",
                            ]
                        ),
                    )
                    try:
                        arch_manifest = json.loads(arch_body.decode("utf-8"))
                    except Exception:
                        arch_manifest = {}

                    config = arch_manifest.get("config") or {}
                    config_digest = config.get("digest")
                    # Sum layer sizes + config size
                    total = 0
                    for layer in arch_manifest.get("layers", []) or []:
                        sz = layer.get("size")
                        if isinstance(sz, int):
                            total += sz
                    if isinstance(config.get("size"), int):
                        total += int(config.get("size"))
                    size_bytes = total if total > 0 else None

                    # Fetch config blob to extract created time
                    if config_digest:
                        try:
                            cfg_body, _ = self._registry_get(
                                f"{base}/blobs/{config_digest}",
                                bearer_token=reg_token,
                                accept="application/vnd.oci.image.config.v1+json, application/vnd.docker.container.image.v1+json",
                            )
                            cfg = json.loads(cfg_body.decode("utf-8"))
                            created_iso = parse_http_date(cfg.get("created", "")) or created_iso
                        except Exception:
                            pass
        else:
            # Single-arch image manifest
            try:
                config = (manifest or {}).get("config") or {}
                config_digest = config.get("digest")
                total = 0
                for layer in (manifest or {}).get("layers", []) or []:
                    sz = layer.get("size")
                    if isinstance(sz, int):
                        total += sz
                if isinstance(config.get("size"), int):
                    total += int(config.get("size"))
                size_bytes = total if total > 0 else None
                arch_digest = headers.get("Docker-Content-Digest")

                if config_digest:
                    try:
                        cfg_body, _ = self._registry_get(
                            f"{base}/blobs/{config_digest}",
                            bearer_token=reg_token,
                            accept="application/vnd.oci.image.config.v1+json, application/vnd.docker.container.image.v1+json",
                        )
                        cfg = json.loads(cfg_body.decode("utf-8"))
                        created_iso = parse_http_date(cfg.get("created", "")) or created_iso
                    except Exception:
                        pass
            except Exception:
                pass

        return {
            "index_digest": index_digest,
            "arch_digest": arch_digest,
            "created": created_iso,
            "size_bytes": size_bytes,
            "content_type": content_type,
        }


def get_ghcr_images(username: str, token: str) -> Tuple[List[RemoteImage], List[Dict[str, Any]]]:
    """Return (images, untagged_versions).

    images: List of RemoteImage entries with keys: repository, tag, image_id(N/A), created, size, digest, index_digest, arch_digest
    untagged_versions: raw version dicts for GHCR entries with no tags
    """
    client = GHCRClient(username, token)
    images: List[RemoteImage] = []
    untagged_versions: List[Dict[str, Any]] = []

    try:
        packages = client.list_packages()
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"Error listing GHCR packages: HTTP {e.code} {e.reason}\n")
        return images, untagged_versions
    except Exception as e:
        sys.stderr.write(f"Error listing GHCR packages: {e}\n")
        return images, untagged_versions

    for pkg in packages:
        name = pkg.get("name")
        if not name:
            continue
        try:
            versions = client.list_package_versions(name)
        except Exception as e:
            sys.stderr.write(f"Error listing versions for {name}: {e}\n")
            continue
        for ver in versions:
            meta = (ver.get("metadata") or {}).get("container") or {}
            tags = meta.get("tags") or []
            if not tags:
                untagged_versions.append(ver)
                continue

            # Choose the best created timestamp available (prefer config-created)
            ver_created = parse_http_date(ver.get("created_at", "")) or parse_http_date(ver.get("updated_at", ""))

            for tag in tags:
                try:
                    m = client.fetch_manifest_info(name, tag)
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        continue
                    sys.stderr.write(f"Error fetching manifest for {name}:{tag} - HTTP {e.code}\n")
                    continue
                except Exception as e:
                    sys.stderr.write(f"Error fetching manifest for {name}:{tag} - {e}\n")
                    continue

                created = m.get("created") or ver_created or ""
                size_bytes = m.get("size_bytes")
                idx_digest = m.get("index_digest")
                arch_digest = m.get("arch_digest")
                digest = idx_digest or arch_digest or ""

                images.append(
                    RemoteImage(
                        repository=f"ghcr.io/{username}/{name}",
                        tag=tag,
                        image_id="N/A",
                        created=created,
                        size=human_bytes(size_bytes) if size_bytes is not None else "N/A",
                        digest=digest,
                        index_digest=idx_digest or "",
                        arch_digest=arch_digest or "",
                    )
                )

    return images, untagged_versions


# ----------------------- Comparison & Markdown -----------------------


def key(repo: str, tag: str) -> Tuple[str, str]:
    return (repo or "", tag or "")


def make_table(headers: List[str], rows: List[List[str]]) -> str:
    # Simple Markdown table generator
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def compare_images(
    local_images: List[LocalImage],
    remote_images: List[RemoteImage],
) -> Dict[str, Any]:
    local_map: Dict[Tuple[str, str], LocalImage] = {key(i["repository"], i["tag"]): i for i in local_images}
    remote_map: Dict[Tuple[str, str], RemoteImage] = {key(i["repository"], i["tag"]): i for i in remote_images}

    local_keys = set(local_map.keys())
    remote_keys = set(remote_map.keys())

    both_keys = sorted(local_keys & remote_keys)
    local_only_keys = sorted(local_keys - remote_keys)
    remote_only_keys = sorted(remote_keys - local_keys)

    both_same_digest = []
    both_diff_digest = []
    both_unknown_digest = []

    for k in both_keys:
        l = local_map[k]
        r = remote_map[k]
        ld = (l.get("digest") or "").strip()
        rd = (r.get("digest") or "").strip()
        r_idx = (r.get("index_digest") or "").strip()
        r_arch = (r.get("arch_digest") or "").strip()

        # Consider a match if local digest equals remote index or arch digest
        same = False
        if ld and (ld == rd or ld == r_idx or ld == r_arch):
            same = True

        if ld and (rd or r_idx or r_arch):
            if same:
                both_same_digest.append((l, r))
            else:
                both_diff_digest.append((l, r))
        else:
            both_unknown_digest.append((l, r))

    # Same name different tags
    local_names: Dict[str, set] = {}
    for l in local_images:
        local_names.setdefault(l["repository"], set()).add(l["tag"])
    remote_names: Dict[str, set] = {}
    for r in remote_images:
        remote_names.setdefault(r["repository"], set()).add(r["tag"])
    common_names = sorted(set(local_names.keys()) & set(remote_names.keys()))
    same_name_diff_tags: List[Tuple[str, List[str], List[str]]] = []
    for name in common_names:
        lt = local_names.get(name, set())
        rt = remote_names.get(name, set())
        if lt != rt:
            same_name_diff_tags.append((name, sorted(list(lt)), sorted(list(rt))))

    return {
        "both_same_digest": both_same_digest,
        "both_diff_digest": both_diff_digest,
        "both_unknown_digest": both_unknown_digest,
        "local_only_keys": local_only_keys,
        "remote_only_keys": remote_only_keys,
        "same_name_diff_tags": same_name_diff_tags,
        "local_map": local_map,
        "remote_map": remote_map,
    }


def newer_of(created_local: str, created_remote: str) -> str:
    dl = iso_to_datetime(created_local)
    dr = iso_to_datetime(created_remote)
    if dl and dr:
        if dl > dr:
            return "LOCAL"
        elif dr > dl:
            return "GHCR"
        return "EQUAL"
    if dl and not dr:
        return "LOCAL"
    if dr and not dl:
        return "GHCR"
    return "UNKNOWN"


def generate_markdown(
    local_images: List[LocalImage],
    remote_images: List[RemoteImage],
    used_local_image_ids: List[str],
    remote_untagged_versions: List[Dict[str, Any]],
    cmp: Dict[str, Any],
) -> str:
    lines: List[str] = []
    lines.append("## Docker Image Inventory and Comparison")
    lines.append("")

    # Local inventory
    lines.append("### Local images")
    headers = ["REPOSITORY", "TAG", "IMAGE ID", "CREATED", "SIZE", "DIGEST", "USED"]
    rows: List[List[str]] = []
    used_set = set(used_local_image_ids)
    for i in sorted(local_images, key=lambda x: (x["repository"], x["tag"])):
        is_used = "yes" if i.get("image_id") in used_set else "no"
        rows.append([
            i.get("repository", ""),
            i.get("tag", ""),
            (i.get("image_id", "") or "").replace("sha256:", "sha256:"),
            i.get("created", ""),
            i.get("size", ""),
            i.get("digest", "") or "",
            is_used,
        ])
    lines.append(make_table(headers, rows))
    lines.append("")

    # GHCR inventory
    lines.append("### GHCR images")
    headers_r = ["REPOSITORY", "TAG", "IMAGE ID", "CREATED", "SIZE", "DIGEST"]
    rows_r: List[List[str]] = []
    for r in sorted(remote_images, key=lambda x: (x["repository"], x["tag"])):
        rows_r.append([
            r.get("repository", ""),
            r.get("tag", ""),
            "N/A",
            r.get("created", "") or "",
            r.get("size", "") or "N/A",
            r.get("digest", "") or "",
        ])
    lines.append(make_table(headers_r, rows_r))
    lines.append("")

    # Both with same digest
    lines.append("### In both (same name:tag) with same digest")
    headers_both = ["REPOSITORY", "TAG", "DIGEST", "CREATED (LOCAL)", "CREATED (GHCR)", "NEWER"]
    rows_both: List[List[str]] = []
    for l, r in cmp["both_same_digest"]:
        rows_both.append([
            l.get("repository", ""),
            l.get("tag", ""),
            r.get("digest", "") or l.get("digest", ""),
            l.get("created", ""),
            r.get("created", ""),
            newer_of(l.get("created", ""), r.get("created", "")),
        ])
    lines.append(make_table(headers_both, rows_both))
    lines.append("")

    # Both with different digest
    lines.append("### In both (same name:tag) with different digest")
    headers_diff = [
        "REPOSITORY",
        "TAG",
        "DIGEST (LOCAL)",
        "DIGEST (GHCR)",
        "CREATED (LOCAL)",
        "CREATED (GHCR)",
        "NEWER",
    ]
    rows_diff: List[List[str]] = []
    for l, r in cmp["both_diff_digest"]:
        rows_diff.append([
            l.get("repository", ""),
            l.get("tag", ""),
            l.get("digest", "") or "",
            r.get("digest", "") or "",
            l.get("created", ""),
            r.get("created", ""),
            newer_of(l.get("created", ""), r.get("created", "")),
        ])
    lines.append(make_table(headers_diff, rows_diff))
    lines.append("")

    # Both unknown digest
    lines.append("### In both (same name:tag) with unknown digest")
    headers_unk = ["REPOSITORY", "TAG", "DIGEST (LOCAL)", "DIGEST (GHCR)", "CREATED (LOCAL)", "CREATED (GHCR)"]
    rows_unk: List[List[str]] = []
    for l, r in cmp["both_unknown_digest"]:
        rows_unk.append([
            l.get("repository", ""),
            l.get("tag", ""),
            l.get("digest", "") or "",
            r.get("digest", "") or "",
            l.get("created", ""),
            r.get("created", ""),
        ])
    lines.append(make_table(headers_unk, rows_unk))
    lines.append("")

    # Local only
    lines.append("### Local only")
    headers_lo = ["REPOSITORY", "TAG", "IMAGE ID", "CREATED", "SIZE", "DIGEST"]
    rows_lo: List[List[str]] = []
    for repo, tag in cmp["local_only_keys"]:
        l = cmp["local_map"][(repo, tag)]
        rows_lo.append([
            l.get("repository", ""),
            l.get("tag", ""),
            (l.get("image_id", "") or ""),
            l.get("created", ""),
            l.get("size", ""),
            l.get("digest", "") or "",
        ])
    lines.append(make_table(headers_lo, rows_lo))
    lines.append("")

    # GHCR only
    lines.append("### GHCR only")
    headers_ro = ["REPOSITORY", "TAG", "CREATED", "SIZE", "DIGEST"]
    rows_ro: List[List[str]] = []
    for repo, tag in cmp["remote_only_keys"]:
        r = cmp["remote_map"][(repo, tag)]
        rows_ro.append([
            r.get("repository", ""),
            r.get("tag", ""),
            r.get("created", "") or "",
            r.get("size", "") or "N/A",
            r.get("digest", "") or "",
        ])
    lines.append(make_table(headers_ro, rows_ro))
    lines.append("")

    # Same name, different tags
    lines.append("### Same name but different tags")
    headers_nt = ["REPOSITORY", "LOCAL TAGS", "GHCR TAGS"]
    rows_nt: List[List[str]] = []
    for name, lt, rt in cmp["same_name_diff_tags"]:
        rows_nt.append([name, ", ".join(lt), ", ".join(rt)])
    lines.append(make_table(headers_nt, rows_nt))
    lines.append("")

    # Unused
    lines.append("### Unused images")
    # Local unused (by image ID)
    lines.append("#### Local unused (no container is using these image IDs)")
    headers_ul = ["REPOSITORY", "TAG", "IMAGE ID", "CREATED", "SIZE", "DIGEST"]
    rows_ul: List[List[str]] = []
    used_ids = set(used_local_image_ids)
    for i in sorted(local_images, key=lambda x: (x["repository"], x["tag"])):
        if i.get("image_id") not in used_ids:
            rows_ul.append([
                i.get("repository", ""),
                i.get("tag", ""),
                (i.get("image_id", "") or ""),
                i.get("created", ""),
                i.get("size", ""),
                i.get("digest", "") or "",
            ])
    lines.append(make_table(headers_ul, rows_ul))
    lines.append("")

    # GHCR unused (untagged)
    lines.append("#### GHCR untagged versions (no active tag/reference)")
    headers_ur = ["PACKAGE", "VERSION ID", "CREATED", "UPDATED", "TAGS"]
    rows_ur: List[List[str]] = []
    for ver in remote_untagged_versions:
        pkg = (ver.get("package_html_url") or "").split("/")[-1] or ""
        vid = str(ver.get("id", ""))
        created = parse_http_date(ver.get("created_at", "")) or ""
        updated = parse_http_date(ver.get("updated_at", "")) or ""
        tags = ", ".join((ver.get("metadata", {}) or {}).get("container", {}).get("tags", []) or [])
        rows_ur.append([pkg, vid, created, updated, tags])
    lines.append(make_table(headers_ur, rows_ur))
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Docker Image Inventory and Comparison Tool")
    parser.add_argument("--output", "-o", default="docker_image_inventory.md", help="Output Markdown file path")
    parser.add_argument("--username", default=os.environ.get("GH_USERNAME", ""), help="GitHub username (for GHCR)")
    parser.add_argument("--token", default=os.environ.get("GH_TOKEN", ""), help="GitHub PAT with read:packages")
    args = parser.parse_args()

    username = args.username.strip()
    token = args.token.strip()

    if not username:
        sys.stderr.write("Missing GitHub username. Provide via --username or GH_USERNAME env.\n")
        return 2

    if not token:
        sys.stderr.write("Missing GitHub token. Provide via --token or GH_TOKEN env.\n")
        return 2

    # Gather local
    local_images, used_ids = get_local_images()

    # Gather remote
    remote_images, remote_untagged = get_ghcr_images(username, token)

    # Compare
    cmp = compare_images(local_images, remote_images)

    # Markdown output
    md = generate_markdown(local_images, remote_images, used_ids, remote_untagged, cmp)
    out_path = os.path.abspath(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)

    # Minimal stdout info for operator
    print(f"Wrote Markdown report to: {out_path}")
    print(f"Local images: {len(local_images)} | GHCR images: {len(remote_images)} | GHCR untagged versions: {len(remote_untagged)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


