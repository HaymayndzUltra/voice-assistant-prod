import yaml, os

config_file = "main_pc_code/config/startup_config.yaml"  # Palitan kung iba
base_dirs = ["."]

with open(config_file) as f:
    data = yaml.safe_load(f)

results = {}

def try_file(fpath):
    for bd in base_dirs:
        fp = os.path.join(bd, fpath)
        if os.path.isfile(fp):
            return fp
    return None

def scan_agents(d):
    for key, val in d.items():
        if isinstance(val, dict):
            if 'script_path' in val:
                fpath = try_file(val['script_path'])
                if fpath:
                    try:
                        with open(fpath, encoding='utf-8') as af:
                            content = af.read()
                            results[fpath] = len([c for c in content if c.isalpha()])
                    except Exception as e:
                        results[fpath] = f"ERROR: {e}"
                else:
                    results[val['script_path']] = "ERROR: File not found in any base_dir"
            else:
                scan_agents(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    scan_agents(item)

scan_agents(data.get('agent_groups', {}))

for f, count in results.items():
    print(f"{f}: {count}")
