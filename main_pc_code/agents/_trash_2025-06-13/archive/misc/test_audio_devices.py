from src.core.base_agent import BaseAgent
import sounddevice as sd
import sys

print("--- Starting Audio Device Test ---")
sys.stdout.flush()

try:
    print("Attempting to query devices using sd.query_devices()...")
    sys.stdout.flush()
    devices = sd.query_devices()
    print("Successfully queried devices.")
    sys.stdout.flush()

    print("\nAvailable audio input devices:")
    sys.stdout.flush()
    found_input_device = False
    for idx, device in enumerate(devices):
        # Make sure device name is a string and encodable
        device_name_str = str(device.get('name', 'Unknown Device'))
        try:
            print(f"  Device Index: {idx}")
            print(f"    Name: {device_name_str}")
            print(f"    Host API: {device.get('hostapi', -1)} ({sd.query_hostapis(device.get('hostapi'))['name'] if device.get('hostapi', -1) != -1 else 'N/A'})")
            print(f"    Max Input Channels: {device.get('max_input_channels', 0)}")
            print(f"    Default Sample Rate: {device.get('default_samplerate', 0)}")
            print("---")
            sys.stdout.flush()
            if device.get('max_input_channels', 0) > 0:
                found_input_device = True
        except Exception as e_print:
            print(f"    Error printing details for device {idx}: {e_print}")
            sys.stdout.flush()

    if not found_input_device:
        print("No input devices found.")
    else:
        print("Finished listing input devices.")
    sys.stdout.flush()

except Exception as e:
    print(f"\nAn error occurred: {e}")
    sys.stdout.flush()

print("--- Audio Device Test Finished ---")
sys.stdout.flush()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
