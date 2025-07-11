# Agent Architectural Standard

Ito ang opisyal na checklist ng mga panuntunan para sa arkitektura ng bawat ahente sa sistema. Ang bawat ahente ay dapat sumunod sa mga panuntunang ito upang matiyak ang katatagan, maintainability, at kahandaan para sa Dockerization.

---

| ID | Kategorya | Panuntunan (Rule) | Rationale |
| :--- | :--- | :--- | :--- |
| **0** | **Code Correctness** | **ZERO SYNTAX ERRORS.** Ang file ay dapat "compilable" ng Python interpreter. | Ito ang pinaka-pundasyon. Kung ang code ay may syntax error, hindi ito tatakbo kahit kailan. |
| **1** | **Core Foundation** | **Dapat mag-inherit mula sa `common.core.base_agent.BaseAgent`** | Nagbibigay ng pundasyon para sa pangalan, port, at shared methods. |
| **2** | **Configuration Management** | **ZERO HARDCODED VALUES.** Lahat ng settings (ports, paths, flags) ay dapat kunin mula sa `startup_config.yaml` o `os.environ.get()`. | Kritikal para sa Dockerization at maintainability. Nag-iisang source of truth. |
| **3** | **Networking & Service Discovery** | **Dapat gumamit ng `service_discovery_client`**. Bawal ang hardcoded IP/localhost. | Tinitiyak na ang sistema ay "location-transparent". |
| **4.0** | **State Management** | **Bawal umasa sa local files para sa kritikal na state.** Ituring na "cache" ang anumang isinulat sa local filesystem. | Ang mga container ay pansamantala ("ephemeral"). |
| **5** | **Lifecycle & Resource Cleanup** | Dapat may kompletong `_shutdown()` method na isinasara (`close()`) ang LAHAT ng ZMQ sockets at threads. | Nag-iiwas sa "zombie processes" at "memory leaks". |
| **6** | **Health Monitoring** | Dapat magbigay ng **standardized health status** sa pamamagitan ng `health_check()` method. | Para malaman ng external systems kung OK ang ahente. |
| **7.0** | **Logging** | **Dapat mag-log sa `stdout`/`stderr`** gamit ang `logging.StreamHandler`. | Best practice sa Docker para sa sentralisadong logs. |
| **8** | **Error Reporting** | **Dapat gumamit ng central Error Bus** para i-report ang mga hindi inaasahang error. | Nagbibigay ng isang sentral na lugar para makita ang lahat ng problema. |
| **9** | **Dependency Imports** | **Dapat malinis ang imports.** Walang "unused", "missing", o "circular" imports. | Nagpapanatili ng kalinisan ng code at iniiwasan ang mga runtime errors. | 

---

## Standard Report Template & Output Path

Ang sinumang magsasagawa ng audit ay **DAPAT** sumunod sa format na ito at gamitin ang eksaktong output path na nakasaad.

**Output File Path:**
`/home/haymayndz/AI_System_Monorepo/documentation/standards/CONTINUATIONREPORT.MD`

**Report Markdown Structure:**
```markdown
# Agent Audit Report: YYYY-MM-DD

## 1. Executive Summary

- **Agents Scanned:** [Number of agents]
- **Agents with Critical Issues (Violations of Rule 0, 2, 3, 5):** [Count]
- **Total Violations Found:** [Count]
- **Most Common Violations:** [List of Rule IDs, e.g., 2, 9]

---

## 2. Detailed Agent Breakdown

### Agent: `[Full Path to Agent File]`

| Rule ID | Status | Findings (Line # and Issue) |
|:---|:---|:---|
| **0** | `[PASS]` / `[FAIL]` | [Details of syntax errors, or "No syntax errors found."] |
| **1** | `[PASS]` / `[FAIL]` | [Confirmation, or "Does not inherit from BaseAgent."] |
| **2** | `[PASS]` / `[FAIL]` | [Confirmation, or "Line XX: Hardcoded path 'C:\...'.", "Line YY: Hardcoded port 5555."] |
| **3** | `[PASS]` / `[FAIL]` | [Confirmation, or "Line XX: Uses hardcoded 'localhost'."] |
| **4** | `[PASS]` / `[FAIL]` / `[WARN]` | [Confirmation, or "Line XX: Writes to local file 'state.json' for critical state."] |
| **5** | `[PASS]` / `[FAIL]` | [Confirmation, or "Shutdown method is missing socket.close() for self.tts_socket."] |
| **6** | `[PASS]` / `[FAIL]` | [Confirmation, or "No health_check() method found."] |
| **7** | `[PASS]` / `[FAIL]` | [Confirmation, or "Logging is configured to file only, not stdout."] |
| **8** | `[PASS]` / `[FAIL]` | [Confirmation, or "Errors are logged but not sent to a central Error Bus."] |
| **9** | `[PASS]` / `[FAIL]` | [Confirmation, or "Unused import: 'os' on line 12."] |

---

(Ulitin ang "Detailed Agent Breakdown" para sa bawat ahente na in-audit)
```



