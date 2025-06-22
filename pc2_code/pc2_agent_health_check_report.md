# PC2 Agent Health Check Report

## HEALTHY AGENTS
- agents/ForPC2/rca_agent.py
- agents/ForPC2/system_digital_twin.py
- agents/ForPC2/proactive_context_monitor.py
- agents/ForPC2/unified_utils_agent.py
- agents/ForPC2/UnifiedErrorAgent.py
- agents/ForPC2/AuthenticationAgent.py
- agents/core_agents/tutoring_service_agent.py
- pc2_launcher.py
- pc2_tinyllama_health_checker.py
- pc2_translator_health_checker.py
- healthcheck_pc2_services.py
- pc2_phase1_validation.py

## FAILED AGENTS
- agents/ForPC2/health_monitor.py: FAILED
  Error Log:
    ```
Traceback (most recent call last):
  File "D:\DISKARTE\Voice Assistant\agents\ForPC2\health_monitor.py", line 23, in <module>
    from agents.core_agents.http_server import setup_health_check_server
ModuleNotFoundError: No module named 'agents'
    ```
- agents/ForPC2/unified_monitoring.py: FAILED
  Error Log:
    ```
Traceback (most recent call last):
  File "D:\DISKARTE\Voice Assistant\agents\ForPC2\unified_monitoring.py", line 10, in <module>
    from src.core.base_agent import BaseAgent
ModuleNotFoundError: No module named 'src'
    ```
- agents/core_agents/http_server.py: FAILED
  Error Log:
    ```

    ```
- agents/core_agents/tutoring_agent.py: FAILED
  Error Log:
    ```
Traceback (most recent call last):
  File "D:\DISKARTE\Voice Assistant\agents\core_agents\tutoring_agent.py", line 7, in <module>
    from port_config import ENHANCED_MODEL_ROUTER_PORT
ModuleNotFoundError: No module named 'port_config'
    ```
- agents/core_agents/LearningAdjusterAgent.py: FAILED
  Error Log:
    ```

    ```
- pc2_gpu_benchmark.py: FAILED
  Error Log:
    ```
Traceback (most recent call last):
  File "D:\DISKARTE\Voice Assistant\pc2_gpu_benchmark.py", line 132, in <module>
    main()
  File "D:\DISKARTE\Voice Assistant\pc2_gpu_benchmark.py", line 128, in main
    print("\u274c CUDA is not available. PyTorch is running on CPU only.")
  File "C:\Users\63956\AppData\Local\Programs\Python\Python310\lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
UnicodeEncodeError: 'charmap' codec can't encode character '\u274c' in position 0: character maps to <undefined>
    ```
- pc2_service_manager.py: FAILED
  Error Log:
    ```

    ```
- pc2_translator_benchmark.py: FAILED
  Error Log:
    ```
Traceback (most recent call last):
  File "D:\DISKARTE\Voice Assistant\pc2_translator_benchmark.py", line 86, in connect_to_translator
    print(f"{Colors.GREEN}\u2713 Connected to translator agent on port 5563{Colors.ENDC}")
  File "C:\Users\63956\AppData\Local\Programs\Python\Python310\lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 5: character maps to <undefined>

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "D:\DISKARTE\Voice Assistant\pc2_translator_benchmark.py", line 269, in <module>
    run_benchmark()
  File "D:\DISKARTE\Voice Assistant\pc2_translator_benchmark.py", line 132, in run_benchmark
    context, socket = connect_to_translator()
  File "D:\DISKARTE\Voice Assistant\pc2_translator_benchmark.py", line 89, in connect_to_translator
    print(f"{Colors.RED}\u2717 Failed to connect to translator agent: {e}{Colors.ENDC}")
  File "C:\Users\63956\AppData\Local\Programs\Python\Python310\lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
UnicodeEncodeError: 'charmap' codec can't encode character '\u2717' in position 5: character maps to <undefined>
    ```
- pc2_health_check.py: FAILED
  Error Log:
    ```

    ```
- start_translator_service.py: FAILED
  Error Log:
    ```

    ```
- system_launcher.py: FAILED
  Error Log:
    ```
2025-06-19 18:05:33,779 - SystemLauncher - INFO - Starting Voice Assistant System...
2025-06-19 18:05:33,779 - SystemLauncher - INFO - Starting core_models group...
2025-06-19 18:05:33,802 - SystemLauncher - INFO - Started TinyLlama Service (PID: 32632)
2025-06-19 18:05:40,819 - SystemLauncher - INFO - Starting memory group...
2025-06-19 18:05:40,819 - SystemLauncher - ERROR - Cannot start memory - dependency core_models not running
2025-06-19 18:05:40,819 - SystemLauncher - ERROR - Failed to start memory group
2025-06-19 18:05:40,819 - SystemLauncher - INFO - System shutdown complete
    ```
- verify_pc2_services_fixed.py: FAILED
  Error Log:
    ```
Traceback (most recent call last):
  File "D:\DISKARTE\Voice Assistant\verify_pc2_services_fixed.py", line 441, in <module>
    main()
  File "D:\DISKARTE\Voice Assistant\verify_pc2_services_fixed.py", line 319, in main
    print_service_result(result)
  File "D:\DISKARTE\Voice Assistant\verify_pc2_services_fixed.py", line 234, in print_service_result
    print(f"\n{Fore.CYAN}\u25a0 {result['name']} (Port {result['port']}){Style.RESET_ALL}")
  File "C:\Users\63956\AppData\Local\Programs\Python\Python310\lib\site-packages\colorama\ansitowin32.py", line 47, in write
    self.__convertor.write(text)
  File "C:\Users\63956\AppData\Local\Programs\Python\Python310\lib\site-packages\colorama\ansitowin32.py", line 177, in write
    self.write_and_convert(text)
  File "C:\Users\63956\AppData\Local\Programs\Python\Python310\lib\site-packages\colorama\ansitowin32.py", line 202, in write_and_convert
    self.write_plain_text(text, cursor, start)
  File "C:\Users\63956\AppData\Local\Programs\Python\Python310\lib\site-packages\colorama\ansitowin32.py", line 210, in write_plain_text
    self.wrapped.write(text[start:end])
  File "C:\Users\63956\AppData\Local\Programs\Python\Python310\lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
UnicodeEncodeError: 'charmap' codec can't encode character '\u25a0' in position 0: character maps to <undefined>
    ```
- verify_pc2_target_config.py: FAILED
  Error Log:
    ```
Traceback (most recent call last):
  File "D:\DISKARTE\Voice Assistant\verify_pc2_target_config.py", line 367, in <module>
    main()
  File "D:\DISKARTE\Voice Assistant\verify_pc2_target_config.py", line 341, in main
    print_service_status(service, result)
  File "D:\DISKARTE\Voice Assistant\verify_pc2_target_config.py", line 255, in print_service_status
    print(f"\n{Colors.BOLD}\u25a0 {name} (Port {port}){Colors.ENDC}")
  File "C:\Users\63956\AppData\Local\Programs\Python\Python310\lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
UnicodeEncodeError: 'charmap' codec can't encode character '\u25a0' in position 6: character maps to <undefined>
    ```
