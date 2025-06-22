# Launcher script for NLLB Translator Agent
import os
import sys
import subprocess

TRANSLATOR_PATH = os.path.join('translation_components', 'nllb_translator.py')

if not os.path.exists(TRANSLATOR_PATH):
    print(f"ERROR: {TRANSLATOR_PATH} not found.")
    sys.exit(1)

print("Starting NLLB Translator Agent...")
subprocess.run([sys.executable, TRANSLATOR_PATH])
