#!/usr/bin/env python3
import os, re, csv, argparse, subprocess, sys
from pathlib import Path

# YAML loader (ruamel preferred, fallback to PyYAML)
try:
    from ruamel.yaml import YAML  # type: ignore
    _YAML_IMPL = "ruamel"
    yaml_ruamel = YAML(typ="safe")
except Exception:
    import yaml as pyyaml  # type: ignore
    _YAML_IMPL = "pyyaml"
    yaml_ruamel = None

def load_yaml(path: Path):
    if _YAML_IMPL == "ruamel":
        with path.open("r", encoding="utf-8") as f:
            return yaml_ruamel.load(f)
    else:
        with path.open("r", encoding="utf-8") as f:
            return pyyaml.safe_load(f)

def discover_startup_configs(repo: Path):
    return [Path(p) for p in repo.rglob("config/startup_config.yaml")]

def derive_host_label(p: Path):
    s = str(p).lower()
    if "main_pc_code" in s or "mainpc" in s:
        return "MainPC"
    if "pc2_code" in s or "pc2" in s:
        return "PC2"
    try:
        return p.parent.parent.name
    except Exception:
        return "UnknownHost"

def extract_agents(doc, host_label, file_path):
    rows = []
    if not isinstance(doc, dict):
        return rows
    
    # Handle main_pc_code format (agent_groups as nested dict)
    agent_groups = doc.get("agent_groups", {})
    if isinstance(agent_groups, dict):
        for group_name, group_content in agent_groups.items():
            if isinstance(group_content, dict):
                for agent_name, agent_data in group_content.items():
                    if isinstance(agent_data, dict):
                        required = agent_data.get("required", True)
                        ports = []
                        for k in ("port", "health_check_port", "http_port", "grpc_port", "metrics_port"):
                            if k in agent_data:
                                ports.append(f"{k}:{agent_data[k]}")
                        rows.append({
                            "host": host_label,
                            "group": group_name,
                            "agent": agent_name,
                            "required": bool(required),
                            "ports": ",".join(ports) if ports else "n/a",
                            "source_file": str(file_path)
                        })
    
    # Handle pc2_code format (pc2_services as list)
    pc2_services = doc.get("pc2_services", [])
    if isinstance(pc2_services, list):
        for service in pc2_services:
            if isinstance(service, dict):
                name = service.get("name", "")
                if name:
                    required = service.get("required", True)
                    ports = []
                    for k in ("port", "health_check_port"):
                        if k in service:
                            ports.append(f"{k}:{service[k]}")
                    rows.append({
                        "host": host_label,
                        "group": "pc2_services",
                        "agent": name,
                        "required": bool(required),
                        "ports": ",".join(ports) if ports else "n/a",
                        "source_file": str(file_path)
                    })
    
    # Handle any top-level agents list (if exists)
    agents = doc.get("agents", [])
    if isinstance(agents, list):
        for a in agents:
            if isinstance(a, dict):
                name = a.get("name", "")
                if name:
                    required = a.get("required", True)
                    ports = []
                    for k in ("port", "health_check_port"):
                        if k in a:
                            ports.append(f"{k}:{a[k]}")
                    rows.append({
                        "host": host_label,
                        "group": "default",
                        "agent": name,
                        "required": bool(required),
                        "ports": ",".join(ports) if ports else "n/a",
                        "source_file": str(file_path)
                    })
    
    return rows

def run_rg(repo: Path, pattern: str):
    try:
        completed = subprocess.run(
            ["rg", "-n", "-S", pattern, str(repo)],
            capture_output=True, text=True, check=False
        )
        if completed.returncode in (0,1):
            return completed.stdout.strip()
        return completed.stdout.strip()
    except FileNotFoundError:
        return ""

def extract_note_hubs(repo: Path, agent: str):
    hubs = set()
    out = run_rg(repo, rf"{re.escape(agent)}.*(CONSOLIDATED INTO|Consolidation Target|CONSOLIDATED)")
    if out:
        for line in out.splitlines():
            m = re.search(r"(?:CONSOLIDATED INTO|Consolidation Target)\s*[:\-]?\s*([A-Za-z0-9_./\-]+)", line)
            if m:
                hubs.add(m.group(1))
    if not hubs:
        out2 = run_rg(repo, r"(CONSOLIDATED INTO|Consolidation Target)\s*[:\-]?\s*([A-Za-z0-9_./\-]+)")
        for line in out2.splitlines():
            if agent in line:
                m = re.search(r"(?:CONSOLIDATED INTO|Consolidation Target)\s*[:\-]?\s*([A-Za-z0-9_./\-]+)", line)
                if m:
                    hubs.add(m.group(1))
    return hubs

def load_ledger(repo: Path):
    candidates = [
        repo / "consolidation_ledger.yaml",
        repo / "infra" / "consolidation_ledger.yaml",
        repo / "memory-bank" / "consolidation_ledger.yaml",
    ]
    for p in candidates:
        if p.exists():
            try:
                return load_yaml(p)
            except Exception:
                return {}
    return {}

def ledger_lookup(ledger, agent: str):
    if not isinstance(ledger, dict):
        return None
    for m in (ledger.get("mappings") or []):
        if (m.get("agent") or "").strip() == agent:
            return m
    return None

def invalid_scope(hub_name: str, host_label: str) -> bool:
    # ModelOpsCoordinator is MainPC-only
    if hub_name and hub_name.lower() == "modelopscoordinator" and host_label != "MainPC":
        return True
    return False

def compute_verdict(required: bool, ports: str, note: bool, in_ledger: bool):
    signals = []
    if not required:
        signals.append("not-required")
    if ports == "n/a":
        signals.append("no-port")
    if note:
        signals.append("has-note")
    if in_ledger:
        signals.append("in-ledger")
    count = len(signals)
    if count >= 3:
        verdict = "consolidated"
    elif count == 2:
        verdict = "partial"
    else:
        verdict = "active/legacy?"
    return verdict, "|".join(signals) if signals else "none"

def main():
    ap = argparse.ArgumentParser(description="Audit hub membership and produce comment-out suggestions.")
    ap.add_argument("--repo", default=".", help="Repo root (default: .)")
    ap.add_argument("--yaml", nargs="*", help="Explicit startup_config.yaml paths (optional)")
    ap.add_argument("--hubs", nargs="+", required=True, help="Hub names to consider (case-insensitive)")
    ap.add_argument("--outdir", default=".", help="Directory to write CSV outputs")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    hub_filters = set([h.lower() for h in args.hubs])  # also used as core-hub guard
    paths = [Path(p).resolve() for p in args.yaml] if args.yaml else discover_startup_configs(repo)
    if not paths:
        print("ERROR: No startup_config.yaml found. Use --yaml to specify.", file=sys.stderr)
        sys.exit(2)

    # Ensure our two expected files exist (fail fast if missing)
    must = [
        repo / "main_pc_code" / "config" / "startup_config.yaml",
        repo / "pc2_code" / "config" / "startup_config.yaml",
    ]
    for m in must:
        if not m.exists():
            print(f"ERROR: Missing required file: {m}", file=sys.stderr); sys.exit(2)

    ledger = load_ledger(repo)

    rows = []
    for p in paths:
        if not p.exists():
            print(f"WARN: missing {p}", file=sys.stderr)
            continue
        host = derive_host_label(p)
        doc = load_yaml(p)
        rows += extract_agents(doc, host, p)

    hub_rows, commentout_rows, active_rows = [], [], []

    for r in sorted(rows, key=lambda x: (x["host"], x["group"], x["agent"])):
        agent = r["agent"]
        note_hubs = extract_note_hubs(repo, agent)
        ledg = ledger_lookup(ledger, agent)
        ledger_hub = (ledg or {}).get("hub","").strip() if ledg else ""
        in_ledger = bool(ledg)
        has_note = bool(note_hubs)

        verdict, signals = compute_verdict(r["required"], r["ports"], has_note, in_ledger)
        # Candidate hubs for this agent (notes + ledger)
        candidates = set(h.lower() for h in note_hubs)
        if ledger_hub:
            candidates.add(ledger_hub.lower())

        # Keep only if it maps to one of our 5 hubs
        passes_filter = len(candidates.intersection(hub_filters)) > 0

        if passes_filter:
            primary_hub = ledger_hub or (next(iter(note_hubs)) if note_hubs else "n/a")
            scope_bad = invalid_scope(primary_hub, r["host"]) if primary_hub else False
            src = "ledger+note" if (ledger_hub and note_hubs) else "ledger" if ledger_hub else "note"
            hub_rows.append({
                "hub": primary_hub if primary_hub else "n/a",
                "agent": agent,
                "source": src if primary_hub else "n/a",
                "host": r["host"],
                "group": r["group"],
                "required": r["required"],
                "ports": r["ports"],
                "signals": signals + ("|invalid-scope" if scope_bad else ""),
                "verdict": "invalid-scope" if scope_bad else verdict,
                "source_file": r["source_file"]
            })

            # Comment-out suggestion only if consolidated, in-scope, and NOT a core hub service
            if (verdict == "consolidated") and (not scope_bad) and (agent.lower() not in hub_filters):
                yq_cmd = f'yq -i \'(.groups[].agents[] | select(.name=="{agent}")).required = false\' "{r["source_file"]}"'
                commentout_rows.append({
                    "host": r["host"],
                    "group": r["group"],
                    "agent": agent,
                    "source_file": r["source_file"],
                    "ports": r["ports"],
                    "signals": signals,
                    "verdict": verdict,
                    "yq_suggest": yq_cmd
                })
            else:
                active_rows.append({
                    "host": r["host"],
                    "group": r["group"],
                    "agent": agent,
                    "required": r["required"],
                    "ports": r["ports"],
                    "signals": signals + ("|invalid-scope" if scope_bad else ""),
                    "verdict": "invalid-scope" if scope_bad else verdict,
                    "source_file": r["source_file"]
                })

    def write_csv(path: Path, rows, headers):
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=headers); w.writeheader()
            for row in rows: w.writerow(row)

    hub_csv = outdir / "hub_membership_report.csv"
    com_csv = outdir / "commentout_candidates.csv"
    act_csv = outdir / "active_agents_report.csv"

    write_csv(hub_csv, hub_rows, ["hub","agent","source","host","group","required","ports","signals","verdict","source_file"])
    write_csv(com_csv, commentout_rows, ["host","group","agent","source_file","ports","signals","verdict","yq_suggest"])
    write_csv(act_csv, active_rows, ["host","group","agent","required","ports","signals","verdict","source_file"])

    print(f"Wrote {hub_csv}")
    print(f"Wrote {com_csv}")
    print(f"Wrote {act_csv}")
    if not hub_rows:
        print("NOTE: No agents mapped to the specified hubs. Check notes/ledger or hub names.", file=sys.stderr)

if __name__ == "__main__":
    main()