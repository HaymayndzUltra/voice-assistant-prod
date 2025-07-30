# 🤖 Cursor AI + GUI Integration Guide

## 🚀 Quick Start

### 1. **Launch GUI with Cursor AI Tab**
```bash
cd gui
python3 main.py
# Navigate to "Cursor AI" tab (if integrated)
```

### 2. **Use Barok-to-Prompt Converter**
```bash
# Standalone converter
python3 gui/scripts/barok_to_prompt_converter.py

# Or use in GUI
# Type your request in any format
# Click "Convert to AI Prompt"
```

---

## 💡 How It Works

### **Input → Process → Output Flow**

```mermaid
graph LR
    A[Barok/Filipino Input] --> B[Language Detection]
    B --> C[Intent Analysis]
    C --> D[Component Detection]
    D --> E[Translation]
    E --> F[Enhancement]
    F --> G[Cursor AI Prompt]
    G --> H[Copy/Send to Cursor]
```

---

## 📝 Usage Examples

### **Example 1: Fix an Error (Filipino)**
**Input:**
```
ayusin mo yung error sa login page na hindi gumagana
```

**Output:**
```markdown
## Task: Debug and fix the error in login page that not working

Focus on:
- View implementation and issues

Provide detailed explanation and potential solutions.
```

### **Example 2: Create Feature (Mixed)**
**Input:**
```
gawa ng new feature para sa file upload with validation and error handling
```

**Output:**
```markdown
## Task: Create and implement new feature for when file upload with validation and error handling

Requirements:
- Include comprehensive unit tests
- Implement proper error handling and validation

Follow best practices for code quality, documentation, and maintainability.

## Focus Areas:
- File
- Feature

## Implementation Guidelines:
1. Analyze the current codebase structure
2. Implement the solution following existing patterns
3. Ensure backward compatibility
4. Add appropriate documentation
5. Create comprehensive test cases
```

### **Example 3: Optimization Request**
**Input:**
```
i-optimize mo lahat ng database queries para mas mabilis yung loading
```

**Output:**
```markdown
## Task: Refactor and optimize all of database queries for faster the loading in the database layer

Requirements:
- Handle multiple items/batch operations

Follow best practices for code quality, documentation, and maintainability.

## Focus Areas:
- Database

## Implementation Guidelines:
1. Analyze the current codebase structure
2. Implement the solution following existing patterns
3. Ensure backward compatibility
4. Add appropriate documentation
```

---

## 🎯 Best Practices

### **1. Writing Effective Barok Input**
- ✅ Be specific about what you want
- ✅ Include context (file, function, feature)
- ✅ Mention special requirements (testing, error handling)
- ✅ Use urgency keywords if needed (urgent, asap, agad)

### **2. Component Keywords**
Include these to get better context:
- `gui` - For interface changes
- `database/db` - For data layer
- `api` - For backend services
- `function` - For specific methods
- `class` - For OOP structures
- `file` - For file operations
- `button/form` - For UI elements

### **3. Intent Keywords**
Use these to specify action:
- `gawa/create` - Create new
- `ayusin/fix` - Fix bugs
- `baguhin/modify` - Change existing
- `dagdag/add` - Add to existing
- `tanggal/remove` - Delete
- `test` - Add tests
- `refactor` - Improve code

---

## 🔧 Advanced Features

### **1. Context Attachment**
The GUI tracks:
- Active files in Cursor
- Current task from queue
- Recent edits
- Open tabs

This context is automatically included when sending to Cursor AI.

### **2. Prompt Templates**
Available templates:
- CRUD Operations
- Error Handling
- Performance Optimization
- Test Creation
- Documentation
- Refactoring

### **3. History & Learning**
- All prompts are saved
- Success tracking
- Pattern recognition
- Reusable prompts

---

## 🔌 Integration with Task System

### **Task → Prompt Flow**
```python
# 1. Task from queue
task = {
    "description": "Fix login validation",
    "todos": ["Add email validation", "Add password strength check"]
}

# 2. Convert to prompt
prompt = converter.task_to_prompt(task)

# 3. Send to Cursor
cursor_api.send(prompt, context=get_active_files())
```

### **Auto-Context Building**
```python
context = {
    "active_file": "login_controller.py",
    "related_files": ["login_view.py", "auth_service.py"],
    "recent_changes": get_git_diff(),
    "task_context": current_task,
    "memory_context": search_memory_bank()
}
```

---

## 📊 Metrics & Tracking

### **What's Tracked:**
- Prompt success rate
- Response time
- Token usage
- Code quality improvements
- Time saved
- Error reduction

### **View Analytics:**
- Dashboard → AI Stats card
- Cursor AI tab → Session Stats
- History tab → Success indicators

---

## 🚨 Troubleshooting

### **Common Issues:**

1. **Translation not working properly**
   - Check spelling of Filipino words
   - Use spaces between words
   - Try simpler phrases

2. **Wrong intent detected**
   - Use explicit action words
   - Start with verb (gawa, ayusin, etc.)

3. **Missing context**
   - Include component keywords
   - Specify file/function names
   - Add more details

4. **Prompt too generic**
   - Be more specific
   - Include requirements
   - Mention edge cases

---

## 🎓 Tips for Cursor AI Success

1. **Start Simple**
   - Begin with single-file changes
   - Graduate to multi-file refactors
   - Then system-wide changes

2. **Iterate on Prompts**
   - First prompt: General direction
   - Second prompt: Specific details
   - Third prompt: Edge cases

3. **Use Context Wisely**
   - Don't overload with files
   - Include only relevant code
   - Reference documentation

4. **Learn from History**
   - Review successful prompts
   - Identify patterns
   - Build personal templates

---

## 🔗 Quick Commands

### **Terminal Commands:**
```bash
# Convert single prompt
echo "gawa ng login form" | python3 gui/scripts/barok_to_prompt_converter.py

# Open GUI
python3 gui/main.py

# Check prompt history
cat gui/data/prompt_history.json | jq
```

### **GUI Shortcuts:**
- `Ctrl+Enter` - Convert prompt
- `Ctrl+C` - Copy converted prompt
- `Ctrl+H` - Show history
- `Ctrl+T` - Load template

---

## 📚 Resources

- **Converter Script:** `gui/scripts/barok_to_prompt_converter.py`
- **GUI View:** `gui/views/cursor_ai_integration.py`
- **Templates:** `gui/data/prompt_templates.json`
- **History:** `gui/data/prompt_history.json`

---

**Happy Coding with Cursor AI! 🚀**