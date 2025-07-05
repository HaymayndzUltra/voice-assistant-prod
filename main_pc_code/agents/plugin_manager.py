from main_pc_code.src.core.base_agent import BaseAgent
import os
import sys
import importlib
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

PLUGINS_DIR = os.path.join(os.path.dirname(__file__), '..', 'plugins')
LOADED_PLUGINS = {}

class PluginEventHandler(BaseAgent, FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return
        plugin_name = os.path.basename(event.src_path)[:-3]
        reload_plugin(plugin_name)
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return
        plugin_name = os.path.basename(event.src_path)[:-3]
        load_plugin(plugin_name)
    def on_deleted(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return
        plugin_name = os.path.basename(event.src_path)[:-3]
        unload_plugin(plugin_name)

def load_plugin(plugin_name):
    if plugin_name in LOADED_PLUGINS:
        print(f"[PluginManager] Plugin '{plugin_name}' already loaded.")
        return
    try:
        module = importlib.import_module(plugin_name)
        LOADED_PLUGINS[plugin_name] = module
        print(f"[PluginManager] Loaded plugin: {plugin_name}")
    except Exception as e:
        print(f"[PluginManager] Failed to load plugin '{plugin_name}': {e}")
    finally:
        if PLUGINS_DIR in sys.path:
            sys.path.remove(PLUGINS_DIR)

def unload_plugin(plugin_name):
    if plugin_name not in LOADED_PLUGINS:
        print(f"[PluginManager] Plugin '{plugin_name}' not loaded.")
        return
    try:
        del sys.modules[plugin_name]
        del LOADED_PLUGINS[plugin_name]
        print(f"[PluginManager] Unloaded plugin: {plugin_name}")
    except Exception as e:
        print(f"[PluginManager] Failed to unload plugin '{plugin_name}': {e}")

def reload_plugin(plugin_name):
    unload_plugin(plugin_name)
    load_plugin(plugin_name)

def list_plugins():
    return list(LOADED_PLUGINS.keys())

def watch_plugins():
    event_handler = PluginEventHandler()
    observer = Observer()
    observer.schedule(event_handler, PLUGINS_DIR, recursive=False)
    observer.start()
    print(f"[PluginManager] Watching plugins directory: {PLUGINS_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def main():
    # Initial load
    for fname in os.listdir(PLUGINS_DIR):
        if fname.endswith('.py'):
            load_plugin(fname[:-3])
    # Start watching
    watch_plugins()

if __name__ == "__main__":
    main()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
