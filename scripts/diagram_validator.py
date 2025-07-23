#!/usr/bin/env python3
"""diagram_validator.py
Ensures that create_system_diagram.py is up-to-date with agent_inventory.csv.
If counts mismatch, it will call the generator to rebuild the diagram.
"""
import subprocess
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
INVENTORY = ROOT / "agent_inventory.csv"
DIAGRAM_HTML = ROOT / "system_diagram.html"


def count_agents_in_inventory():
    with INVENTORY.open() as f:
        return sum(1 for _ in csv.DictReader(f))


def extract_agent_count_from_html():
    if not DIAGRAM_HTML.exists():
        return 0
    return sum(1 for line in DIAGRAM_HTML.read_text().splitlines() if "class=\"agent-name\"" in line)


def main():
    inv_count = count_agents_in_inventory()
    html_count = extract_agent_count_from_html()
    if inv_count != html_count:
        print(f"Mismatch detected (inventory={inv_count}, diagram={html_count}). Regenerating…")
        ret = subprocess.call([sys.executable, "create_system_diagram.py"], cwd=str(ROOT))
        sys.exit(ret)
    else:
        print("✔ Diagram is up to date.")


if __name__ == "__main__":
    main()