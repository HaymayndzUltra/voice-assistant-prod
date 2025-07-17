import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(__file__).resolve().parent.parent
MAINPC_DIR = BASE_DIR / 'main_pc_code'
PC2_DIR = BASE_DIR / 'pc2_code'

CONFIG_PATH_MAINPC = MAINPC_DIR / 'config' / 'startup_config_complete.yaml'
CONFIG_PATH_PC2 = PC2_DIR / 'config' / 'startup_config_corrected.yaml'

OUTPUT_JSON = BASE_DIR / 'output' / 'phase1_discovery.json'

IGNORE_DIR_KEYWORDS = {
    '_archive', '_trash', 'backups', 'logs', 'tests', 'test_scripts', 'test_audio', 'cache'
}

TEST_DIR_KEYWORDS = {'tests', 'test_scripts', 'testing', 'tests_smoke'}

ARCHIVE_DIR_KEYWORDS = {'_archive', '_trash', 'backups', 'archive'}


def load_configured_scripts() -> Dict[str, str]:
    """Parse startup configs to get configured script paths -> status classification."""
    results: Dict[str, str] = {}

    def _walk_config(node: Any):
        if isinstance(node, dict):
            if 'script_path' in node:
                script = node['script_path']
                status = 'active'
                enabled = node.get('enabled', True)
                required = node.get('required', True)
                # If explicitly disabled or not required, mark unused
                if not enabled or not required:
                    status = 'unused'
                results[script] = status
            else:
                for v in node.values():
                    _walk_config(v)
        elif isinstance(node, list):
            for item in node:
                _walk_config(item)

    for cfg_path in (CONFIG_PATH_MAINPC, CONFIG_PATH_PC2):
        with open(cfg_path, 'r') as f:
            cfg = yaml.safe_load(f)
        _walk_config(cfg)

    return results


def classify_file(path: Path, configured: Dict[str, str]) -> str:
    rel = str(path.relative_to(BASE_DIR))
    if any(k in rel for k in ARCHIVE_DIR_KEYWORDS):
        return 'archive'
    if any(k in rel for k in TEST_DIR_KEYWORDS) or path.name.startswith('test_'):
        return 'test'
    if rel in configured:
        return configured[rel]
    # Duplicates will be handled separately
    return 'ghost'


def gather_metadata() -> List[Dict[str, Any]]:
    configured = load_configured_scripts()
    all_files: List[Path] = list(MAINPC_DIR.rglob('*.py')) + list(PC2_DIR.rglob('*.py'))

    file_records = []
    for file_path in all_files:
        if any(k in str(file_path) for k in IGNORE_DIR_KEYWORDS):
            # Still include tests/archives but skip caches/logs etc.
            pass
        stat = file_path.stat()
        loc = 0
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                loc = sum(1 for _ in f)
        except Exception:
            pass
        classification = classify_file(file_path, configured)
        file_records.append({
            'file_path': str(file_path.relative_to(BASE_DIR)),
            'size_bytes': stat.st_size,
            'lines_of_code': loc,
            'last_modified': stat.st_mtime,
            'classification': classification,
        })
    return file_records


def detect_duplicates(records: List[Dict[str, Any]]):
    from collections import defaultdict
    name_map = defaultdict(list)
    for rec in records:
        name_map[Path(rec['file_path']).name].append(rec)
    duplicates = [recs for recs in name_map.values() if len(recs) > 1]
    for group in duplicates:
        for rec in group:
            if rec['classification'] == 'archive':
                continue
            rec['classification'] = 'duplicate'


def main():
    records = gather_metadata()
    detect_duplicates(records)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(records, f, indent=2)
    print(f"Discovery phase completed. Records saved to {OUTPUT_JSON}")


if __name__ == '__main__':
    main()