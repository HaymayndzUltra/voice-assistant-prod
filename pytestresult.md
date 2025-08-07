/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_nllb_translation.py", line 23
E       logger = configure_logging(__name__) / "nllb_test_results.log"),
E                                                                     ^
E   SyntaxError: unmatched ')'
_________________________________________ ERROR collecting pc2_code/test_ollama.py _________________________________________
import file mismatch:
imported module 'test_ollama' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_ollama.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_ollama.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
__________________________________ ERROR collecting pc2_code/test_performance_monitor.py ___________________________________
import file mismatch:
imported module 'test_performance_monitor' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_performance_monitor.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_performance_monitor.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
_______________________________ ERROR collecting pc2_code/test_performance_monitor_health.py _______________________________
import file mismatch:
imported module 'test_performance_monitor_health' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_performance_monitor_health.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_performance_monitor_health.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
__________________________________ ERROR collecting pc2_code/test_phi_adapter_advanced.py __________________________________
import file mismatch:
imported module 'test_phi_adapter_advanced' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_phi_adapter_advanced.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_phi_adapter_advanced.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
_______________________________ ERROR collecting pc2_code/test_proactive_context_monitor.py ________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_proactive_context_monitor.py", line 9
E       sys.path.insert(0, str(current_dir)
E                      ^
E   SyntaxError: '(' was never closed
_______________________________________ ERROR collecting pc2_code/test_rca_agent.py ________________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_rca_agent.py", line 9
E       sys.path.insert(0, str(current_dir)
E                      ^
E   SyntaxError: '(' was never closed
___________________________________ ERROR collecting pc2_code/test_self_healing_agent.py ___________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_self_healing_agent.py", line 18
E       sys.path.insert(0, str(project_root)
E                      ^
E   SyntaxError: '(' was never closed
______________________________________ ERROR collecting pc2_code/test_simple_agent.py ______________________________________
import file mismatch:
imported module 'test_simple_agent' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_simple_agent.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_simple_agent.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
________________________________________ ERROR collecting pc2_code/test_taglish.py _________________________________________
import file mismatch:
imported module 'test_taglish' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_taglish.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_taglish.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
____________________________________ ERROR collecting pc2_code/test_tiered_responder.py ____________________________________
import file mismatch:
imported module 'test_tiered_responder' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_tiered_responder.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_tiered_responder.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
___________________________________ ERROR collecting pc2_code/test_translation_cache.py ____________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_translation_cache.py", line 40
E       hit_ratio = (agent.cache_hits / (agent.cache_hits + agent.cache_misses) * 100 if (agent.cache_hits + agent.cache_misses) > 0 else 0
E                                                                                                                                         
E   SyntaxError: invalid syntax. Perhaps you forgot a comma?
__________________________________ ERROR collecting pc2_code/test_translation_pipeline.py __________________________________
import file mismatch:
imported module 'test_translation_pipeline' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_translation_pipeline.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_translation_pipeline.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
___________________________________ ERROR collecting pc2_code/test_translator_client.py ____________________________________
import file mismatch:
imported module 'test_translator_client' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_translator_client.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_translator_client.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
__________________________________ ERROR collecting pc2_code/test_translator_messages.py ___________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_translator_messages.py", line 64
E       }
E       ^
E   SyntaxError: f-string: closing parenthesis '}' does not match opening parenthesis '('
__________________________________ ERROR collecting pc2_code/test_unified_error_agent.py ___________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_unified_error_agent.py", line 9
E       sys.path.insert(0, str(current_dir)
E                      ^
E   SyntaxError: '(' was never closed
__________________________________ ERROR collecting pc2_code/test_unified_memory_agent.py __________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_unified_memory_agent.py", line 18
E       from pc2_code.agents.unified_memory_reasoning_agent import UnifiedMemoryReasoningAgent
E       ^^^^
E   SyntaxError: expected 'except' or 'finally' block
__________________________________ ERROR collecting pc2_code/test_unified_utils_agent.py ___________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_unified_utils_agent.py", line 9
E       sys.path.insert(0, str(current_dir)
E                      ^
E   SyntaxError: '(' was never closed
___________________________________ ERROR collecting pc2_code/test_unified_web_agent.py ____________________________________
import file mismatch:
imported module 'test_unified_web_agent' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/agents/archive/misc/test_unified_web_agent.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_unified_web_agent.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
_____________________________________ ERROR collecting pc2_code/test_voice_pipeline.py _____________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/test_voice_pipeline.py", line 64
E       else:
E       ^^^^
E   SyntaxError: invalid syntax
_________________________________ ERROR collecting pc2_code/agents/custom_tutoring_test.py _________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/pc2_code/agents/custom_tutoring_test.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'agents.custom_tutoring_test'
___________________________________ ERROR collecting pc2_code/agents/direct_emr_test.py ____________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/pc2_code/agents/direct_emr_test.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'agents.direct_emr_test'
_________________________________ ERROR collecting pc2_code/agents/test_compliant_agent.py _________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/pc2_code/agents/test_compliant_agent.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'agents.test_compliant_agent'
_______________________________ ERROR collecting pc2_code/agents/test_dreamworld_updates.py ________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/pc2_code/agents/test_dreamworld_updates.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'agents.test_dreamworld_updates'
________________________________ ERROR collecting pc2_code/agents/test_model_management.py _________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/pc2_code/agents/test_model_management.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'agents.test_model_management'
___________________________________ ERROR collecting pc2_code/agents/test_translator.py ____________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/pc2_code/agents/test_translator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'agents.test_translator'
________________________________ ERROR collecting pc2_code/agents/test_tutoring_feature.py _________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/pc2_code/agents/test_tutoring_feature.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'agents.test_tutoring_feature'
_________________________________ ERROR collecting pc2_code/agents/test_web_connections.py _________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/pc2_code/agents/test_web_connections.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'agents.test_web_connections'
____________________________ ERROR collecting pc2_code/agents/ForPC2/test_task_router_health.py ____________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/pc2_code/agents/ForPC2/test_task_router_health.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'agents.ForPC2'
________________ ERROR collecting pc2_code/agents/archive/memory_reasoning/test_unified_memory_reasoning.py ________________
import file mismatch:
imported module 'test_unified_memory_reasoning' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/agents/archive/memory_reasoning/test_unified_memory_reasoning.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/agents/archive/memory_reasoning/test_unified_memory_reasoning.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
___________________________ ERROR collecting pc2_code/agents/archive/misc/pub_translator_test.py ___________________________
import file mismatch:
imported module 'pub_translator_test' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/agents/archive/misc/pub_translator_test.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/agents/archive/misc/pub_translator_test.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
___________________________ ERROR collecting pc2_code/agents/archive/misc/test_main_pc_socket.py ___________________________
import file mismatch:
imported module 'test_main_pc_socket' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/agents/archive/misc/test_main_pc_socket.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/agents/archive/misc/test_main_pc_socket.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
____________________________ ERROR collecting pc2_code/agents/archive/misc/test_self_healing.py ____________________________
import file mismatch:
imported module 'test_self_healing' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/agents/archive/misc/test_self_healing.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/agents/archive/misc/test_self_healing.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
_________________________ ERROR collecting pc2_code/agents/archive/misc/test_unified_web_agent.py __________________________
import file mismatch:
imported module 'test_unified_web_agent' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/agents/archive/misc/test_unified_web_agent.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/agents/archive/misc/test_unified_web_agent.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
_________________________________ ERROR collecting pc2_code/scripts/test_pc2_containers.py _________________________________
import file mismatch:
imported module 'test_pc2_containers' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/scripts/test_pc2_containers.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/scripts/test_pc2_containers.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
_____________________________ ERROR collecting pc2_code/test_scripts/test_translator_health.py _____________________________
import file mismatch:
imported module 'test_translator_health' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/test_scripts/test_translator_health.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/test_scripts/test_translator_health.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
____________________________________ ERROR collecting pc2_code/tests/end_to_end_test.py ____________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/tests/end_to_end_test.py", line 27
E       sys.path.insert(0, str(project_root)
E                      ^
E   SyntaxError: '(' was never closed
_____________________________ ERROR collecting pc2_code/tests/test_consolidated_translator.py ______________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/tests/test_consolidated_translator.py", line 5
E       sys.path.append(str(Path(__file__).resolve().parent.parent)
E                      ^
E   SyntaxError: '(' was never closed
________________________________ ERROR collecting pc2_code/tests/test_memory_integration.py ________________________________
import file mismatch:
imported module 'test_memory_integration' has this __file__ attribute:
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/tests/test_memory_integration.py
which is not the same as the test file we want to collect:
  /home/haymayndz/AI_System_Monorepo/pc2_code/tests/test_memory_integration.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
__________________________ ERROR collecting pc2_code/tests/test_unified_memory_reasoning_agent.py __________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/pc2_code/tests/test_unified_memory_reasoning_agent.py", line 15
E       sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))
E                                          
E   SyntaxError: invalid syntax. Perhaps you forgot a comma?
_ ERROR collecting phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/simple_test.py _
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:992: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:241: in _call_with_frames_removed
    ???
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
<frozen importlib._bootstrap_external>:883: in exec_module
    ???
<frozen importlib._bootstrap>:241: in _call_with_frames_removed
    ???
phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/__init__.py:21: in <module>
    from .model_manager_suite import ModelManagerSuite
E     File "/home/haymayndz/AI_System_Monorepo/phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/model_manager_suite.py", line 116
E       logger = configure_logging(__name__)),
E                                           ^
E   SyntaxError: unmatched ')'
_ ERROR collecting phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/test_model_manager_suite.py _
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:992: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:241: in _call_with_frames_removed
    ???
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
<frozen importlib._bootstrap_external>:883: in exec_module
    ???
<frozen importlib._bootstrap>:241: in _call_with_frames_removed
    ???
phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/__init__.py:21: in <module>
    from .model_manager_suite import ModelManagerSuite
E     File "/home/haymayndz/AI_System_Monorepo/phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/model_manager_suite.py", line 116
E       logger = configure_logging(__name__)),
E                                           ^
E   SyntaxError: unmatched ')'
____________________________________ ERROR collecting scripts/test_batch_processing.py _____________________________________
../.local/lib/python3.10/site-packages/_pytest/runner.py:341: in from_call
    result: Optional[TResult] = func()
../.local/lib/python3.10/site-packages/_pytest/runner.py:372: in <lambda>
    call = CallInfo.from_call(lambda: list(collector.collect()), "collect")
../.local/lib/python3.10/site-packages/_pytest/python.py:531: in collect
    self._inject_setup_module_fixture()
../.local/lib/python3.10/site-packages/_pytest/python.py:545: in _inject_setup_module_fixture
    self.obj, ("setUpModule", "setup_module")
../.local/lib/python3.10/site-packages/_pytest/python.py:310: in obj
    self._obj = obj = self._getobj()
../.local/lib/python3.10/site-packages/_pytest/python.py:528: in _getobj
    return self._importtestmodule()
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:186: in exec_module
    exec(co, module.__dict__)
scripts/test_batch_processing.py:10: in <module>
    import numpy as np
../.local/lib/python3.10/site-packages/numpy/__init__.py:195: in <module>
    core.numerictypes.typeDict,
../.local/lib/python3.10/site-packages/numpy/core/__init__.py:161: in __getattr__
    raise AttributeError(f"Module {__name__!r} has no attribute {name!r}")
E   AttributeError: Module 'numpy.core' has no attribute 'numerictypes'
____________________________________ ERROR collecting scripts/test_graceful_shutdown.py ____________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/scripts/test_graceful_shutdown.py", line 83
E       print(f"
E             ^
E   SyntaxError: unterminated string literal (detected at line 83)
___________________________________ ERROR collecting scripts/test_memory_agent_health.py ___________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/scripts/test_memory_agent_health.py", line 32
E       logger = configure_logging(__name__)}")
E                                           ^
E   SyntaxError: unmatched '}'
_______________________________________ ERROR collecting scripts/test_performance.py _______________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/scripts/test_performance.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
scripts/test_performance.py:20: in <module>
    from common.utils.async_io import AsyncIOManager
common/utils/async_io.py:7: in <module>
    import aiofiles
E   ModuleNotFoundError: No module named 'aiofiles'
_________________________________ ERROR collecting scripts/test_secure_twin_connection.py __________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/scripts/test_secure_twin_connection.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
scripts/test_secure_twin_connection.py:27: in <module>
    from main_pc_code.agents.system_digital_twin import SystemDigitalTwin
E   ImportError: cannot import name 'SystemDigitalTwin' from 'main_pc_code.agents.system_digital_twin' (/home/haymayndz/AI_System_Monorepo/main_pc_code/agents/system_digital_twin.py)
____________________________________ ERROR collecting scripts/test_service_discovery.py ____________________________________
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:177: in exec_module
    source_stat, co = _rewrite_test(fn, self.config)
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:359: in _rewrite_test
    tree = ast.parse(source, filename=strfn)
/usr/lib/python3.10/ast.py:50: in parse
    return compile(source, filename, mode, flags,
E     File "/home/haymayndz/AI_System_Monorepo/scripts/test_service_discovery.py", line 37
E       logging.FileHandler(os.path.join(log_dir, 'test_service_discovery.log'))
E   IndentationError: unexpected indent
________________________________ ERROR collecting scripts/test_unified_tiered_responder.py _________________________________
../.local/lib/python3.10/site-packages/_pytest/runner.py:341: in from_call
    result: Optional[TResult] = func()
../.local/lib/python3.10/site-packages/_pytest/runner.py:372: in <lambda>
    call = CallInfo.from_call(lambda: list(collector.collect()), "collect")
../.local/lib/python3.10/site-packages/_pytest/python.py:531: in collect
    self._inject_setup_module_fixture()
../.local/lib/python3.10/site-packages/_pytest/python.py:545: in _inject_setup_module_fixture
    self.obj, ("setUpModule", "setup_module")
../.local/lib/python3.10/site-packages/_pytest/python.py:310: in obj
    self._obj = obj = self._getobj()
../.local/lib/python3.10/site-packages/_pytest/python.py:528: in _getobj
    return self._importtestmodule()
../.local/lib/python3.10/site-packages/_pytest/python.py:617: in _importtestmodule
    mod = import_path(self.path, mode=importmode, root=self.config.rootpath)
../.local/lib/python3.10/site-packages/_pytest/pathlib.py:567: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
<frozen importlib._bootstrap>:1050: in _gcd_import
    ???
<frozen importlib._bootstrap>:1027: in _find_and_load
    ???
<frozen importlib._bootstrap>:1006: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:688: in _load_unlocked
    ???
../.local/lib/python3.10/site-packages/_pytest/assertion/rewrite.py:186: in exec_module
    exec(co, module.__dict__)
scripts/test_unified_tiered_responder.py:17: in <module>
    from main_pc_code.agents.tiered_responder_unified import TieredResponder
main_pc_code/agents/tiered_responder_unified.py:23: in <module>
    import torch
../.local/lib/python3.10/site-packages/torch/__init__.py:465: in <module>
    for name in dir(_C):
E   NameError: name '_C' is not defined
________________________________ ERROR collecting servers/src/time/test/time_server_test.py ________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/servers/src/time/test/time_server_test.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
servers/src/time/test/time_server_test.py:2: in <module>
    from freezegun import freeze_time
E   ModuleNotFoundError: No module named 'freezegun'
______________________________________ ERROR collecting utils/mma_mms_parity_test.py _______________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/utils/mma_mms_parity_test.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'utils.mma_mms_parity_test'
_________________________________________ ERROR collecting utils/mms_smoke_test.py _________________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/utils/mms_smoke_test.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'utils.mms_smoke_test'
________________________________________ ERROR collecting utils/simple_zmq_test.py _________________________________________
ImportError while importing test module '/home/haymayndz/AI_System_Monorepo/utils/simple_zmq_test.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.10/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
E   ModuleNotFoundError: No module named 'utils.simple_zmq_test'
===================================================== warnings summary =====================================================
../../../usr/lib/python3/dist-packages/docker/credentials/utils.py:1
  /usr/lib/python3/dist-packages/docker/credentials/utils.py:1: DeprecationWarning: The distutils package is deprecated and slated for removal in Python 3.12. Use setuptools or check PEP 632 for potential alternatives
    import distutils.spawn

backups/unused_import_cleanup/pc2_code/agents/archive/memory_reasoning/test_unified_memory_reasoning.py:26
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/agents/archive/memory_reasoning/test_unified_memory_reasoning.py:26: PytestCollectionWarning: cannot collect test class 'TestClient' because it has a __init__ constructor (from: backups/unused_import_cleanup/pc2_code/agents/archive/memory_reasoning/test_unified_memory_reasoning.py)
    class TestClient:

backups/unused_import_cleanup/pc2_code/agents/archive/misc/test_unified_web_agent.py:26
  /home/haymayndz/AI_System_Monorepo/backups/unused_import_cleanup/pc2_code/agents/archive/misc/test_unified_web_agent.py:26: PytestCollectionWarning: cannot collect test class 'TestClient' because it has a __init__ constructor (from: backups/unused_import_cleanup/pc2_code/agents/archive/misc/test_unified_web_agent.py)
    class TestClient:

../.local/lib/python3.10/site-packages/pydantic/_internal/_config.py:323
../.local/lib/python3.10/site-packages/pydantic/_internal/_config.py:323
../.local/lib/python3.10/site-packages/pydantic/_internal/_config.py:323
../.local/lib/python3.10/site-packages/pydantic/_internal/_config.py:323
../.local/lib/python3.10/site-packages/pydantic/_internal/_config.py:323
../.local/lib/python3.10/site-packages/pydantic/_internal/_config.py:323
  /home/haymayndz/.local/lib/python3.10/site-packages/pydantic/_internal/_config.py:323: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.11/migration/
    warnings.warn(DEPRECATION_MESSAGE, DeprecationWarning)

../.local/lib/python3.10/site-packages/fastapi/openapi/models.py:55
  /home/haymayndz/.local/lib/python3.10/site-packages/fastapi/openapi/models.py:55: DeprecationWarning: `general_plain_validator_function` is deprecated, use `with_info_plain_validator_function` instead.
    return general_plain_validator_function(cls._validate)

../.local/lib/python3.10/site-packages/pydantic_core/core_schema.py:4298
  /home/haymayndz/.local/lib/python3.10/site-packages/pydantic_core/core_schema.py:4298: DeprecationWarning: `general_plain_validator_function` is deprecated, use `with_info_plain_validator_function` instead.
    warnings.warn(

../.local/lib/python3.10/site-packages/starlette/formparsers.py:10
  /home/haymayndz/.local/lib/python3.10/site-packages/starlette/formparsers.py:10: PendingDeprecationWarning: Please use `import python_multipart` instead.
    import multipart

main_pc_code/agents/system_digital_twin.py:37
  /home/haymayndz/AI_System_Monorepo/main_pc_code/agents/system_digital_twin.py:37: DeprecationWarning: Importing from main_pc_code.utils.service_discovery_client is deprecated. Use 'from common.service_mesh.unified_discovery_client import discover_service_async' for new code.
    from main_pc_code.utils.service_discovery_client import get_service_discovery_client

tests/test_phase_4_1_logging.py:54
  /home/haymayndz/AI_System_Monorepo/tests/test_phase_4_1_logging.py:54: PytestCollectionWarning: cannot collect test class 'TestStructuredLogging' because it has a __init__ constructor (from: tests/test_phase_4_1_logging.py)
    class TestStructuredLogging:

tests/test_phase_4_1_logging.py:164
  /home/haymayndz/AI_System_Monorepo/tests/test_phase_4_1_logging.py:164: PytestCollectionWarning: cannot collect test class 'TestAuditTrail' because it has a __init__ constructor (from: tests/test_phase_4_1_logging.py)
    class TestAuditTrail:

tests/test_phase_4_1_logging.py:341
  /home/haymayndz/AI_System_Monorepo/tests/test_phase_4_1_logging.py:341: PytestCollectionWarning: cannot collect test class 'TestLogAggregation' because it has a __init__ constructor (from: tests/test_phase_4_1_logging.py)
    class TestLogAggregation:

tests/e2e/test_dialogue_flow.py:42
  /home/haymayndz/AI_System_Monorepo/tests/e2e/test_dialogue_flow.py:42: PytestUnknownMarkWarning: Unknown pytest.mark.timeout - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.timeout(30)

tests/e2e/test_dialogue_flow.py:68
  /home/haymayndz/AI_System_Monorepo/tests/e2e/test_dialogue_flow.py:68: PytestUnknownMarkWarning: Unknown pytest.mark.timeout - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.timeout(45)

tests/e2e/test_dialogue_flow.py:100
  /home/haymayndz/AI_System_Monorepo/tests/e2e/test_dialogue_flow.py:100: PytestUnknownMarkWarning: Unknown pytest.mark.timeout - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.timeout(60)

tests/e2e/test_dialogue_flow.py:135
  /home/haymayndz/AI_System_Monorepo/tests/e2e/test_dialogue_flow.py:135: PytestUnknownMarkWarning: Unknown pytest.mark.timeout - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.timeout(30)

tests/smoke_tests/test_smoke_tonedetector.py:9
  /home/haymayndz/AI_System_Monorepo/tests/smoke_tests/test_smoke_tonedetector.py:9: PytestUnknownMarkWarning: Unknown pytest.mark.smoke - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.smoke

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================================= short test summary info ==================================================
ERROR test_periodic_sync.py
ERROR agents/simple_smart_home_test.py
ERROR backups/unused_import_cleanup/main_pc_code/agents/model_manager_agent_test.py
ERROR backups/unused_import_cleanup/main_pc_code/agents/test_meta_cognition.py
ERROR backups/unused_import_cleanup/main_pc_code/agents/_trash_2025-06-13/archive/misc/basic_audio_test.py
ERROR backups/unused_import_cleanup/main_pc_code/agents/_trash_2025-06-13/archive/misc/simple_whisper_test.py
ERROR backups/unused_import_cleanup/main_pc_code/agents/_trash_2025-06-13/archive/misc/test_audio_devices.py
ERROR backups/unused_import_cleanup/main_pc_code/agents/_trash_2025-06-13/archive/misc/test_generator_agent.py
ERROR backups/unused_import_cleanup/main_pc_code/agents/_trash_2025-06-13/archive/misc/trigger_test.py
ERROR backups/unused_import_cleanup/main_pc_code/agents/_trash_2025-06-13/archive/misc/whisper_test.py
ERROR backups/unused_import_cleanup/main_pc_code/scripts/run_voice_flow_test.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/end_to_end_test.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_cross_machine_registration.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_integration_model_manager_api.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_model_client.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_model_manager_api.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_no_direct_model_load.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_phase5_integration.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_pilot_migration_sla.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_unified_planning_agent.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_voice_command_flow.py
ERROR backups/unused_import_cleanup/main_pc_code/tests/test_vram_optimizer_agent.py
ERROR backups/unused_import_cleanup/pc2_code/test_health_rep.py - zmq.error.Again: Resource temporarily unavailable
ERROR backups/unused_import_cleanup/pc2_code/test_nllb_translation.py
ERROR backups/unused_import_cleanup/pc2_code/test_proactive_context_monitor.py
ERROR backups/unused_import_cleanup/pc2_code/test_rca_agent.py - SystemExit: 1
ERROR backups/unused_import_cleanup/pc2_code/test_self_healing_agent.py
ERROR backups/unused_import_cleanup/pc2_code/test_translation_cache.py
ERROR backups/unused_import_cleanup/pc2_code/test_translator_messages.py - KeyboardInterrupt
ERROR backups/unused_import_cleanup/pc2_code/test_unified_error_agent.py
ERROR backups/unused_import_cleanup/pc2_code/test_unified_memory_agent.py
ERROR backups/unused_import_cleanup/pc2_code/test_unified_utils_agent.py - SystemExit: 1
ERROR backups/unused_import_cleanup/pc2_code/test_unified_web_agent.py - KeyboardInterrupt
ERROR backups/unused_import_cleanup/pc2_code/test_voice_pipeline.py - KeyboardInterrupt
ERROR backups/unused_import_cleanup/pc2_code/agents/custom_tutoring_test.py
ERROR backups/unused_import_cleanup/pc2_code/agents/direct_emr_test.py
ERROR backups/unused_import_cleanup/pc2_code/agents/test_compliant_agent.py
ERROR backups/unused_import_cleanup/pc2_code/agents/test_dreamworld_updates.py
ERROR backups/unused_import_cleanup/pc2_code/agents/test_model_management.py
ERROR backups/unused_import_cleanup/pc2_code/agents/test_translator.py
ERROR backups/unused_import_cleanup/pc2_code/agents/test_tutoring_feature.py
ERROR backups/unused_import_cleanup/pc2_code/agents/test_web_connections.py
ERROR backups/unused_import_cleanup/pc2_code/agents/ForPC2/test_task_router_health.py
ERROR backups/unused_import_cleanup/pc2_code/tests/end_to_end_test.py
ERROR backups/unused_import_cleanup/pc2_code/tests/test_consolidated_translator.py
ERROR backups/unused_import_cleanup/pc2_code/tests/test_unified_memory_reasoning_agent.py
ERROR docker_backup_not_in_startup_config/pc2_infra_core/test_imports.py - SystemExit: 1
ERROR main_pc_code/NEWMUSTFOLLOW/test_streaming_audio.py
ERROR main_pc_code/agents/model_manager_agent_test.py
ERROR main_pc_code/agents/test_meta_cognition.py
ERROR main_pc_code/agents/_trash_2025-06-13/archive/misc/basic_audio_test.py
ERROR main_pc_code/agents/_trash_2025-06-13/archive/misc/simple_whisper_test.py
ERROR main_pc_code/agents/_trash_2025-06-13/archive/misc/test_audio_devices.py
ERROR main_pc_code/agents/_trash_2025-06-13/archive/misc/test_generator_agent.py
ERROR main_pc_code/agents/_trash_2025-06-13/archive/misc/trigger_test.py
ERROR main_pc_code/agents/_trash_2025-06-13/archive/misc/whisper_test.py - SystemExit: 1
ERROR main_pc_code/scripts/run_voice_flow_test.py
ERROR main_pc_code/scripts/test_pc2_sdt_connection.py
ERROR main_pc_code/scripts/test_script.py
ERROR main_pc_code/scripts/test_sdt_improved.py
ERROR main_pc_code/scripts/test_sdt_local_connection.py
ERROR main_pc_code/scripts/test_task_router_health.py
ERROR main_pc_code/tests/end_to_end_test.py
ERROR main_pc_code/tests/test_cross_machine_registration.py
ERROR main_pc_code/tests/test_integration_model_manager_api.py
ERROR main_pc_code/tests/test_model_client.py
ERROR main_pc_code/tests/test_model_manager_api.py
ERROR main_pc_code/tests/test_no_direct_model_load.py
ERROR main_pc_code/tests/test_phase5_integration.py
ERROR main_pc_code/tests/test_pilot_migration_sla.py
ERROR main_pc_code/tests/test_unified_planning_agent.py
ERROR main_pc_code/tests/test_voice_command_flow.py
ERROR main_pc_code/tests/test_vram_optimizer_agent.py
ERROR main_pc_code/utils/mma_mms_parity_test.py
ERROR main_pc_code/utils/mms_smoke_test.py
ERROR main_pc_code/utils/simple_zmq_test.py
ERROR pc2_code/test_health_rep.py
ERROR pc2_code/test_nllb_translation.py
ERROR pc2_code/test_ollama.py
ERROR pc2_code/test_performance_monitor.py
ERROR pc2_code/test_performance_monitor_health.py
ERROR pc2_code/test_phi_adapter_advanced.py
ERROR pc2_code/test_proactive_context_monitor.py
ERROR pc2_code/test_rca_agent.py
ERROR pc2_code/test_self_healing_agent.py
ERROR pc2_code/test_simple_agent.py
ERROR pc2_code/test_taglish.py
ERROR pc2_code/test_tiered_responder.py
ERROR pc2_code/test_translation_cache.py
ERROR pc2_code/test_translation_pipeline.py
ERROR pc2_code/test_translator_client.py
ERROR pc2_code/test_translator_messages.py
ERROR pc2_code/test_unified_error_agent.py
ERROR pc2_code/test_unified_memory_agent.py
ERROR pc2_code/test_unified_utils_agent.py
ERROR pc2_code/test_unified_web_agent.py
ERROR pc2_code/test_voice_pipeline.py
ERROR pc2_code/agents/custom_tutoring_test.py
ERROR pc2_code/agents/direct_emr_test.py
ERROR pc2_code/agents/test_compliant_agent.py
ERROR pc2_code/agents/test_dreamworld_updates.py
ERROR pc2_code/agents/test_model_management.py
ERROR pc2_code/agents/test_translator.py
ERROR pc2_code/agents/test_tutoring_feature.py
ERROR pc2_code/agents/test_web_connections.py
ERROR pc2_code/agents/ForPC2/test_task_router_health.py
ERROR pc2_code/agents/archive/memory_reasoning/test_unified_memory_reasoning.py
ERROR pc2_code/agents/archive/misc/pub_translator_test.py
ERROR pc2_code/agents/archive/misc/test_main_pc_socket.py
ERROR pc2_code/agents/archive/misc/test_self_healing.py
ERROR pc2_code/agents/archive/misc/test_unified_web_agent.py
ERROR pc2_code/scripts/test_pc2_containers.py
ERROR pc2_code/test_scripts/test_translator_health.py
ERROR pc2_code/tests/end_to_end_test.py
ERROR pc2_code/tests/test_consolidated_translator.py
ERROR pc2_code/tests/test_memory_integration.py
ERROR pc2_code/tests/test_unified_memory_reasoning_agent.py
ERROR phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/simple_test.py
ERROR phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/test_model_manager_suite.py
ERROR scripts/test_batch_processing.py - AttributeError: Module 'numpy.core' has no attribute 'numerictypes'
ERROR scripts/test_graceful_shutdown.py
ERROR scripts/test_memory_agent_health.py
ERROR scripts/test_performance.py
ERROR scripts/test_secure_twin_connection.py
ERROR scripts/test_service_discovery.py
ERROR scripts/test_unified_tiered_responder.py - NameError: name '_C' is not defined
ERROR servers/src/time/test/time_server_test.py
ERROR utils/mma_mms_parity_test.py
ERROR utils/mms_smoke_test.py
ERROR utils/simple_zmq_test.py
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! Interrupted: 130 errors during collection !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
21 warnings, 130 errors in 880.70s (0:14:40)
--- Logging error ---
Traceback (most recent call last):
  File "/usr/lib/python3.10/logging/__init__.py", line 1103, in emit
    stream.write(msg + self.terminator)
ValueError: I/O operation on closed file.
Call stack:
  File "/home/haymayndz/AI_System_Monorepo/auto_sync_manager.py", line 63, in _sync_on_exit
    logger.info("🔄 Auto-syncing on session exit...")
Message: '🔄 Auto-syncing on session exit...'
Arguments: ()
--- Logging error ---
Traceback (most recent call last):
  File "/usr/lib/python3.10/logging/__init__.py", line 1103, in emit
    stream.write(msg + self.terminator)
ValueError: I/O operation on closed file.
Call stack:
  File "/home/haymayndz/AI_System_Monorepo/auto_sync_manager.py", line 64, in _sync_on_exit
    self.sync_all_states()
  File "/home/haymayndz/AI_System_Monorepo/auto_sync_manager.py", line 81, in sync_all_states
    logger.info("✅ Auto-sync completed successfully")
Message: '✅ Auto-sync completed successfully'
Arguments: ()
haymayndz@DESKTOP-GC2ET1O:~/AI_System_Monorepo$ 
