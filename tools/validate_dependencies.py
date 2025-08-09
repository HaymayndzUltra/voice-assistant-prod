#!/usr/bin/env python3
import sys, yaml

FILES = [
  "main_pc_code/config/startup_config.yaml",
  "pc2_code/config/startup_config.yaml",
]

ALLOW_MISSING = {"CloudTranslationService", "UnifiedSystemAgent"}

LEGACY_BLOCKERS = {"ObservabilityHub"}

def load(path):
  with open(path, 'r', encoding='utf-8') as f:
    return yaml.safe_load(f) or {}

def collect_agents(doc):
  names=set()
  ag = (doc.get('agent_groups') or {})
  for group, entries in ag.items():
    if isinstance(entries, dict):
      for agent_name in entries.keys():
        names.add(agent_name)
  pcs = doc.get('pc2_services') or []
  for svc in pcs:
    if isinstance(svc, dict) and 'name' in svc:
      names.add(svc['name'])
  return names

def scan_doc(path, doc):
  errs=[]
  text = open(path,'r',encoding='utf-8').read()
  if any(x in text for x in LEGACY_BLOCKERS):
    errs.append(f"{path}: contains legacy ObservabilityHub reference")

  agents = collect_agents(doc)
  ag = (doc.get('agent_groups') or {})
  for group, entries in ag.items():
    if isinstance(entries, dict):
      for agent_name, cfg in entries.items():
        deps = (cfg or {}).get('dependencies') or []
        for d in deps:
          if d not in agents and d not in ALLOW_MISSING:
            errs.append(f"{path}: {agent_name} depends on missing agent '{d}'")

  # RTAP gating matching
  speech = (ag.get('speech_io') or {})
  def get_req(x):
    v = speech.get(x, {}) or {}
    return str(v.get('required', '')).strip()
  if speech:
    si = get_req('StreamingInterruptHandler')
    sla = get_req('StreamingLanguageAnalyzer')
    ssr = get_req('StreamingSpeechRecognition')
    if si and ssr and si != ssr:
      errs.append(f"{path}: StreamingInterruptHandler required gating != SSR gating ({si} vs {ssr})")
    if sla and ssr and sla != ssr:
      errs.append(f"{path}: StreamingLanguageAnalyzer required gating != SSR gating ({sla} vs {ssr})")
  return errs

def main():
  errors=0
  for path in FILES:
    try:
      doc = load(path)
      for msg in scan_doc(path, doc):
        print("[DEP-GRAPH]", msg)
        errors+=1
    except Exception as e:
      print(f"[DEP-PARSE] {path}: {e}")
      errors+=1
  if errors:
    print(f"FAIL: Dependency validation found {errors} issues")
    sys.exit(1)
  print("OK: Dependencies and gating validated")

if __name__ == "__main__":
  main()