# MVS Installation Guide

This guide provides step-by-step instructions for installing and setting up the Minimal Viable System (MVS).

## System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended) or WSL2
- **Python**: 3.8 or higher
- **RAM**: Minimum 8GB, recommended 16GB+
- **Storage**: 10GB+ free space
- **GPU**: NVIDIA GPU with CUDA support (optional but recommended)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/AI_System_Monorepo.git
cd AI_System_Monorepo
```

### 2. Set Up Python Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
# Install basic dependencies
pip install -r requirements.txt

# If requirements.txt doesn't exist, install the minimum required packages
pip install zmq pyyaml psutil torch numpy
```

### 4. Set Up Directory Structure

```bash
# Create necessary directories
mkdir -p logs data models cache certificates
```

### 5. Configure the MVS

The MVS configuration is stored in `main_pc_code/config/minimal_system_config.yaml`. Review this file to ensure it matches your environment.

Key configuration items to check:
- Agent script paths
- Port numbers (ensure they don't conflict with other services)
- Host settings (usually 0.0.0.0 for all interfaces)

### 6. Set Up Environment Variables

The MVS requires several environment variables. These are set automatically by the `run_mvs.sh` script, but you may need to modify them for your environment.

Edit `main_pc_code/NEWMUSTFOLLOW/run_mvs.sh` and adjust the following variables if needed:
- `MAIN_PC_IP`: IP address of the main PC
- `PC2_IP`: IP address of the second PC (if applicable)
- `BIND_ADDRESS`: Address to bind services to (usually 0.0.0.0)
- `MODEL_DIR`: Directory for AI models
- `MAX_MEMORY_MB` and `MAX_VRAM_MB`: Resource limits

### 7. Install CUDA (Optional but Recommended)

If you have an NVIDIA GPU, install CUDA to enable GPU acceleration:

1. Check CUDA compatibility with your GPU: [NVIDIA CUDA GPUs](https://developer.nvidia.com/cuda-gpus)
2. Download and install CUDA Toolkit: [CUDA Downloads](https://developer.nvidia.com/cuda-downloads)
3. Install PyTorch with CUDA support:
   ```bash
   pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu116
   ```
   (Replace cu116 with your CUDA version)

### 8. Download Required Models

Some agents require pre-trained models. Create a `models` directory and download the necessary models:

```bash
mkdir -p models
# Download models (specific commands depend on your setup)
```

### 9. Make Scripts Executable

```bash
chmod +x main_pc_code/NEWMUSTFOLLOW/run_mvs.sh
chmod +x main_pc_code/NEWMUSTFOLLOW/check_mvs_health.py
chmod +x main_pc_code/NEWMUSTFOLLOW/start_mvs.py
```

## Running the MVS

### Option 1: Using the Shell Script

```bash
./main_pc_code/NEWMUSTFOLLOW/run_mvs.sh
```

### Option 2: Using the Python Script (Recommended)

```bash
python main_pc_code/NEWMUSTFOLLOW/start_mvs.py
```

### Checking MVS Health

```bash
python main_pc_code/NEWMUSTFOLLOW/check_mvs_health.py
```

## Troubleshooting

If you encounter issues during installation or startup, refer to `main_pc_code/NEWMUSTFOLLOW/mvs_troubleshooting.md` for common problems and solutions.

### Common Installation Issues

1. **ZMQ Installation Fails**
   ```bash
   # Install ZMQ development libraries
   sudo apt-get install libzmq3-dev
   pip install pyzmq
   ```

2. **CUDA Not Found**
   ```bash
   # Check CUDA installation
   nvcc --version
   # If not found, add to PATH
   export PATH=/usr/local/cuda/bin:$PATH
   ```

3. **Port Conflicts**
   ```bash
   # Check if ports are already in use
   sudo netstat -tulpn | grep LISTEN
   # Kill processes using conflicting ports
   kill -9 <PID>
   ```

## Next Steps

After successful installation:

1. Test each agent individually
2. Run the complete MVS
3. Monitor agent health and logs
4. Expand the system by adding more agents

For more detailed information, refer to `main_pc_code/NEWMUSTFOLLOW/PROJECT_CONTINUATION_GUIDE.md`. 