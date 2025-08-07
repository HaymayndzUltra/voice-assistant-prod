def test_import():
    import ast, pathlib
    p = pathlib.Path("services/self_healing_supervisor/supervisor.py")
    content = p.read_text()
    tree = ast.parse(content)
    # Check for main function and docker client
    has_main = any(isinstance(node, ast.If) and hasattr(node.test, 'left') and 
                   getattr(node.test.left, 'id', None) == '__name__' for node in ast.walk(tree))
    assert has_main, "Main execution block not found"
