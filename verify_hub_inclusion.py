#!/usr/bin/env python3
"""
Reads:
  - audits/hub_membership_report.csv (from your previous audit)
  - hub_manifest.yaml
  - optional consolidation_ledger.yaml (for replaced_by paths)

Produces:
  - audits/proof_matrix.csv  (per agent proof breakdown + confidence score)
  - audits/missing_or_weak.csv (agents mapped to hubs but lacking strong proofs)
Rules:
  exists_in_hub = (strong_proofs >= 1) and (weak_proofs >= 1)
  confidence ∈ [0,1]: strong=0.6 each, weak=0.25 each (capped at 1.0)
"""
import csv, sys, re, os
from pathlib import Path
import subprocess

# YAML loader
try:
    from ruamel.yaml import YAML
    yaml = YAML(typ="safe")
except Exception:
    import yaml as pyyaml
    def yaml_load(p):
        with open(p,"r",encoding="utf-8") as f:
            return pyyaml.safe_load(f)
else:
    def yaml_load(p):
        with open(p,"r",encoding="utf-8") as f:
            return yaml.load(f)

REPO = Path(".").resolve()
AUDITS = REPO / "audits"
HM = REPO / "hub_manifest.yaml"
LEDGER = REPO / "consolidation_ledger.yaml"  # optional
IN_CSV = AUDITS / "hub_membership_report.csv"
OUT_PROOF = AUDITS / "proof_matrix.csv"
OUT_WEAK = AUDITS / "missing_or_weak.csv"

def rg(pattern, cwd):
    try:
        r = subprocess.run(["rg","-n","-S",pattern,str(cwd)], capture_output=True, text=True)
        return r.stdout.strip()
    except FileNotFoundError:
        return ""  # rg missing

def load_ledger():
    if LEDGER.exists():
        try:
            return yaml_load(LEDGER)
        except Exception:
            return {}
    return {}

def ledger_replaced_by(ledger, agent):
    try:
        for m in (ledger.get("mappings") or []):
            if (m.get("agent") or "").strip() == agent:
                return (m.get("replaced_by") or "").strip()
    except Exception:
        pass
    return ""

def main():
    if not IN_CSV.exists():
        print(f"ERROR: missing {IN_CSV}", file=sys.stderr); sys.exit(2)
    if not HM.exists():
        print(f"ERROR: missing {HM}", file=sys.stderr); sys.exit(2)

    manifest = yaml_load(HM)
    hubs = manifest.get("hubs") or []
    hubs_by_name = { (h.get("name") or "").strip(): h for h in hubs }

    ledger = load_ledger()

    rows = []
    with open(IN_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    out_rows = []
    weak_rows = []

    for r in rows:
        hub = (r.get("hub") or "").strip()
        agent = (r.get("agent") or "").strip()
        host = (r.get("host") or "").strip()
        required = str(r.get("required","")).lower()
        ports = (r.get("ports") or "").strip()
        signals = (r.get("signals") or "").strip()
        verdict = (r.get("verdict") or "").strip()
        source_file = (r.get("source_file") or "").strip()

        mh = hubs_by_name.get(hub)
        if not mh:
            # not a target hub from manifest; skip
            continue

        # Host scope guard (e.g., ModelOpsCoordinator MainPC-only)
        scope = mh.get("host_scope","")
        if scope and scope != host:
            strong = []; weak = ["invalid_scope"]
            score = 0.25
            out_rows.append({
                "hub": hub, "agent": agent, "host": host,
                "strong_proofs": "|".join(strong) if strong else "none",
                "weak_proofs": "|".join(weak),
                "exists_in_hub": "false",
                "confidence": f"{score:.2f}",
                "source_file": source_file
            })
            weak_rows.append(out_rows[-1])
            continue

        # Weak proofs from audit signals
        weak = []
        if "not-required" in signals: weak.append("not-required")
        if "no-port" in signals: weak.append("no-port")
        if "has-note" in signals: weak.append("has-note")
        if "in-ledger" in signals: weak.append("in-ledger")

        # Strong proofs (code-level)
        strong = []
        code_roots = mh.get("code_roots") or []
        include_globs = mh.get("include_globs") or ["**/*.py"]
        registry_hints = mh.get("registry_hints") or []

        # 1) replaced_by path must exist under any hub root
        repl = ledger_replaced_by(ledger, agent)
        if repl:
            p = REPO / repl
            if p.exists():
                # also verify it's inside one of code_roots
                inside = any((REPO / cr) in p.resolve().parents for cr in code_roots)
                if inside or not code_roots:
                    strong.append("ledger.replaced_by.exists")

        # 2) registry/registration & imports in hub code
        for cr in code_roots:
            base = REPO / cr
            if not base.exists(): continue
            # search for register patterns mentioning agent name root
            agent_token = re.escape(agent)
            hits = []
            # registration verbs
            for pat in [rf"{agent_token}.*register", rf"register.*{agent_token}", rf"add_stage.*{agent_token}", rf"{agent_token}.*add_stage"]:
                h = rg(pat, base)
                if h: hits.append("registry:"+pat)
            # imports/refs
            for pat in [rf"from .* import .*{agent_token}", rf"import .*{agent_token}", rf"{agent_token}.*Adapter", rf"{agent_token}.*Stage"]:
                h = rg(pat, base); 
                if h: hits.append("ref:"+pat)
            # registry hint files
            for hint in registry_hints:
                pat = rf"{hint}.*{agent_token}|{agent_token}.*{hint}"
                h = rg(pat, base)
                if h: hits.append("hint:"+pat)

            if hits:
                strong.append("hub_code_refs")

        # Confidence scoring
        score = 0.0
        score += 0.6 * (1 if strong else 0)          # any strong proof
        # count distinct weak categories (cap 2)
        wuniq = set(weak)
        score += 0.25 * min(len(wuniq), 2)
        if score > 1.0: score = 1.0

        exists = "true" if (strong and weak) else "false"

        row = {
            "hub": hub, "agent": agent, "host": host,
            "strong_proofs": "|".join(strong) if strong else "none",
            "weak_proofs": "|".join(weak) if weak else "none",
            "exists_in_hub": exists,
            "confidence": f"{score:.2f}",
            "source_file": source_file
        }
        out_rows.append(row)
        if exists == "false":
            weak_rows.append(row)

    AUDITS.mkdir(parents=True, exist_ok=True)
    with open(OUT_PROOF, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader(); w.writerows(out_rows)
    with open(OUT_WEAK, "w", newline="", encoding="utf-8") as f:
        if weak_rows:
            w = csv.DictWriter(f, fieldnames=list(weak_rows[0].keys()))
            w.writeheader(); w.writerows(weak_rows)
        else:
            f.write("")

    print(f"Wrote {OUT_PROOF}")
    print(f"Wrote {OUT_WEAK} (may be empty)")

if __name__ == "__main__":
    main()