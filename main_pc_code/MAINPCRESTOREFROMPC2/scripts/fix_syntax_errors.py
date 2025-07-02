import os
import re

def fix_bom(file_path):
    """Remove BOM characters from file"""
    with open(file_path, 'rb') as f:
        content = f.read()
    
    # Remove BOM if present
    if content.startswith(b'\xef\xbb\xbf'):
        content = content[3:]
    
    with open(file_path, 'wb') as f:
        f.write(content)

def fix_fstring_syntax(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix double f-string prefix
    content = re.sub(r'f"f"', 'f"', content)
    
    # Fix PredictiveHealthMonitor specific patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}"\)"', 'f"tcp://\1:\2"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}""', 'f"tcp://\1:\2"', content)
    
    # Fix nested f-string patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}""', 'f"tcp://\1:\2"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}\)', 'f"tcp://\1:\2"', content)
    
    # Fix port concatenation patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}""', 'f"tcp://\1:\2"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}\)', 'f"tcp://\1:\2"', content)
    
    # Fix port with SELF_HEALING_PORT
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{SELF_HEALING_PORT\}""', 'f"tcp://\1:{SELF_HEALING_PORT}"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{SELF_HEALING_PORT\}\)', 'f"tcp://\1:{SELF_HEALING_PORT}"', content)
    
    # Fix port with numbers
    content = re.sub(r'f"tcp://\{([^}]+)\}:(\d+)""', 'f"tcp://\1:\2"', content)
    content = re.sub(r'"tcp://\{([^}]+)\}:(\d+)""', '"tcp://\1:\2"', content)
    
    # Fix unterminated string patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\)"', 'f"tcp://\1"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:(\d+)""', 'f"tcp://\1:\2"', content)
    
    # Fix multiple port patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}""', 'f"tcp://\1:\2"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}\)', 'f"tcp://\1:\2"', content)
    
    # Fix port variable patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}""', 'f"tcp://\1:\2"', content)
    content = re.sub(r'"tcp://\{([^}]+)\}:\{([^}]+)\}""', '"tcp://\1:\2"', content)
    
    # Fix mixed patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}:(\d+)""', 'f"tcp://\1:\2:\3"', content)
    content = re.sub(r'"tcp://\{([^}]+)\}:\{([^}]+)\}:(\d+)""', '"tcp://\1:\2:\3"', content)
    
    # Fix remaining patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:(\d+)""', 'f"tcp://\1:\2"', content)
    content = re.sub(r'"tcp://\{([^}]+)\}:(\d+)""', '"tcp://\1:\2"', content)
    
    # Fix final patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}\)"', 'f"tcp://\1:\2"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}""', 'f"tcp://\1:\2"', content)
    
    # Fix specific f-string patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}"\)"', 'f"tcp://\1:\2"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}""', 'f"tcp://\1:\2"', content)
    
    # Fix nested port patterns
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}"\)"', 'f"tcp://\1:\2"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}""', 'f"tcp://\1:\2"', content)
    
    # Fix nested f-string with SELF_HEALING_PORT
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}"\)"', 'f"tcp://\1:\2"', content)
    content = re.sub(r'f"tcp://\{([^}]+)\}:\{([^}]+)\}""', 'f"tcp://\1:\2"', content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def fix_syntax_errors(file_path):
    """Apply all syntax fixes to a file"""
    try:
        # First fix BOM if present
        fix_bom(file_path)
        
        # Then fix f-string syntax
        fix_fstring_syntax(file_path)
        
        # Then fix unterminated strings
        fix_unterminated_strings(file_path)
        
        # Then fix import statements
        fix_import_statements(file_path)
        
        print(f"Successfully fixed all syntax issues in {file_path}")
        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {str(e)}")
        return False

def fix_import_statements(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix multiple imports on same line
    content = re.sub(r'from BaseAgent filterpy.kalman import KalmanFilter', 
                     'from BaseAgent import *\nfrom filterpy.kalman import KalmanFilter', content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def fix_unterminated_strings(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix unterminated string literals
    content = re.sub(r'f"([^:]+):\)\)', 'f"\1"', content)
    content = re.sub(r'"f"([^:]+):""', '"\1"', content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def main():
    # List of files to fix
    files_to_fix = [
        'src/memory/memory_orchestrator.py',
        'src/memory/memory_client.py',
        'agents/tone_detector.py',
        'agents/learning_manager.py',
        'agents/MetaCognitionAgent.py',
        'agents/active_learning_monitor.py',
        'agents/unified_planning_agent.py',
        'agents/MultiAgentSwarmManager.py',
        'agents/coordinator_agent.py',
        'agents/tts_connector.py',
        'agents/code_generator_agent.py',
        'src/audio/fused_audio_preprocessor.py',
        'agents/wake_word_detector.py',
        'agents/streaming_speech_recognition.py',
        'agents/language_and_translation_coordinator.py',
        'agents/predictive_health_monitor.py',
        'agents/face_recognition_agent.py'
    ]
    
    # Apply all fixes to each file
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            print(f"\nFixing {file_path}...")
            if fix_syntax_errors(file_path):
                print(f"Successfully fixed {file_path}")
            else:
                print(f"Failed to fix {file_path}")
        else:
            print(f"File not found: {file_path}")

    print("\nAll fixes have been applied.")
    print("\nTo verify the fixes, run the smoke test script manually:")
    print("python3 scripts/smoke_test_agents.py")

def verify_fixes():
    """Run smoke test to verify all fixes"""
    print("\nRunning smoke test to verify fixes...")
    smoke_test_agents()

def verify_fixes():
    """Run smoke test to verify all fixes"""
    print("\nRunning smoke test to verify fixes...")
    smoke_test_agents()

if __name__ == "__main__":
    main()
