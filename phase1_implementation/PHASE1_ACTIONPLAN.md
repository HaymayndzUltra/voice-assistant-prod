Agent Consolidation Task
Objective:
Consolidate the following legacy agents into a single unified agent/service.
It is CRUCIAL that you preserve ALL logic, error handling, imports, helper functions, and interface patterns from each original agent.
No part of the original agent's logic or pattern should be lost or omitted during this process.

Instructions for Consolidation
Lossless Merge (Walang Makakalimutan):

Import or migrate all code from each agent as modules, classes, or sub-apps.
DO NOT discard, rewrite, or drop any logic, error handling, or reusable code—retain everything from each source agent.
Preserve and Integrate Patterns:

Keep all original error handling, logging, helper imports, and interface patterns.
If logic overlaps (e.g. same method names), use adapters or wrapper classes to avoid overwriting.
Namespace schemas, tables, or memory keys to prevent collisions (e.g. session_, kb_, etc.).
Maintain API Compatibility:

Expose legacy endpoints (routes, methods) as sub-routes or sub-apps so that any old integrations still work.
If deprecating any endpoint, mark it clearly but do not remove support.
Modular Structure:

Organize merged code in a modular way: each legacy agent’s logic should be traceable and testable after the merge.
Use clear comments and sections for each legacy agent’s logic within the unified agent.
Testing and Documentation:

After merging, ensure all original agent logic is covered by tests (unit/integration).
Update or generate documentation mapping legacy agent features to the unified agent structure.
Migration Scripts:

If there are schema or data changes, generate migration scripts or adapters to ensure smooth data transition.
Example Agent List for Consolidation
MemoryClient
SessionMemoryAgent
KnowledgeBase
MemoryOrchestratorService
UnifiedMemoryReasoningAgent
ContextManager
ExperienceTracker
CacheManager
ProactiveContextMonitor
UnifiedUtilsAgent
AuthenticationAgent
AgentTrustScorer
Output
Unified agent/service codebase with ALL logic, error handling, and patterns preserved.
Modular structure (not copy-paste, not mixed up).
Legacy API compatibility.
Documentation and migration scripts.
Tagalog Reminder:
Siguraduhin na WALANG logic, error handling, imports, o pattern na mawawala o maliligtaan. Bawat dating agent ay dapat may traceable na bahagi sa bagong unified agent.

END OF INSTRUCTION.