import os 
import subprocess 
print("Setting up Python environment...") 
venv_path = os.path.join(os.getcwd(), "venv") 
if not os.path.exists(venv_path): 
    print("Creating virtual environment...") 
    subprocess.run(["python", "-m", "venv", "venv"]) 
activate_script = os.path.join(venv_path, "Scripts", "activate.bat") 
print("Installing required packages...") 
subprocess.run(["cmd", "/c", f"{activate_script} && pip install -r requirements.txt"]) 
print("Installing additional packages...") 
subprocess.run(["cmd", "/c", f"{activate_script} && pip install pyzmq torch torchvision torchaudio psutil"]) 
print("Setup complete!") 
