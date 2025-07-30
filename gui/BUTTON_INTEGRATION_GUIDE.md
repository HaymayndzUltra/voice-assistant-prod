# 🎮 GUI Button Integration Guide

## 📋 Complete Button Mapping & Integration Requirements

---

## 🏠 DASHBOARD VIEW - Quick Actions

### 🆕 New Task Button
**File:** `dashboard.py` → `_create_new_task()`
```python
# Current: Placeholder dialog
# Needs: Integration with todo_manager.py

def _create_new_task(self):
    # INTEGRATE WITH:
    import subprocess
    task_desc = simpledialog.askstring("New Task", "Enter task description:")
    if task_desc:
        result = subprocess.run(
            ["python3", "../todo_manager.py", "add", task_desc],
            capture_output=True, text=True
        )
        # Handle result and refresh display
```

### ▶️ Start Queue Button  
**File:** `dashboard.py` → `_start_queue()`
```python
# Current: Placeholder
# Needs: queue_cli.py integration

def _start_queue(self):
    # INTEGRATE WITH:
    result = subprocess.run(
        ["python3", "../queue_cli.py", "start", "--daemon"],
        capture_output=True, text=True
    )
    # Update status indicators
```

### ⏸️ Pause Queue Button
**File:** `dashboard.py` → `_pause_queue()`
```python
# Current: Placeholder
# Needs: queue_cli.py integration

def _pause_queue(self):
    # INTEGRATE WITH:
    result = subprocess.run(
        ["python3", "../queue_cli.py", "pause"],
        capture_output=True, text=True
    )
    # Update UI status
```

### 📊 System Health Button
**File:** `dashboard.py` → `_check_system_health()`
```python
# Current: Placeholder
# Needs: Health check system

def _check_system_health(self):
    # INTEGRATE WITH:
    # 1. Check queue engine status
    # 2. Check agent health
    # 3. Check memory system
    # 4. Check file system
    # Display comprehensive health report
```

---

## 📋 TASK MANAGEMENT VIEW - Control Panel

### ➕ New Task Button
**File:** `task_management.py` → `_create_new_task()`
```python
# Current: Basic dialog
# Needs: Full todo_manager.py integration

def _create_new_task(self):
    # INTEGRATE WITH:
    # 1. Advanced task creation dialog
    # 2. todo_manager.py add_task()
    # 3. Real-time UI refresh
    # 4. Validation and error handling
```

### ✏️ Edit Task Button
**File:** `task_management.py` → `_edit_selected_task()`
```python
# Current: Placeholder
# Needs: Task editing interface

def _edit_selected_task(self):
    # INTEGRATE WITH:
    # 1. Get selected task from treeview
    # 2. Load task data
    # 3. Show edit dialog
    # 4. todo_manager.py edit functions
    # 5. Update display
```

### 🗑️ Delete Task Button
**File:** `task_management.py` → `_delete_selected_task()`
```python
# Current: Placeholder
# Needs: Task deletion with confirmation

def _delete_selected_task(self):
    # INTEGRATE WITH:
    # 1. Get selected task
    # 2. Confirmation dialog
    # 3. todo_manager.py delete_task()
    # 4. Refresh task list
```

### ▶️ Start Selected Button
**File:** `task_management.py` → `_start_selected_task()`
```python
# Current: Placeholder
# Needs: Task execution integration

def _start_selected_task(self):
    # INTEGRATE WITH:
    # 1. Get selected task
    # 2. Move to tasks_active.json
    # 3. Trigger queue engine
    # 4. Update UI status
```

### ⏸️ Pause Selected Button
**File:** `task_management.py` → `_pause_selected_task()`
```python
# Current: Placeholder
# Needs: Task interruption system

def _pause_selected_task(self):
    # INTEGRATE WITH:
    # 1. Get active task
    # 2. Move to tasks_interrupted.json
    # 3. Stop execution
    # 4. Update status
```

### 🔄 Refresh Button
**File:** `task_management.py` → `_refresh_task_data()`
```python
# Current: Placeholder
# Needs: Real data loading

def _refresh_task_data(self):
    # INTEGRATE WITH:
    # 1. Load tasks_active.json
    # 2. Load tasks_queue.json
    # 3. Load tasks_done.json
    # 4. Update all treeviews
    # 5. Update progress indicators
```

### 📤 Export Button
**File:** `task_management.py` → `_export_tasks()`
```python
# Current: Placeholder
# Needs: Export functionality

def _export_tasks(self):
    # INTEGRATE WITH:
    # 1. File dialog for save location
    # 2. Choose export format (JSON/CSV)
    # 3. Generate export data
    # 4. Save to file
```

### 🧹 Cleanup Button
**File:** `task_management.py` → `_cleanup_completed()`
```python
# Current: Placeholder
# Needs: Cleanup operations

def _cleanup_completed(self):
    # INTEGRATE WITH:
    # 1. todo_manager.py cleanup functions
    # 2. Archive old completed tasks
    # 3. Refresh display
```

---

## 🤖 AGENT CONTROL VIEW - Agent Operations

### ▶️ Start Agent Button
**File:** `agent_control.py` → `_start_selected_agent()`
```python
# Current: Placeholder
# Needs: Agent start scripts

def _start_selected_agent(self):
    # INTEGRATE WITH:
    # 1. Get selected agent
    # 2. Load agent start command
    # 3. Execute start script
    # 4. Monitor startup
    # 5. Update status display
```

### ⏹️ Stop Agent Button
**File:** `agent_control.py` → `_stop_selected_agent()`
```python
# Current: Placeholder
# Needs: Agent stop scripts

def _stop_selected_agent(self):
    # INTEGRATE WITH:
    # 1. Get selected agent
    # 2. Send stop signal
    # 3. Wait for graceful shutdown
    # 4. Force kill if needed
    # 5. Update status
```

### 🔄 Restart Agent Button
**File:** `agent_control.py` → `_restart_selected_agent()`
```python
# Current: Placeholder
# Needs: Agent restart sequence

def _restart_selected_agent(self):
    # INTEGRATE WITH:
    # 1. Stop agent
    # 2. Wait for clean shutdown
    # 3. Start agent
    # 4. Monitor startup
    # 5. Update display
```

### ❤️ Health Check Button
**File:** `agent_control.py` → `_check_agent_health()`
```python
# Current: Placeholder
# Needs: Agent health monitoring

def _check_agent_health(self):
    # INTEGRATE WITH:
    # 1. Ping agent endpoints
    # 2. Check process status
    # 3. Verify functionality
    # 4. Update health indicators
```

### 🔧 Configure Button
**File:** `agent_control.py` → `_configure_agent()`
```python
# Current: Placeholder
# Needs: Agent configuration interface

def _configure_agent(self):
    # INTEGRATE WITH:
    # 1. Load agent config
    # 2. Show config dialog
    # 3. Validate settings
    # 4. Save configuration
    # 5. Restart if needed
```

### 📊 Logs Button
**File:** `agent_control.py` → `_view_agent_logs()`
```python
# Current: Placeholder
# Needs: Log viewing interface

def _view_agent_logs(self):
    # INTEGRATE WITH:
    # 1. Find agent log files
    # 2. Open log viewer window
    # 3. Real-time log monitoring
    # 4. Search and filtering
```

### 🧹 Cleanup Conflicts Button
**File:** `agent_control.py` → `_cleanup_port_conflicts()`
```python
# Current: Placeholder
# Needs: Port conflict resolution

def _cleanup_port_conflicts(self):
    # INTEGRATE WITH:
    # 1. Scan for port conflicts
    # 2. Identify conflicting processes
    # 3. Resolve conflicts
    # 4. Update agent configurations
```

### 🔍 Rescan Agents Button
**File:** `agent_control.py` → `_rescan_agents()`
```python
# Current: Placeholder
# Needs: Agent discovery refresh

def _rescan_agents(self):
    # INTEGRATE WITH:
    # 1. Run agent discovery scan
    # 2. Update agent_scan_results.json
    # 3. Refresh agent list
    # 4. Update counts and status
```

---

## 🧠 MEMORY INTELLIGENCE VIEW - Memory Operations

### 🔍 Search Brain Button
**File:** `memory_intelligence.py` → `_search_brain()`
```python
# Current: Placeholder
# Needs: Memory search functionality

def _search_brain(self):
    # INTEGRATE WITH:
    # 1. memory_system/cli.py search
    # 2. Search across memory-bank/
    # 3. Display search results
    # 4. Relevance ranking
```

### 🔄 Refresh Graph Button
**File:** `memory_intelligence.py` → `_refresh_graph()`
```python
# Current: Sample data
# Needs: Real MCP graph data

def _refresh_graph(self):
    # INTEGRATE WITH:
    # 1. MCP memory server API
    # 2. Load knowledge graph data
    # 3. Update entity relationships
    # 4. Refresh visualization
```

### 🔍 Explore Graph Button
**File:** `memory_intelligence.py` → `_explore_graph()`
```python
# Current: Placeholder
# Needs: Interactive graph exploration

def _explore_graph(self):
    # INTEGRATE WITH:
    # 1. NetworkX graph library
    # 2. Interactive visualization
    # 3. Node selection and details
    # 4. Relationship exploration
```

### 📎 Edit Content Button
**File:** `memory_intelligence.py` → `_edit_content()`
```python
# Current: Placeholder
# Needs: Memory editing interface

def _edit_content(self):
    # INTEGRATE WITH:
    # 1. Load selected memory
    # 2. Open editor interface
    # 3. Save changes to memory
    # 4. Update display
```

### 📄 Export Content Button
**File:** `memory_intelligence.py` → `_export_content()`
```python
# Current: Placeholder
# Needs: Memory export functionality

def _export_content(self):
    # INTEGRATE WITH:
    # 1. File save dialog
    # 2. Format selection
    # 3. Export memory data
    # 4. Save to file
```

### 📝 Create Memory Button
**File:** `memory_intelligence.py` → `_create_memory()`
```python
# Current: Placeholder
# Needs: Memory creation interface

def _create_memory(self):
    # INTEGRATE WITH:
    # 1. Memory creation dialog
    # 2. MCP memory API
    # 3. Save new memory
    # 4. Refresh display
```

### 🔄 Sync All Button
**File:** `memory_intelligence.py` → `_sync_all_memory()`
```python
# Current: Placeholder
# Needs: Memory synchronization

def _sync_all_memory(self):
    # INTEGRATE WITH:
    # 1. MCP sync operations
    # 2. Memory-bank sync
    # 3. Progress indication
    # 4. Status updates
```

---

## 📊 MONITORING VIEW - System Controls

### 🔄 Refresh Metrics Button
**File:** `monitoring.py` → `_refresh_metrics()`
```python
# Current: Placeholder
# Needs: Real-time metrics

def _refresh_metrics(self):
    # INTEGRATE WITH:
    # 1. psutil system metrics
    # 2. Update CPU/Memory/Disk
    # 3. Refresh charts
    # 4. Update displays
```

### 📊 Export Data Button
**File:** `monitoring.py` → `_export_monitoring_data()`
```python
# Current: Placeholder
# Needs: Data export functionality

def _export_monitoring_data(self):
    # INTEGRATE WITH:
    # 1. Collect metrics history
    # 2. Format data (CSV/JSON)
    # 3. Save to file
    # 4. Include charts if needed
```

### ⚙️ Settings Button
**File:** `monitoring.py` → `_monitoring_settings()`
```python
# Current: Placeholder
# Needs: Settings configuration

def _monitoring_settings(self):
    # INTEGRATE WITH:
    # 1. Show settings dialog
    # 2. Refresh intervals
    # 3. Chart preferences
    # 4. Alert thresholds
```

### 🚨 Alerts Button
**File:** `monitoring.py` → `_configure_alerts()`
```python
# Current: Placeholder
# Needs: Alert system

def _configure_alerts(self):
    # INTEGRATE WITH:
    # 1. Alert configuration dialog
    # 2. Threshold settings
    # 3. Notification preferences
    # 4. Alert history
```

---

## 🔄 AUTOMATION CONTROL VIEW - System Controls

### ▶️ Start Queue Engine Button
**File:** `automation_control.py` → `_start_queue_engine()`
```python
# Current: Basic command
# Needs: Full integration

def _start_queue_engine(self):
    # CURRENT IMPLEMENTATION:
    result = self.system_service.execute_cli_command("queue start --daemon")
    if result.get("success"):
        self._log_automation("✅ Queue engine started successfully")
        self.status_cards["queue_engine"].status_label.configure(text="Running")
    # NEEDS: Better error handling, status monitoring
```

### ⏹️ Stop Queue Engine Button
**File:** `automation_control.py` → `_stop_queue_engine()`
```python
# Current: Basic command
# Needs: Graceful shutdown

def _stop_queue_engine(self):
    # INTEGRATE WITH:
    # 1. Graceful shutdown sequence
    # 2. Wait for current tasks
    # 3. Force stop if needed
    # 4. Update status indicators
```

### 📊 Status Check Button
**File:** `automation_control.py` → `_check_queue_status()`
```python
# Current: Basic command
# Needs: Detailed status parsing

def _check_queue_status(self):
    # INTEGRATE WITH:
    # 1. Parse queue status output
    # 2. Display formatted status
    # 3. Show running tasks
    # 4. Performance metrics
```

### ▶️ Enable Auto-Sync Button
**File:** `automation_control.py` → `_enable_auto_sync()`
```python
# Current: Placeholder
# Needs: Auto-sync integration

def _enable_auto_sync(self):
    # INTEGRATE WITH:
    # 1. auto_sync_manager.py
    # 2. Start sync service
    # 3. Configure intervals
    # 4. Monitor sync status
```

### 🔄 Force Sync Button
**File:** `automation_control.py` → `_force_sync()`
```python
# Current: Placeholder
# Needs: Manual sync trigger

def _force_sync(self):
    # INTEGRATE WITH:
    # 1. Trigger immediate sync
    # 2. Show progress indicator
    # 3. Display sync results
    # 4. Update timestamps
```

### ⚠️ Emergency Stop Button
**File:** `automation_control.py` → `_emergency_stop()`
```python
# Current: Basic implementation
# Needs: Complete shutdown sequence

def _emergency_stop(self):
    # INTEGRATE WITH:
    # 1. Stop all queue engines
    # 2. Stop all agents
    # 3. Disable auto-sync
    # 4. Save current state
    # 5. Show emergency status
```

### 💾 Save Settings Button
**File:** `automation_control.py` → `_save_settings()`
```python
# Current: Placeholder
# Needs: Settings persistence

def _save_settings(self):
    # INTEGRATE WITH:
    # 1. Collect all settings
    # 2. Validate values
    # 3. Save to config file
    # 4. Apply changes
    # 5. Show confirmation
```

---

## 🔧 SYSTEM SERVICE METHODS - Backend Integration

### Execute CLI Command
**File:** `system_service.py` → `execute_cli_command()`
```python
# Current: Placeholder
# Needs: Full CLI integration

def execute_cli_command(self, command):
    # INTEGRATE WITH:
    # 1. Subprocess execution
    # 2. Error handling
    # 3. Timeout management
    # 4. Output parsing
    # 5. Result formatting
```

### Get System Health
**File:** `system_service.py` → `get_system_health()`
```python
# Current: Placeholder
# Needs: Health check system

def get_system_health(self):
    # INTEGRATE WITH:
    # 1. Check all system components
    # 2. Aggregate health status
    # 3. Return structured data
    # 4. Cache results
```

### Load Task Data
**File:** `system_service.py` → `load_task_data()`
```python
# Current: Placeholder
# Needs: Task file integration

def load_task_data(self):
    # INTEGRATE WITH:
    # 1. Load all task JSON files
    # 2. Parse and validate data
    # 3. Handle file errors
    # 4. Return formatted data
```

### Monitor File Changes
**File:** `system_service.py` → `monitor_file_changes()`
```python
# Current: None
# Needs: File watching system

def monitor_file_changes(self):
    # INTEGRATE WITH:
    # 1. Watchdog file monitoring
    # 2. Real-time change detection
    # 3. Trigger UI updates
    # 4. Handle multiple files
```

---

## 🎯 INTEGRATION PRIORITY MATRIX

### 🔥 CRITICAL (Implement First)
1. **Task queue file loading** - Basic task display
2. **Queue engine controls** - Start/stop functionality  
3. **Real-time data refresh** - Auto-updating displays
4. **Basic agent status** - Show agent health

### ⚡ HIGH (Implement Second)
1. **Task CRUD operations** - Full task management
2. **Agent control operations** - Start/stop agents
3. **System monitoring** - CPU/memory metrics
4. **Settings persistence** - Save configurations

### 📊 MEDIUM (Implement Third)
1. **Memory system integration** - MCP connection
2. **Advanced monitoring** - Charts and graphs
3. **Export functionality** - Data export features
4. **Alert system** - Monitoring alerts

### 🌟 LOW (Implement Last)
1. **Advanced visualizations** - Complex charts
2. **Graph visualization** - NetworkX integration
3. **Advanced automation** - Smart rules
4. **Performance optimization** - Speed improvements

---

**NEXT STEPS:**
1. Choose one view to start with (recommend Task Management)
2. Implement critical buttons first
3. Test each button thoroughly
4. Move to next priority level
5. Document progress and issues
