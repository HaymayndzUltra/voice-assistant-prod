import ast
from pathlib import Path

# Enforce use of ServiceNames constants instead of string literals
# This lightweight static check parses Python files under main_pc_code/agents and services

ALLOWED_FILES = [
    Path("common/constants/service_names.py").resolve(),
]

FORBIDDEN_LITERALS = {
    "StreamingTTSAgent",
    "StreamingSpeechRecognition",
    "StreamingInterruptHandler",
    "RequestCoordinator",
}


def _violations_in_file(py_path: Path) -> list[str]:
    try:
        src = py_path.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return []
    violations = []
    class LiteralVisitor(ast.NodeVisitor):
        def visit_Constant(self, node: ast.Constant):
            if isinstance(node.value, str) and node.value in FORBIDDEN_LITERALS:
                violations.append(f"{py_path}:{node.lineno} uses literal '{node.value}' (use ServiceNames)")
    LiteralVisitor().visit(tree)
    return violations


def test_service_name_literals():
    root = Path("/workspace")
    targets = []
    for rel in ["main_pc_code/agents", "main_pc_code/services", "pc2_code/agents", "services"]:
        p = root / rel
        if p.exists():
            targets.extend(p.rglob("*.py"))
    problems = []
    for f in targets:
        if f.resolve() in ALLOWED_FILES:
            continue
        problems.extend(_violations_in_file(f))
    assert not problems, "\n" + "\n".join(problems)