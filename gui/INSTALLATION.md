# 🎯 Modern GUI Control Center - Installation Guide

## 🚀 Complete Installation Instructions

### Prerequisites Check
```bash
# Check Python version (requires 3.10+)
python3 --version

# Check if tkinter is available
python3 -c "import tkinter; print('✅ tkinter available')"
```

### System Dependencies

#### Ubuntu/Debian
```bash
# Install tkinter and development tools
sudo apt-get update
sudo apt-get install -y python3-tk python3-pip python3-dev

# Verify installation
python3 -c "import tkinter; tkinter._test()"
```

#### CentOS/RHEL/Fedora
```bash
# Install tkinter
sudo dnf install python3-tkinter python3-pip python3-devel
# OR for older systems:
# sudo yum install tkinter python3-pip python3-devel
```

#### macOS
```bash
# tkinter comes with Python on macOS
# Install pip if needed
python3 -m ensurepip --upgrade
```

#### Windows
```bash
# tkinter comes with Python on Windows
# No additional installation needed
```

### Python Dependencies

#### Option 1: Modern Styling (Recommended)
```bash
# Install ttkbootstrap for beautiful modern themes
pip3 install ttkbootstrap

# Verify installation
python3 -c "import ttkbootstrap; print('✅ Modern styling available')"
```

#### Option 2: Standard Installation
```bash
# GUI will work with standard tkinter (fallback theme)
# No additional packages needed
```

#### Option 3: Full Features (Future)
```bash
# Install all dependencies for advanced features
pip3 install -r gui/requirements.txt
```

### Launch Instructions

#### Standard Launch
```bash
# From project root directory
cd /home/haymayndz/AI_System_Monorepo
python3 gui/main.py
```

#### With Modern Styling
```bash
# Automatically detects ttkbootstrap
python3 gui/main.py
```

#### Debug Mode
```bash
# Launch with debug output
python3 -u gui/main.py
```

### Troubleshooting

#### Issue: ModuleNotFoundError: No module named 'tkinter'
**Solution**: Install system tkinter package
```bash
sudo apt-get install python3-tk  # Ubuntu/Debian
sudo dnf install python3-tkinter  # Fedora/CentOS
```

#### Issue: Import error with ttkbootstrap
**Solution**: GUI automatically falls back to standard tkinter
```bash
# Optional: Install for better styling
pip3 install ttkbootstrap
```

#### Issue: GUI doesn't start in headless environment
**Solution**: Requires display/X11 forwarding
```bash
# For SSH with X11 forwarding
ssh -X user@server
export DISPLAY=:0
```

#### Issue: Permission errors
**Solution**: Run with proper permissions
```bash
# Check file permissions
ls -la gui/main.py
chmod +x gui/main.py
```

### Environment Variables

#### Optional Configuration
```bash
# Set theme preference
export GUI_THEME=darkly  # darkly, flatly, cosmo, etc.

# Set window size
export GUI_GEOMETRY=1600x1000

# Enable debug mode
export GUI_DEBUG=1
```

### Testing Installation

#### Quick Test
```bash
# Test tkinter availability
python3 -c "
import tkinter as tk
root = tk.Tk()
root.title('Test')
label = tk.Label(root, text='✅ tkinter working!')
label.pack()
print('✅ GUI test successful')
root.after(2000, root.destroy)  # Auto-close after 2 seconds
root.mainloop()
"
```

#### Full GUI Test
```bash
# Launch the complete GUI
python3 gui/main.py
```

Expected result:
- Modern GUI window opens
- Dashboard loads with system status
- Navigation sidebar is functional
- No error messages in console

### Performance Optimization

#### For Better Performance
```bash
# Install Pillow for image optimization
pip3 install Pillow

# Install matplotlib for future charts
pip3 install matplotlib
```

### Security Considerations

#### File Permissions
```bash
# Ensure proper permissions
chmod 755 gui/
chmod 644 gui/*.py
chmod 644 gui/views/*.py
chmod 644 gui/services/*.py
```

#### Network Security
- GUI uses local file system only
- No network connections by default
- CLI integration uses subprocess locally

---

## 🎯 Quick Start Summary

```bash
# 1. Install system dependencies
sudo apt-get install python3-tk python3-pip

# 2. Install modern styling (optional)
pip3 install ttkbootstrap

# 3. Launch GUI
cd /home/haymayndz/AI_System_Monorepo
python3 gui/main.py
```

**Expected Result**: Modern GUI Control Center opens with dashboard showing system status, task queue information, and navigation to all major system components.

---

**Status**: ✅ Installation guide complete - Ready for deployment!
