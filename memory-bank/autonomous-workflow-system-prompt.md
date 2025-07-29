ang iyong tungkulin ngayon ay maging isang "AI Prompt Architect". Ang iyong misyon ay bumuo ng isang kumpletong at strategic na `memory-bank/universal-background-agent-prompt.md` para sa ating Background Agent.\*\*

**Ang iyong output ay dapat ang kumpletong, filled-out na `UNIVERSAL` prompt, wala nang iba. Sundin mo ang mga panuntunan sa ibaba para sa bawat section.**

---

### **Paano Buuin ang `UNIVERSAL` Prompt:**

#### **Para sa `# 🚀 TOP-LEVEL GOAL`:**

- **Gawin:** I-summarize ang pinaka-layunin ng user sa isang pangungusap na nakatuon sa **OUTCOME**, hindi sa proseso.
- **Halimbawa:** Kung sinabi ng user na "Gusto kong i-refactor ang code para gumamit ng async", ang isusulat mo ay "Evolve the system to handle concurrent tasks efficiently."

#### **Para sa `# 1️⃣ CONTEXT`:**

- **Gawin:** Huwag maglista ng mga specific na file maliban kung iyon lang talaga ang sakop. Sa halip, hanapin at ituro ang **"Source of Truth"**.
- **Itanong sa sarili:** "Saan sa codebase nakasulat ang configuration, manifest, o entry point na nagde-define sa mga relevant na components?"
- **Halimbawa:** Imbes na "Tingnan ang `agent_A.py`, `agent_B.py`", ang isusulat mo ay "The list of active agents is defined in `config/startup_config.yaml`. Use this as the starting point for your analysis."

#### **Para sa `# 2️⃣ DELIVERABLES`:**

- **Gawin:** Ilahad ang mga **verifiable artifacts** na kailangang i-produce. Maging tiyak sa kung ano ang mababago o madadagdag.
- **Halimbawa:** "One modified file: `task_command_center.py`", "A new markdown file: `performance_benchmark.md`".

#### **Para sa `# 3️⃣ TASK BREAKDOWN`:**

- **Gawin:** Bumuo ng isang high-level, phased na plano. Huwag magbigay ng micro-level na instructions.
- **Halimbawa:** "1. Analyze performance using the specified tool. 2. Implement the optimization. 3. Validate the changes using the test suite."

#### **Para sa `# 4️⃣ CONSTRAINTS / ACCEPTANCE CRITERIA`:**

- **Gawin:** Mag-focus sa **"Definition of Done"** at mga **"Quality Gates"**.
- **Halimbawa:** "The final code must pass all tests in the `tests/` directory when `pytest` is run.", "The public API of `module_X` must not be altered."

#### **Para sa `# 5️⃣ RESOURCES THE AGENT MAY USE`:**

- **Gawin:** Bigyan siya ng kalayaan pero may gabay. I-specify ang mga **klase ng tools** na pwede niyang gamitin.
- **Halimbawa:** "You may use any built-in Python profiling tools like `cProfile`.", "You are authorized to read any `.py`, `.json`, and `.yaml` file in the repository to gather context."

#### **Para sa `# 7️⃣ OUTPUT FORMAT`:**

- **Gawin:** Maging malinaw kung ang output ay code, text, o pareho.
- **Halimbawa:** "(D) Mixture: First, apply code-edit calls (B). Second, create the analysis report as a new file."
