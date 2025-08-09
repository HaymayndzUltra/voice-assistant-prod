#!/usr/bin/env python3
import sys, yaml

FILES = [
  "main_pc_code/config/startup_config.yaml",
  "pc2_code/config/startup_config.yaml",
]

ALLOW_MISSING = {"CloudTranslationService", "UnifiedSystemAgent", "UnifiedObservabilityCenter"}

LEGACY_BLOCKERS = {"ObservabilityHub"}

def load(path):
  with open(path, 'r', encoding='utf-8') as f:
    return yaml.safe_load(f) or {}


def collect_agents(doc):
  names = set()
  ag = (doc.get('agent_groups') or {}) if isinstance(doc, dict) else {}
  for group, entries in ag.items():
    if isinstance(entries, dict):
      for agent_name in entries.keys():
        names.add(agent_name)
  pcs = doc.get('pc2_services') or [] if isinstance(doc, dict) else []
  for svc in pcs:
    if isinstance(svc, dict) and 'name' in svc:
      names.add(svc['name'])
  return names


def contains_legacy(obj) -> bool:
  if isinstance(obj, str):
    return obj in LEGACY_BLOCKERS
  if isinstance(obj, dict):
    for k, v in obj.items():
      if contains_legacy(k) or contains_legacy(v):
        return True
    return False
  if isinstance(obj, list):
    for it in obj:
      if contains_legacy(it):
        return True
    return False
  return False


def scan_doc(path, doc):
  errs = []
  # Only scan parsed YAML (comments are not present), avoiding false positives
  if contains_legacy(doc):
    errs.append(f"{path}: contains legacy ObservabilityHub reference")

  agents = collect_agents(doc)
  ag = (doc.get('agent_groups') or {}) if isinstance(doc, dict) else {}
  for group, entries in ag.items():
    if not isinstance(entries, dict):
      continue
    for agent_name, cfg in entries.items():
      if not isinstance(cfg, dict):
        # Skip non-dict stubs or malformed entries
        continue
      deps = (cfg.get('dependencies') or [])
      if not isinstance(deps, list):
        # Normalize single string to list
        deps = [deps] if isinstance(deps, str) else []
      for d in deps:
        if isinstance(d, str) and d not in agents and d not in ALLOW_MISSING:
          errs.append(f"{path}: {agent_name} depends on missing agent '{d}'")

  # RTAP gating matching (guard non-dict configs)
  speech = ag.get('speech_io') if isinstance(ag, dict) else None
  if isinstance(speech, dict):
    def get_req(x):
      v = speech.get(x, {})
      v = v if isinstance(v, dict) else {}
      return str(v.get('required', '')).strip()
    si = get_req('StreamingInterruptHandler')
    sla = get_req('StreamingLanguageAnalyzer')
    ssr = get_req('StreamingSpeechRecognition')
    if si and ssr and si != ssr:
      errs.append(f"{path}: StreamingInterruptHandler required gating != SSR gating ({si} vs {ssr})")
    if sla and ssr and sla != ssr:
      errs.append(f"{path}: StreamingLanguageAnalyzer required gating != SSR gating ({sla} vs {ssr})")
  return errs


def main():
  errors = 0
  for path in FILES:
    try:
      doc = load(path)
      for msg in scan_doc(path, doc):
        print("[DEP-GRAPH]", msg)
        errors += 1
    except Exception as e:
      print(f"[DEP-PARSE] {path}: {e}")
      errors += 1
  if errors:
    print(f"FAIL: Dependency validation found {errors} issues")
    sys.exit(1)
  print("OK: Dependencies and gating validated")

if __name__ == "__main__":
  main()