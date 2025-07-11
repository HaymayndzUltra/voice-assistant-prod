import subprocess
import os

def test_no_stray_from_pretrained_calls():
    """
    This test fails if `from_pretrained(` is found in any file outside
    of the approved model manager agents. This enforces our new architecture
    where all model loading is centralized.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    main_pc_code_path = os.path.join(repo_root, 'main_pc_code')

    # The only two agents allowed to load models directly.
    allowed_dirs = [
        os.path.join(main_pc_code_path, 'agents', 'model_manager_agent.py'),
        os.path.join(main_pc_code_path, 'agents', 'gguf_model_manager.py')
    ]

    # Construct the grep command
    # We search for the string and then use grep -v to exclude the allowed files.
    # If the final output has any lines, it means a violation was found.
    search_command = f'grep -r "from_pretrained(" {main_pc_code_path}'
    exclude_command = ' | grep -v -f /dev/null' # Start with a no-op exclude
    for allowed_path in allowed_dirs:
        exclude_command += f' | grep -v "{allowed_path}"'

    full_command = f'{search_command}{exclude_command}'

    # Run the command
    result = subprocess.run(full_command, shell=True, capture_output=True, text=True)

    # If grep finds matches, it returns 0. If it finds nothing, it returns 1.
    # We want it to find nothing.
    if result.returncode == 0 and result.stdout:
        assert False, f"Found disallowed 'from_pretrained' calls in:\n{result.stdout}"

    # If grep finds nothing (exit code 1), the test passes.
    # If there's an error in the command itself, this will also fail.
    assert result.returncode == 1 or (result.returncode == 0 and not result.stdout), "Test passed: No stray model loading calls found." 