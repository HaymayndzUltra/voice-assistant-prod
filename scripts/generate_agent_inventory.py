import csv
import os
import re
import ast
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent
MACHINES = {
    "MainPC": WORKSPACE_ROOT / "main_pc_code" / "agents",
    "PC2": WORKSPACE_ROOT / "pc2_code" / "agents",
}

AGENT_PATTERN = re.compile(r"(?i).*agent.*\.py$")
PORT_REGEX = re.compile(r"tcp://[^:]+:(\d{3,6})")


def extract_ports(file_path: Path) -> set[str]:
    """Very light-weight regex scan for hard-coded port numbers inside tcp:// URLs."""
    ports: set[str] = set()
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        for match in PORT_REGEX.finditer(text):
            ports.add(match.group(1))
    except Exception:
        pass
    return ports


def extract_agent_classes(file_path: Path) -> list[str]:
    """Return class names in the file that inherit from anything ending with Agent."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8", errors="ignore"))
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.lower().endswith("agent"):
                    classes.append(node.name)
        return classes
    except Exception:
        return []


def build_inventory() -> list[dict]:
    inventory: list[dict] = []
    for machine, agents_dir in MACHINES.items():
        if not agents_dir.exists():
            continue
        for path in agents_dir.rglob("*.py"):
            if not AGENT_PATTERN.match(str(path.name)):
                # also accept files inside agents dir even if not matching *_agent
                if "agents" not in path.parts:
                    continue
            classes = extract_agent_classes(path)
            ports = extract_ports(path)
            inventory.append(
                {
                    "machine": machine,
                    "file": str(path.relative_to(WORKSPACE_ROOT)),
                    "classes": ";".join(classes) or "N/A",
                    "ports": ";".join(sorted(ports)) or "N/A",
                    "size_kb": round(path.stat().st_size / 1024, 1),
                }
            )
    return inventory


def main():
    inventory = build_inventory()
    out_csv = WORKSPACE_ROOT / "agent_inventory.csv"
    with out_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["machine", "file", "classes", "ports", "size_kb"],
        )
        writer.writeheader()
        writer.writerows(inventory)
    print(f"Generated inventory → {out_csv.relative_to(WORKSPACE_ROOT)}  (rows={len(inventory)})")


if __name__ == "__main__":
    main()