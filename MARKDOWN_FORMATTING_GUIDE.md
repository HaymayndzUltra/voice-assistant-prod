# 📝 Markdown Formatting Guide para sa AI System Monorepo

## 🔧 Paano Mag-format ng Markdown Files

### 1. **Quick Setup** (One-time lang)
```bash
# Install mo muna ang tools
bash scripts/setup_formatting.sh
```

### 2. **Basic Formatting Commands**

#### Format lahat ng Markdown files:
```bash
python scripts/format_markdown.py
```

#### Format specific files lang:
```bash
python scripts/format_markdown.py --files README.md report.md
```

### 3. **Custom Formatting Options**

#### **Line Width** (Haba ng linya)
```bash
# 100 characters max per line
python scripts/format_markdown.py --line-width 100

# 80 characters max per line (mas maikli)
python scripts/format_markdown.py --line-width 80

# 150 characters max per line (mas mahaba)
python scripts/format_markdown.py --line-width 150
```

#### **Text Wrapping Style**
```bash
# PRESERVE - hindi gagalawin ang linya breaks (recommended)
python scripts/format_markdown.py --wrap preserve

# ALWAYS - automatic wrap kapag sobrang haba
python scripts/format_markdown.py --wrap always

# NEVER - hindi mag-wrap kahit mahaba
python scripts/format_markdown.py --wrap never
```

#### **Indentation** (Pag-indent)
```bash
# 2 spaces (default)
python scripts/format_markdown.py --indent 2

# 4 spaces
python scripts/format_markdown.py --indent 4

# Use tabs instead of spaces
python scripts/format_markdown.py --tabs
```

### 4. **Combination Examples**

#### Para sa Filipino documentation:
```bash
# Magandang setting para sa Taglish content
python scripts/format_markdown.py --line-width 120 --wrap preserve --indent 2
```

#### Para sa technical documentation:
```bash
# Strict formatting
python scripts/format_markdown.py --line-width 100 --wrap always --indent 2
```

#### Para sa specific files with custom settings:
```bash
python scripts/format_markdown.py --files AGENTLIST.md README.md --line-width 100 --wrap always
```

### 5. **Automatic Formatting** (Mas convenient)

#### Setup pre-commit hooks:
```bash
pre-commit install
```
After nito, automatic na mag-format ang markdown files kapag nag-commit ka.

#### Manual pre-commit run:
```bash
pre-commit run --all-files
```

### 6. **Alternative: Direct Prettier Commands**

Kung may Node.js/npm ka:

```bash
# Install prettier globally
npm install -g prettier

# Format all markdown files
prettier --write "**/*.md"

# Format with custom settings
prettier --write "**/*.md" --print-width 100 --prose-wrap always

# Format specific files
prettier --write README.md AGENTLIST.md --print-width 120
```

### 7. **Current Default Settings**

Ang current config sa `.prettierrc.json`:
- **Line width**: 120 characters
- **Prose wrap**: preserve (hindi babaguhin ang existing line breaks)
- **Indentation**: 2 spaces
- **End of line**: LF (Unix style)

### 8. **Troubleshooting**

#### Kung walang prettier:
```bash
# Install Node.js from https://nodejs.org/
# Then install prettier
npm install -g prettier
```

#### Kung may error sa script:
```bash
# Check muna kung nag-install ng requirements
pip install -r requirements-dev.txt

# Test kung may prettier
prettier --version
```

#### Help command:
```bash
python scripts/format_markdown.py --help
```

### 9. **Recommended Workflow**

1. **Setup** (once lang):
   ```bash
   bash scripts/setup_formatting.sh
   ```

2. **Daily use**:
   ```bash
   # Format all markdown files
   python scripts/format_markdown.py

   # Or format specific files
   python scripts/format_markdown.py --files myfile.md
   ```

3. **Before commit** (automatic na if may pre-commit):
   ```bash
   pre-commit run --all-files
   ```

---

## 🎯 **Quick Reference Commands**

 | Purpose | Command | 
 | --------- | --------- | 
 | Format all MD files | `python scripts/format_markdown.py` | 
 | Format specific files | `python scripts/format_markdown.py --files file1.md file2.md` | 
 | Short lines (80 chars) | `python scripts/format_markdown.py --line-width 80` | 
 | Long lines (150 chars) | `python scripts/format_markdown.py --line-width 150` | 
 | Always wrap long text | `python scripts/format_markdown.py --wrap always` | 
 | Never wrap text | `python scripts/format_markdown.py --wrap never` | 
 | Use 4 spaces indent | `python scripts/format_markdown.py --indent 4` | 
 | Use tabs | `python scripts/format_markdown.py --tabs` | 
 | Show help | `python scripts/format_markdown.py --help` | 

---

**Tip**: Subukan mo muna sa sample file bago i-apply sa lahat! 😊