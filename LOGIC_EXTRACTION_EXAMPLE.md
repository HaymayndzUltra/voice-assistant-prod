# LOGIC EXTRACTION EXAMPLE - How to Preserve ALL Logic

## ANG TANONG: "MAKUKUHA TALAGA ANG BUONG LOGICS?"

**SAGOT: OO, 100% MAKUKUHA!** Pero kailangan nating gawin ito nang TAMA.

---

## EXAMPLE: RequestCoordinator Logic Extraction

### ❌ ANG MALI (What we did before):
```python
# Generic implementation - WALANG ACTUAL LOGIC!
class TaskRouter:
    def route_task(self, task):
        return {"status": "routed"}  # MALI!
```

### ✅ ANG TAMA (What we should do):

#### STEP 1: Extract ALL Methods from RequestCoordinator
```python
# From RequestCoordinator line 524-570
def _calculate_priority(self, task_type, request):
    """
    EXACT LOGIC from RequestCoordinator - PRESERVED!
    """
    # Base priority by task type
    base_priority = {
        'audio_processing': 1,  # Highest priority
        'text_processing': 2,
        'vision_processing': 3,
        'background_task': 5    # Lowest priority
    }.get(task_type, 3)  # Default priority
    
    # Adjust for user profile if available
    user_id = request.user_id
    user_priority_adjustment = 0
    if user_id:
        user_profiles = {
            "admin": -2,        # Higher priority (lower number)
            "premium": -1,
            "standard": 0,
            "guest": 1          # Lower priority (higher number)
        }
        user_type = request.metadata.get("user_type", "standard")
        user_priority_adjustment = user_profiles.get(user_type, 0)
    
    # Adjust for urgency level from metadata
    urgency = request.metadata.get("urgency", "normal")
    urgency_adjustment = {
        "critical": -3,
        "high": -1,
        "normal": 0,
        "low": 1
    }.get(urgency, 0)
    
    # System load adjustment
    system_load_adjustment = 0
    if len(self.task_queue) > self.queue_max_size * 0.8:
        system_load_adjustment = 1
    
    # Calculate final priority (lower is higher priority)
    final_priority = base_priority + user_priority_adjustment + urgency_adjustment + system_load_adjustment
    
    # Ensure priority is within reasonable bounds
    return max(1, min(10, final_priority))
```

#### STEP 2: Extract Circuit Breaker Logic
```python
# From RequestCoordinator line 740-780
def _process_task(self, task: TaskDefinition):
    """
    EXACT LOGIC from RequestCoordinator - PRESERVED!
    """
    task_type = task.task_type
    logger.info(f"Dispatching task {task.task_id} of type {task_type}")

    # Expanded routing logic
    if 'audio' in task_type or 'vision' in task_type:
        target_service, target_socket = 'got_tot', self.got_tot_socket
    else:
        target_service, target_socket = 'cot', self.cot_socket

    breaker = self.circuit_breakers.get(target_service)
    if not breaker or not breaker.allow_request():
        logger.warning(f"Circuit for {target_service} is open. Dropping task {task.task_id}.")
        return

    try:
        if not target_socket:
            raise ConnectionError(f"Socket for {target_service} is not available.")

        response_dict = self.send_request_to_agent(
            agent_name=target_service,
            request=task.model_dump(),
            timeout=ZMQ_REQUEST_TIMEOUT
        )
        
        response = AgentResponse.model_validate(response_dict)
        self._handle_task_response(response)
        breaker.record_success()
    except Exception as e:
        error_data = {
            "error_type": "task_processing_error",
            "message": f"Failed to process task {task.task_id}: {str(e)}",
            "severity": str(ErrorSeverity.ERROR),
            "context": {"task_id": task.task_id, "service": target_service, "task_type": task_type}
        }
        self.report_error(error_data)
        logger.error(f"Failed to process task {task.task_id} with {target_service}: {e}")
        if breaker: breaker.record_failure()
```

#### STEP 3: Extract Queue Management Logic
```python
# From RequestCoordinator line 650-680
def add_task_to_queue(self, priority: int, task: TaskDefinition):
    """
    EXACT LOGIC from RequestCoordinator - PRESERVED!
    """
    with self.queue_lock:
        if len(self.task_queue) >= self.queue_max_size:
            logger.warning("Task queue full. Rejecting new task.")
            return
        heapq.heappush(self.task_queue, (priority, time.time(), task))
        logger.info(f"Task {task.task_id} added to queue. Size: {len(self.task_queue)}")

def _dispatch_loop(self):
    """
    EXACT LOGIC from RequestCoordinator - PRESERVED!
    """
    while self.running:
        if self.interrupt_flag.is_set():
            time.sleep(0.1)
            continue
        
        task_item = None
        with self.queue_lock:
            if self.task_queue:
                task_item = heapq.heappop(self.task_queue)
        
        if task_item:
            _priority, _timestamp, task = task_item
            self._process_task(task)
        else:
            time.sleep(0.05)
```

---

## COMPLETE TASKROUTER WITH ALL LOGIC PRESERVED

```python
class TaskRouter(BaseAgent):
    """
    TaskRouter - Consolidated agent with ALL original logic preserved
    Combines: RequestCoordinator + TaskScheduler + AdvancedRouter + AsyncProcessor + ResourceManager + TieredResponder
    """
    
    def __init__(self, **kwargs):
        port = kwargs.get('port', 7000)
        super().__init__(name="TaskRouter", port=port, health_check_port=port + 1000)
        
        # PRESERVED from RequestCoordinator
        self.context = zmq.Context()
        self.running = True
        self.start_time = time.time()
        self.interrupt_flag = threading.Event()
        
        # PRESERVED: Queue management
        self.task_queue = []
        self.queue_lock = threading.Lock()
        self.queue_max_size = kwargs.get('params', {}).get('queue_max_size', 100)
        
        # PRESERVED: Circuit breakers
        self.circuit_breakers = {}
        self._init_circuit_breakers()
        
        # PRESERVED: Metrics and monitoring
        self.metrics = {
            "requests_total": 0,
            "requests_by_type": {"text": 0, "audio": 0, "vision": 0},
            "success": 0,
            "failure": 0,
            "response_times": {"text": [], "audio": [], "vision": []},
            "queue_sizes": [],
            "last_updated": datetime.now().isoformat()
        }
        self.metrics_lock = threading.Lock()
        
        # PRESERVED: ZMQ sockets
        self._init_zmq_sockets()
        
        # PRESERVED: Background threads
        self._start_threads()
        
    def _calculate_priority(self, task_type, request):
        """
        EXACT LOGIC from RequestCoordinator - PRESERVED!
        """
        # Base priority by task type
        base_priority = {
            'audio_processing': 1,  # Highest priority
            'text_processing': 2,
            'vision_processing': 3,
            'background_task': 5    # Lowest priority
        }.get(task_type, 3)  # Default priority
        
        # Adjust for user profile if available
        user_id = request.user_id
        user_priority_adjustment = 0
        if user_id:
            user_profiles = {
                "admin": -2,        # Higher priority (lower number)
                "premium": -1,
                "standard": 0,
                "guest": 1          # Lower priority (higher number)
            }
            user_type = request.metadata.get("user_type", "standard")
            user_priority_adjustment = user_profiles.get(user_type, 0)
        
        # Adjust for urgency level from metadata
        urgency = request.metadata.get("urgency", "normal")
        urgency_adjustment = {
            "critical": -3,
            "high": -1,
            "normal": 0,
            "low": 1
        }.get(urgency, 0)
        
        # System load adjustment
        system_load_adjustment = 0
        if len(self.task_queue) > self.queue_max_size * 0.8:
            system_load_adjustment = 1
        
        # Calculate final priority (lower is higher priority)
        final_priority = base_priority + user_priority_adjustment + urgency_adjustment + system_load_adjustment
        
        # Ensure priority is within reasonable bounds
        return max(1, min(10, final_priority))
    
    def _process_task(self, task: TaskDefinition):
        """
        EXACT LOGIC from RequestCoordinator - PRESERVED!
        """
        task_type = task.task_type
        logger.info(f"Dispatching task {task.task_id} of type {task_type}")

        # Expanded routing logic
        if 'audio' in task_type or 'vision' in task_type:
            target_service, target_socket = 'got_tot', self.got_tot_socket
        else:
            target_service, target_socket = 'cot', self.cot_socket

        breaker = self.circuit_breakers.get(target_service)
        if not breaker or not breaker.allow_request():
            logger.warning(f"Circuit for {target_service} is open. Dropping task {task.task_id}.")
            return

        try:
            if not target_socket:
                raise ConnectionError(f"Socket for {target_service} is not available.")

            response_dict = self.send_request_to_agent(
                agent_name=target_service,
                request=task.model_dump(),
                timeout=ZMQ_REQUEST_TIMEOUT
            )
            
            response = AgentResponse.model_validate(response_dict)
            self._handle_task_response(response)
            breaker.record_success()
        except Exception as e:
            error_data = {
                "error_type": "task_processing_error",
                "message": f"Failed to process task {task.task_id}: {str(e)}",
                "severity": str(ErrorSeverity.ERROR),
                "context": {"task_id": task.task_id, "service": target_service, "task_type": task_type}
            }
            self.report_error(error_data)
            logger.error(f"Failed to process task {task.task_id} with {target_service}: {e}")
            if breaker: breaker.record_failure()
    
    def add_task_to_queue(self, priority: int, task: TaskDefinition):
        """
        EXACT LOGIC from RequestCoordinator - PRESERVED!
        """
        with self.queue_lock:
            if len(self.task_queue) >= self.queue_max_size:
                logger.warning("Task queue full. Rejecting new task.")
                return
            heapq.heappush(self.task_queue, (priority, time.time(), task))
            logger.info(f"Task {task.task_id} added to queue. Size: {len(self.task_queue)}")

    def _dispatch_loop(self):
        """
        EXACT LOGIC from RequestCoordinator - PRESERVED!
        """
        while self.running:
            if self.interrupt_flag.is_set():
                time.sleep(0.1)
                continue
            
            task_item = None
            with self.queue_lock:
                if self.task_queue:
                    task_item = heapq.heappop(self.task_queue)
            
            if task_item:
                _priority, _timestamp, task = task_item
                self._process_task(task)
            else:
                time.sleep(0.05)
    
    # ADD LOGIC FROM OTHER AGENTS...
    def detect_task_type(self, prompt):
        """
        EXACT LOGIC from AdvancedRouter - PRESERVED!
        """
        # Task type detection patterns
        patterns = {
            'code': ['write', 'create', 'implement', 'function', 'class'],
            'reasoning': ['explain', 'why', 'how', 'analyze'],
            'chat': ['hello', 'hi', 'how are you'],
            'creative': ['imagine', 'create', 'design', 'invent']
        }
        
        prompt_lower = prompt.lower()
        for task_type, keywords in patterns.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return task_type
        return 'general'
    
    def _handle_response_tiering(self, query):
        """
        EXACT LOGIC from TieredResponder - PRESERVED!
        """
        text = query.get('text', '').lower()
        
        # Instant response patterns
        instant_patterns = ['hello', 'hi', 'kumusta', 'thanks', 'bye']
        if any(pattern in text for pattern in instant_patterns):
            return self._handle_instant_response(query)
        
        # Fast response patterns
        fast_patterns = ['what is', 'who is', 'when is', 'how to']
        if any(pattern in text for pattern in fast_patterns):
            return self._handle_fast_response(query)
        
        # Default to deep analysis
        return self._handle_deep_response(query)
```

---

## KEY POINTS:

### ✅ WHAT WE PRESERVE:
1. **Every method** from original agents
2. **Every algorithm** (priority calculation, task detection, etc.)
3. **Every data structure** (queues, locks, circuit breakers)
4. **Every ZMQ pattern** (REQ/REP, PUB/SUB, etc.)
5. **Every business logic** (user profiles, urgency levels, etc.)

### ❌ WHAT WE DON'T DO:
1. **Generic implementations** - "return {'status': 'routed'}"
2. **Simplified logic** - Remove complex algorithms
3. **New patterns** - Change established communication
4. **Lost functionality** - Drop any original features

### 🎯 RESULT:
**TaskRouter will have EXACTLY the same functionality as all 6 original agents combined!**

---

## TEMPLATE FOR EXTRACTION:

```python
# BEFORE EXTRACTING:
1. Read the COMPLETE source code
2. List ALL methods and their purposes
3. Identify ALL algorithms and data structures
4. Map ALL ZMQ communication patterns
5. Document ALL business logic

# DURING IMPLEMENTATION:
1. Copy EXACT method signatures
2. Preserve EXACT algorithm logic
3. Maintain EXACT data structures
4. Keep EXACT communication patterns
5. Include EXACT error handling

# AFTER IMPLEMENTATION:
1. Test with EXACT same inputs
2. Verify EXACT same outputs
3. Confirm EXACT same behavior
4. Validate EXACT same performance
```

**BOTTOM LINE**: Oo, makukuha talaga ang buong logic, pero kailangan nating gawin ito nang TAMA - extract first, implement second, test thoroughly! 