import sys
import subprocess

print("Installing Voice Assistant dependencies...")

# Check if we're in a virtual environment
in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
if not in_venv:
    print("WARNING: Not running in a virtual environment. It's recommended to run this script inside a virtual environment.")
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
        print("Installation aborted.")
        sys.exit(1)

# List of required packages
packages = [
    "pyzmq",
    "torch",
    "torchaudio",
    "torchvision",
    "psutil",
    "numpy",
    "faster-whisper",
    "langdetect",
    "TTS",
    "sounddevice",
    "soundfile",
    "ctranslate2",
    "transformers",
    "sentencepiece",
    "insightface",
    "opencv-python",
]

# Install each package
print("Installing packages...")
for package in packages:
    print(f"Installing {package}...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
        print(f"Successfully installed {package}")
    except Exception as e:
        print(f"Error installing {package}: {e}")

print("\nAll dependencies installed!")
print("You can now run the Voice Assistant with:")
print("python agents\\orchestrator.py --distributed --machine-id second_pc")
