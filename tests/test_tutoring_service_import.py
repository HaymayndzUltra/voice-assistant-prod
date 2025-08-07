def test_import():
    import ast, pathlib
    p = pathlib.Path("pc2_code/agents/TutoringServiceAgent.py")
    content = p.read_text()
    tree = ast.parse(content)
    found_class = any(isinstance(node, ast.ClassDef) and node.name == "TutoringServiceAgent" for node in ast.walk(tree))
    assert found_class, "TutoringServiceAgent class not found"
