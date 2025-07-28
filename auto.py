import ast
import sys
import os
from pathlib import Path
import re

visited = set()
base_path = Path(".")

def find_imports_and_data(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return [], [], []

    imports, data_files, config_files = [], [], []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

        elif isinstance(node, ast.Call) and hasattr(node.func, 'id'):
            # Detect open("file"), yaml.load("file"), torch.load("file"), etc.
            args = node.args
            if args and isinstance(args[0], ast.Constant):
                val = args[0].value
                if isinstance(val, str):
                    if re.search(r'\.ya?ml$', val):
                        config_files.append(val)
                    elif re.search(r'\.(json|bin|pt|pkl|mpk|msgpack)$', val):
                        data_files.append(val)

    return imports, config_files, data_files

def resolve_local_imports(imp):
    rel_path = base_path / Path(imp.replace(".", "/") + ".py")
    if rel_path.exists():
        return rel_path
    return None

def trace_file(file_path, depth=0):
    global visited
    if file_path in visited:
        return
    visited.add(file_path)

    indent = "  " * depth
    print(f"{indent}📄 {file_path.name}")

    imports, configs, data = find_imports_and_data(file_path)

    for imp in imports:
        local = resolve_local_imports(imp)
        if local:
            print(f"{indent} ├── imports: {imp}")
            trace_file(local, depth + 1)

    for cfg in configs:
        print(f"{indent} ├── loads config: {cfg}")
    for dat in data:
        print(f"{indent} ├── loads data: {dat}")

def walk_directory(path):
    path = Path(path)
    for pyfile in path.rglob("*.py"):
        print("=" * 60)
        trace_file(pyfile)
        print("=" * 60)

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    walk_directory(target_dir)
