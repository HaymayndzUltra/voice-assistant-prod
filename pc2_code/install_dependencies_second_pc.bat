@echo off
echo Creating installation files for Second PC...

REM Create install_deps.py script for manual copying
echo import os > "second_pc_install_deps.py"
echo import subprocess >> "second_pc_install_deps.py"
echo print("Installing Voice Assistant dependencies...") >> "second_pc_install_deps.py"
echo venv_path = os.path.join(os.getcwd(), "venv") >> "second_pc_install_deps.py"
echo activate_script = os.path.join(venv_path, "Scripts", "activate.bat") >> "second_pc_install_deps.py"
echo packages = [ >> "second_pc_install_deps.py"
echo     "pyzmq", >> "second_pc_install_deps.py"
echo     "torch", >> "second_pc_install_deps.py"
echo     "torchaudio", >> "second_pc_install_deps.py"
echo     "torchvision", >> "second_pc_install_deps.py"
echo     "psutil", >> "second_pc_install_deps.py"
echo     "numpy", >> "second_pc_install_deps.py"
echo     "faster-whisper", >> "second_pc_install_deps.py"
echo     "langdetect", >> "second_pc_install_deps.py"
echo     "TTS", >> "second_pc_install_deps.py"
echo     "sounddevice", >> "second_pc_install_deps.py"
echo     "soundfile", >> "second_pc_install_deps.py"
echo     "ctranslate2", >> "second_pc_install_deps.py"
echo     "transformers", >> "second_pc_install_deps.py"
echo     "sentencepiece", >> "second_pc_install_deps.py"
echo     "insightface", >> "second_pc_install_deps.py"
echo     "opencv-python", >> "second_pc_install_deps.py"
echo ] >> "second_pc_install_deps.py"
echo print("Installing packages...") >> "second_pc_install_deps.py"
echo for package in packages: >> "second_pc_install_deps.py"
echo     print(f"Installing {package}...") >> "second_pc_install_deps.py"
echo     try: >> "second_pc_install_deps.py"
echo         subprocess.run([sys.executable, "-m", "pip", "install", package], check=True) >> "second_pc_install_deps.py"
echo         print(f"Successfully installed {package}") >> "second_pc_install_deps.py"
echo     except Exception as e: >> "second_pc_install_deps.py"
echo         print(f"Error installing {package}: {e}") >> "second_pc_install_deps.py"
echo print("All dependencies installed!") >> "second_pc_install_deps.py"

REM Create batch file to run install_deps.py
echo @echo off > "second_pc_install.bat"
echo D: >> "second_pc_install.bat"
echo cd \DISKARTE\Voice Assistant >> "second_pc_install.bat"
echo call venv\Scripts\activate.bat >> "second_pc_install.bat"
echo python second_pc_install_deps.py >> "second_pc_install.bat"
echo pause >> "second_pc_install.bat"

echo Files created successfully.
echo.
echo Please manually copy these files to your Second PC:
echo 1. second_pc_install_deps.py
echo 2. second_pc_install.bat
echo.
echo Then on your Second PC, run:
echo D:\DISKARTE\Voice Assistant\second_pc_install.bat
echo.
pause
