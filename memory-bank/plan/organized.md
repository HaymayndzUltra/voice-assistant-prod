1. 🗒️  2024_master_bug_remediation
   Description: A prioritized action plan to fix critical, high, medium, and low severity bugs a...
   Status: in_progress
   Created: 2024-05-24T12:00:00Z
   TODO Items (5):
      [✗] 0. PHASE 0: SETUP & PROTOCOL (READ FIRST)

**Core Behavioral Mandates**
*   **Execute Sequentially:** Phases are ordered by severity (Critical → High → Medium → Low). Do not skip phases. The system's stability depends on fixing critical issues first.
*   **Verify Rigorously:** Each task includes a `Proposed Fix`. Do not mark a phase complete until all fixes are implemented and have passed relevant tests.
*   **Consult Context:** Each task includes `Root Cause & Impact` to provide a deep understanding of the bug, helping to prevent regressions.

**How-To/Workflow Protocol**
This plan is managed by a script, `todo_manager.py`.
1.  **To Show Plan State:** `python3 todo_manager.py show 2024_master_bug_remediation`
2.  **To Mark a Phase Complete:** `python3 todo_manager.py done 2024_master_bug_remediation [phase_index]` (e.g., `... done 2024_master_bug_remediation 0` for this phase).
3.  **Follow the Protocol:** At the end of each phase, you will find a `Concluding Step` protocol. Follow it exactly to maintain plan integrity.

**Concluding Step: Phase Completion Protocol**
To formally conclude this phase, update the plan's state, and prepare for the next, execute the following protocol:
1.  **Run Command (Mark Complete):** `python3 todo_manager.py done 2024_master_bug_remediation 0`
2.  **Analyze Next Phase:** Before proceeding, read and understand the 'Context' and 'Technical Artifacts' for Phase 1.

──────────────────────────────────
IMPORTANT NOTE: This phase contains the operating manual for this entire remediation plan. Completing it signifies your understanding of the process. Failure to follow the protocol can lead to incorrect state tracking.
      [✗] 1. PHASE 1: CRITICAL BUGS

**Task 1: Fix ZMQ REP socket pool misuse, undefined endpoints, and context misuse**
*   **Context (Root Cause & Impact):** Pool helpers bind REP sockets by default, but agents are binding them again, causing `Address already in use` errors. Furthermore, some agents overwrite `self.context` with `None` or use an undefined `self.endpoint`, leading to `AttributeError` crashes. This results in widespread agent startup failures and service unavailability.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** Agents obtain already-bound REP sockets and bind them again, use undefined endpoints, and/or nullify the ZMQ context before use.
    *   **Location(s):**
        *   `common/pools/zmq_pool.py`: 123-129, 398-402
        *   `main_pc_code/agents/emotion_engine.py`: 122-146
        *   `main_pc_code/agents/emotion_engine_enhanced.py`: 141-160
        *   `main_pc_code/agents/chitchat_agent.py`: 79-86
        *   `main_pc_code/agents/nlu_agent.py`: 147-153
        *   `main_pc_code/agents/face_recognition_agent.py`: 484-494
        *   `main_pc_code/agents/executor.py`: 121-129
    *   **Proposed Fix:** For server-side REP sockets, stop using the pooled `get_rep_socket` helper. Instead, create sockets directly via `self.context.socket(zmq.REP)` and bind them once. Do not overwrite `self.context`. Ensure `self.endpoint` is defined before use or remove the reference if unnecessary.

**Task 2: Remediate untrusted deserialization with pickle (RCE risk)**
*   **Context (Root Cause & Impact):** The use of `pickle.loads` on untrusted network data is a severe security vulnerability. A specially crafted message can execute arbitrary commands on the host machine, leading to a full system compromise.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** Network messages are deserialized via the unsafe `pickle.loads` function.
    *   **Location(s):**
        *   `main_pc_code/agents/fused_audio_preprocessor.py`: 709-713
        *   `main_pc_code/agents/streaming_interrupt_handler.py`: 226-228
    *   **Proposed Fix:** Replace `pickle` with a safe serialization format like JSON or MsgPack. Strictly validate the schema of all incoming data. Consider adding message authentication (e.g., HMAC) if the channel is untrusted.

**Task 3: Fix asyncio task creation with synchronous methods in ModelOps app**
*   **Context (Root Cause & Impact):** The `asyncio.create_task()` function requires a coroutine (an `async def` function). The code is passing regular synchronous functions (`start()`), which return `None`. This raises a `TypeError` at startup, preventing the ModelOps Coordinator service from booting entirely.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** `asyncio.create_task()` is called with synchronous `start()` methods.
    *   **Location(s):**
        *   `model_ops_coordinator/app.py`: 247-252, 260-263
        *   `model_ops_coordinator/transport/grpc_server.py`: 336-376
        *   `model_ops_coordinator/transport/rest_api.py`: 503-518
    *   **Proposed Fix:** Either convert the `start()` methods to `async def` or wrap the synchronous calls using `loop.run_in_executor(None, self.server.start)`.

**Concluding Step: Phase Completion Protocol**
To formally conclude this phase, update the plan's state, and prepare for the next, execute the following protocol:
1.  **Run Command (Review State):** `python3 todo_manager.py show 2024_master_bug_remediation`
2.  **Run Command (Mark Complete):** `python3 todo_manager.py done 2024_master_bug_remediation 1`
3.  **Analyze Next Phase:** Before proceeding, read and understand the 'Context' and 'Technical Artifacts' for Phase 2.

──────────────────────────────────
IMPORTANT NOTE: The bugs in this phase are critical. They cause agents to crash on startup or introduce severe remote code execution vulnerabilities. The system is unstable and insecure until this phase is complete.
      [✗] 2. PHASE 2: HIGH-SEVERITY BUGS

**Task 4: Fix invalid ErrorPublisher PUB socket pattern**
*   **Context (Root Cause & Impact):** The `ErrorPublisher` gets a PUB socket from a pool that binds it to an endpoint, but then the code attempts to `connect()` with it. A PUB socket should either bind (if it's a central collector) or connect (if it's a publisher), but not both. Binding to a remote endpoint will fail, silently disabling the entire error reporting bus.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** A pooled, bound PUB socket is then used with `.connect()`.
    *   **Location(s):**
        *   `main_pc_code/agents/error_publisher.py`: 41-52
        *   `common/pools/zmq_pool.py`: 123-129, 404-408
    *   **Proposed Fix:** Create a plain PUB socket with `zmq.Context.instance().socket(zmq.PUB)` and only call `.connect(self.endpoint)`. Alternatively, modify the pool helper to support a `bind=False` option for publisher sockets.

**Task 5: Remediate code injection risk from `eval()` in metrics alerts**
*   **Context (Root Cause & Impact):** Using `eval()` on dynamically constructed strings is a major security risk. A misconfiguration or a maliciously crafted alert condition can lead to arbitrary code execution, causing instability or system compromise.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** Alert conditions are checked using `eval()`.
    *   **Location(s):** `common/observability/metrics.py`: 60-66
    *   **Proposed Fix:** Do not use `eval()`. Parse the condition string safely. For example, use a regular expression to extract the operator (e.g., '>', '==', '<') and the value, then use the safe `operator` module (e.g., `operator.gt`, `operator.eq`) to perform the comparison.

**Task 6: Fix mixed sync/async calls in shutdown path**
*   **Context (Root Cause & Impact):** The shutdown logic attempts to `await asyncio.gather()` on a list of tasks that contains the results of synchronous `stop()` calls. Since sync functions return `None` (not a coroutine), this raises a `TypeError`, preventing a graceful shutdown and potentially leaving orphaned processes or resources.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** `asyncio.gather()` is called with non-awaitable results from synchronous functions.
    *   **Location(s):**
        *   `model_ops_coordinator/app.py`: 290-299
        *   `model_ops_coordinator/transport/grpc_server.py`: 377-407
        *   `model_ops_coordinator/transport/rest_api.py`: 533-546
    *   **Proposed Fix:** Make the `stop()` methods `async def`, or wrap the synchronous calls in `loop.run_in_executor` before passing them to `gather`.

**Task 7: Secure REST API (Fail-closed auth and restricted CORS)**
*   **Context (Root Cause & Impact):** The API is "fail-open": if an API key isn't configured, authentication is simply disabled. Combined with a wildcard CORS policy (`allow_origins=["*"]`), this exposes the entire ModelOps API to unauthenticated control from any website, a major security flaw.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** Auth is disabled when `api_key` is missing, and CORS is open to all origins.
    *   **Location(s):** `model_ops_coordinator/transport/rest_api.py`: 190-197, 220-224
    *   **Proposed Fix:** The API must be "fail-closed". If the API key is missing in a production environment, the application should refuse to start or reject all requests by default. Restrict `allow_origins` to a specific list of trusted domains.

**Concluding Step: Phase Completion Protocol**
To formally conclude this phase, update the plan's state, and prepare for the next, execute the following protocol:
1.  **Run Command (Review State):** `python3 todo_manager.py show 2024_master_bug_remediation`
2.  **Run Command (Mark Complete):** `python3 todo_manager.py done 2024_master_bug_remediation 2`
3.  **Analyze Next Phase:** Before proceeding, read and understand the 'Context' and 'Technical Artifacts' for Phase 3.

──────────────────────────────────
IMPORTANT NOTE: This phase addresses high-severity security vulnerabilities and architectural flaws. Completing it is essential for securing the system and ensuring its long-term stability.
      [✗] 3. PHASE 3: MEDIUM-SEVERITY BUGS

**Task 8: Ensure GPU lease-sweeper thread is joined on shutdown**
*   **Context (Root Cause & Impact):** The sweeper thread, which reclaims GPU resources, is signaled to stop but is never explicitly joined. This creates a race condition during interpreter shutdown, which can lead to incomplete VRAM accounting or unclean exits.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** The sweeper thread is not joined.
    *   **Location(s):** `model_ops_coordinator/transport/grpc_server.py`: 49-51 (start), 399-405 (stop without join)
    *   **Proposed Fix:** After setting the stop event (`self.servicer._lease_sweeper_stop.set()`), call `self.servicer._lease_sweeper.join(timeout=5)` to wait for the thread to finish.

**Task 9: Fix data race on shared `voice_buffer` list**
*   **Context (Root Cause & Impact):** Multiple threads are accessing and modifying the `self.voice_buffer` list without any synchronization. A `len()` check can pass, but another thread can `pop(0)` the last item before the first thread does, causing an `IndexError` and data loss.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** Unsynchronized access to a shared list from multiple threads.
    *   **Location(s):** `main_pc_code/agents/face_recognition_agent.py`: 200-208
    *   **Proposed Fix:** Replace the standard `list` with the thread-safe `queue.Queue()`, or protect all access to the list (appends, pops, checks) with a `threading.Lock()`.

**Task 10: Remove silent error swallowing in machine auto-detection**
*   **Context (Root Cause & Impact):** A bare `except: pass` block is used during GPU/machine detection. This is dangerous because it hides all underlying errors, including critical ones like `FileNotFoundError` or security exceptions. This makes debugging extremely difficult.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** A bare `except: pass` hides all exceptions.
    *   **Location(s):** `common/utils/unified_config_loader.py`: 97-105
    *   **Proposed Fix:** Catch only the specific exceptions you expect (e.g., `subprocess.CalledProcessError`, `FileNotFoundError`). Log any caught exceptions clearly with their traceback, and then either re-raise them or return an explicit fallback value.

**Concluding Step: Phase Completion Protocol**
To formally conclude this phase, update the plan's state, and prepare for the next, execute the following protocol:
1.  **Run Command (Review State):** `python3 todo_manager.py show 2024_master_bug_remediation`
2.  **Run Command (Mark Complete):** `python3 todo_manager.py done 2024_master_bug_remediation 3`
3.  **Analyze Next Phase:** Before proceeding, read and understand the 'Context' and 'Technical Artifacts' for Phase 4.

──────────────────────────────────
IMPORTANT NOTE: These medium-severity bugs relate to race conditions and poor error handling. Fixing them will improve the system's robustness, thread safety, and debuggability.
      [✗] 4. PHASE 4: LOW-SEVERITY BUGS

**Task 11: Reduce TTL reaper cadence to prevent transient VRAM over-allocation**
*   **Context (Root Cause & Impact):** The lease sweeper runs only once per second. In scenarios with rapid model loading/unloading, this coarse window can allow the total allocated VRAM to temporarily exceed the soft cap for up to 999ms, potentially causing an Out-Of-Memory (OOM) error on GPUs with limited VRAM.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** The 1.0s sweeper interval is too long.
    *   **Location(s):** `model_ops_coordinator/transport/grpc_server.py`: 269-276
    *   **Proposed Fix:** Reduce the sleep interval to a smaller value (e.g., 0.1 seconds) or implement a VRAM reservation system that keeps a small percentage of VRAM as a buffer.

**Task 12: Add shutdown checks to infinite background loops**
*   **Context (Root Cause & Impact):** Many background threads and utility exporters use a `while True:` loop without any mechanism to stop them. This means they will ignore shutdown signals, causing the main process to hang or be forcefully killed, preventing a clean exit.
*   **Technical Artifacts / Tasks:**
    *   **The Bug:** `while True:` loops lack a stop condition.
    *   **Location(s) (representative):** `main_pc_code/agents/face_recognition_agent.py`: 200-208
    *   **Proposed Fix:** In each loop, check a `threading.Event` or a boolean flag (e.g., `while not stop_event.is_set():`). Ensure the loop includes a short `time.sleep()` to prevent busy-waiting and allow the event to be processed.

**Concluding Step: Plan Completion Protocol**
To formally conclude this plan, update its state by executing the following protocol:
1.  **Run Command (Review State):** `python3 todo_manager.py show 2024_master_bug_remediation`
2.  **Run Command (Mark Complete):** `python3 todo_manager.py done 2024_master_bug_remediation 4`

──────────────────────────────────
IMPORTANT NOTE: This final phase addresses low-severity bugs that improve resource management and ensure graceful shutdowns. Completing this phase finalizes the stabilization effort