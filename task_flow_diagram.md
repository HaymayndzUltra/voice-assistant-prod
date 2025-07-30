# Task Management System Flow

```mermaid
flowchart TD
    Start([System Idle/Ready])
    Q[tasks_queue.json<br/>(Task Queue)]
    A[tasks_active.json<br/>(Active Task)]
    I[tasks_interrupted.json<br/>(Interrupted Tasks)]
    D[tasks_done.json<br/>(Completed Tasks)]

    Start --> CheckActive{Is<br/>Active Task empty?}
    CheckActive -- "Yes" --> CheckInterrupted{Is<br/>Interrupted empty?}
    CheckActive -- "No" --> ProcessA[Work on Active Task]

    CheckInterrupted -- "Yes" --> CheckQueue{Is<br/>Queue empty?}
    CheckInterrupted -- "No" --> I2A[Move Interrupted → Active]
    I2A --> ProcessA

    CheckQueue -- "Yes" --> DoneAll([All tasks finished])
    CheckQueue -- "No" --> Q2A[Move Queue → Active]
    Q2A --> ProcessA

    ProcessA -- "Interrupt" --> A2I[Move Active → Interrupted]
    A2I --> NewTask[Put New Task → Active]
    NewTask --> ProcessA

    ProcessA -- "Finish" --> A2D[Move Active → Done]
    A2D --> CheckActive
```

## How to View This Flowchart:

### Option 1: GitHub (Recommended)
- If you push this to GitHub, the flowchart will render automatically
- GitHub natively supports Mermaid diagrams

### Option 2: Mermaid Live Editor
- Go to: https://mermaid.live/
- Copy and paste the flowchart code (everything between ```mermaid and ```)
- See it rendered instantly

### Option 3: VS Code
- Install "Mermaid Preview" extension
- Open this file and use Ctrl+Shift+P → "Mermaid Preview: Open Preview"

### Option 4: Online Mermaid Viewer
- Go to: https://mermaid.js.org/demo/
- Paste the flowchart code
- Click "Render" 