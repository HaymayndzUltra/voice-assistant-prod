# Full Capabilities ng Background Agent (o3-pro, Max Mode) sa Buong Codebase

## 1. Ano ang kaya gawin sa codebase?

### A. Deep Context/Codebase Awareness

* Kayang magbasa ng buong repo (up to 1M tokens context; o3-pro supports Max Mode context window, mas malawak pa kaysa GPT-4/Gemini).
* **Global code search:** Automatic na nadi-detect ang dependencies, usage, at relationships ng files/functions kahit hindi mo manually i-point out.
* **Code graph analysis:** Nakikita ang interconnected logic, business rules, config flows, at environment setup.

### B. Multi-file & Project-wide Edits

* **Bulk refactor:** Rename, extract, move, or split code across hundreds of files in one command.
* **Add features/fix bugs:** Kayang mag-implement ng bagong feature, mag-lipat ng logic, o mag-fix ng bugs affecting several modules at once.
* **Docstring/comment sync:** Pwede kang mag-utos na i-update lahat ng docstrings sa project para maging consistent, or lagyan ng headers ang lahat ng file.

### C. Automated, Autonomous Debugging

* **Full test suite run:** Kayang patakbuhin at i-debug ang lahat ng tests; uulitin ang cycles (edit-run-test) hanggang wala nang error.
* **Log analysis:** Kayang basahin ang test outputs/logs para tukuyin ang root cause (halimbawa: race conditions, edge cases, integration errors).
* **Stack trace hopping:** Madi-detect at maaayos ang bugs na tumatawid ng maraming files o modules (unlike inline mode na limited sa isang file).

### D. Complex Automation (CI/CD, PR, etc)

* **Auto-PR creation:** Mag-commit sa branch, ayusin ang PR details (title, body, checklist), i-resolve ang merge conflict, at mag-push ng code sa GitHub.
* **Lint/fix all:** Pwede i-utos na i-fix lahat ng linter/formatter errors project-wide.
* **Automated code review:** Mag-summarize ng diffs, detect potential risks, at maglagay ng review comments.

### E. Custom Environment & Task Orchestration

* **Install dependencies** (npm, pip, conda, system tools, custom scripts).
* **Snapshot/rollback environment** para mabilis mag-experiment nang hindi masisira ang main branch or main PC.
* **Terminal command chaining:** I-run ang sequences ng shell commands (build, deploy, generate assets, migrate db).

### F. Remote/Headless Operation

* **Run all of the above remotely** sa cloud VM (may internet), habang tuloy-tuloy ka pa rin magtrabaho sa ibang task/local IDE.
* **Slack/Web/Mobile control:** Monitor, takeover, at mag-follow up ng agents kahit hindi ka sa main IDE.

---

## 2. Mga debugging na hindi kayang gawin ng normal Cursor

| Task                         | Normal Cursor | o3-pro MaxMode Background Agent      |
| ---------------------------- | ------------- | ------------------------------------ |
| Mag-debug across many files  | ❌ (manual)    | ✅ (automatic, recursive)             |
| Auto-fix test chains/loops   | ❌             | ✅                                    |
| Auto-resolve merge conflicts | ❌             | ✅                                    |
| CI/CD, env orchestration     | ❌             | ✅ (pwede mag-migrate, build, deploy) |
| Multi-file lint/fix          | ❌             | ✅                                    |
| Detect indirect/deep bugs    | ❌             | ✅ (log, stack trace, dependencies)   |
| Headless/remote ops          | ❌             | ✅                                    |

---

## 3. Tamang Prompting Strategy

### A. General Format

* **Gamitin ang `/agent` command** (sa Cursor command bar, Slack, o web UI)
* Sa IDE: Pwede rin manual via "Ask Cursor" + enable background agent + select Max Mode + o3-pro model.

#### Prompt Template 1: Bulk Refactor

```
/agent
Refactor all usage of the function `get_user_profile` across the entire codebase to use the new signature `get_user_profile(user_id, include_settings=False)`. Update all imports and add type annotations where missing. Run the full test suite and commit the changes if all tests pass.
```

#### Prompt Template 2: Project-wide Debug

```
/agent
Find and fix the root cause of the intermittent `KeyError` exception in the production logs. Trace through all modules involved, patch any unsafe access patterns, and add appropriate error handling. Run all tests and push a PR with your fixes.
```

#### Prompt Template 3: Automated Docs

```
/agent
Add detailed docstrings to all classes and functions in the `services/` and `controllers/` folders. Ensure that each docstring includes the function's purpose, arguments, and return values. Generate a markdown summary of all changes.
```

#### Prompt Template 4: Custom Environment Setup

```
/agent
Install `ffmpeg` and `torch` in the environment, then run all scripts under the `scripts/` folder and report any errors or failed dependencies.
```

#### Prompt Template 5: Mass Linting/Fix

```
/agent
Run black and flake8 across the entire repo, auto-fix all issues, and commit the changes with message "Apply lint and formatting fixes project-wide".
```

### B. Best Practices

* **Be specific:** Sabihin kung anong folders/files, anong klaseng change, at kung anong success criteria (test passing, linter clean, etc).
* **Pwede mo i-chain ang tasks:** "After refactor, run all tests then push a PR. If any fail, retry up to 2 times."
* **Monitor sa web/Slack dashboard:** Para makita status/progress at mag-follow up or i-takeover manually kung needed.

---

## 4. References

* [https://docs.cursor.com/agent/modes](https://docs.cursor.com/agent/modes)
* [https://docs.cursor.com/models](https://docs.cursor.com/models)
* [https://reddit.com/r/cursor](https://reddit.com/r/cursor)
* [https://cursor.com/changelog](https://cursor.com/changelog) 