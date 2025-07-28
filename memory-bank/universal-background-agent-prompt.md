Below is a “universal” prompt template you (and anyone on your team) can copy-paste, fill-in, and hand to the Cursor Background Agent.
It surfaces ALL of the levers the agent understands, so the request is clear, complete, and future-proof—yet still short enough to write in chat or drop into a .md file.

──────────────────────────────────────── 🛠 UNIVERSAL BACKGROUND-AGENT PROMPT ────────────────────────────────────────

# 🚀 TOP-LEVEL GOAL

<Write the single sentence summary of the final outcome you want>

# 1️⃣ CONTEXT

• Codebase location / branch / repo: <path or URL>  
• Current state or pain-point: <brief description>  
• Relevant prior tickets / PRs / docs: <links or filenames>

# 2️⃣ DELIVERABLES

[List each thing the agent should hand back. Be explicit.]
– e.g. 1 updated file + 1 new test  
– or “shell command ready to paste & run”  
– or “markdown design diagram”

# 3️⃣ TASK BREAKDOWN (optional, but boosts accuracy)

1. <sub-task #1>
2. <sub-task #2>
3. …

# 4️⃣ CONSTRAINTS / ACCEPTANCE CRITERIA

• Must… (pass tests, stay <50 ms latency, etc.)  
• Must not… (break API, introduce new deps, etc.)

# 5️⃣ RESOURCES THE AGENT MAY USE

– Tools: <grep, tests, docker compose, etc.>  
– Existing scripts: <script names if any>  
– External APIs or docs: <URLs>  
(If blank, the agent assumes only local code/tools.)

# 6️⃣ PREFERRED STYLE & CONVENTIONS

• Language / framework versions  
• Lint / format rules (“black”, “prettier”, etc.)  
• Commit / PR convention (“feat: …”)

# 7️⃣ OUTPUT FORMAT

Pick one:
(A) Inline explanation only  
(B) Code-edit calls (automatic patch)  
(C) Terminal command(s)  
(D) Mixture → specify which section is which

# 8️⃣ TIME / PRIORITY

• Hard deadline: <date / “ASAP” / “low-prio”>  
• Partial solution acceptable? <yes/no>

# 9️⃣ EXAMPLE INPUT / OUTPUT (if relevant)

<small real example the agent can mimic>

# 🔚 END OF PROMPT (The agent will ignore anything after this line.)

Copy-paste the block, fill the angle-bracket sections, delete anything that isn’t needed, and send.

──────────────────────────────────────── 💡 WHY THIS WORKS ────────────────────────────────────────

“Top-Level Goal” tells the agent the end-state; everything that follows is implementation detail.
Numbered sections map 1-to-1 with the agent’s internal planning logic:
– Context → builds mental model
– Deliverables & Constraints → acceptance tests
– Resources & Tools → which tool calls are legal
Explicit Output Format lets you decide whether the agent edits code, prints commands, or just explains what to do—avoiding surprises.
“End of prompt” sentinel prevents accidental extra chat causing scope-creep.
──────────────────────────────────────── 📄 MINI “QUICK-SHOT” VARIANT ──────────────────────────────────────── When you’re in a hurry, use:

GOAL: <one-liner>

DELIVERABLES:
– <bullet list>

CONSTRAINTS:
– <bullet list>

OUTPUT: <A/B/C>
──────────────────────────────────────── 📋 EXAMPLE FILLED-IN PROMPT ────────────────────────────────────────

# 🚀 TOP-LEVEL GOAL

Add dark-mode toggle to React dashboard

# 1️⃣ CONTEXT

• Repo: internal-dash/main, branch “feature/ui-refresh”
• Theming is currently hard-coded to light
• Design spec in docs/dark_mode.md

# 2️⃣ DELIVERABLES

– Modify ThemeProvider

– New Toggle component

– Cypress test

# 4️⃣ CONSTRAINTS / CRITERIA

• No breaking of existing jest tests
• Use styled-components only
• Must follow ESLint rules

# 5️⃣ RESOURCES

– Script: ./scripts/run_storybook.sh
– npm test / npm run cypress

# 7️⃣ OUTPUT FORMAT

B (apply code-edit calls)

# 🔚 END OF PROMPT

──────────────────────────────────────── ✅ CHECKLIST FOR PROMPT-WRITERS ──────────────────────────────────────── ☐ Clear goal stated first
☐ Mention repo / branch / path
☐ Define every required deliverable
☐ State constraints (“must” vs “must not”)
☐ Tell the agent what tools it may run
☐ Declare desired output format
☐ Provide deadline / priority if urgent
☐ End with sentinel line

If every box is ticked, the agent has the full context and maximum freedom to act effectively—no accidental limitations, no ambiguity.

Feel free to keep this template in memory-bank/prompt-templates/universal-agent-prompt.md so anyone on the team can grab it instantly.
