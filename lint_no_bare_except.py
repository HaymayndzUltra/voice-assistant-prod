"""lint_no_bare_except.py
Flake8 plugin banning bare `except:` and broad `except Exception:`.
Install with:
    pip install -e .
Then run: flake8 --select=E9F      (E9F900 custom code)
"""
import ast
from typing import Generator, Tuple

__version__ = "0.1.0"
_BARE_MSG = "E900 bare except or 'except Exception' is forbidden"


class BareExceptChecker:
    name = "flake8-bare-except"
    version = __version__

    def __init__(self, tree):
        self.tree = tree

    def run(self) -> Generator[Tuple[int, int, str, type], None, None]:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    yield node.lineno, node.col_offset, _BARE_MSG, type(self)
                elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    yield node.lineno, node.col_offset, _BARE_MSG, type(self)