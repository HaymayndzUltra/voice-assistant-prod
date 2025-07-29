from ollama_client import call_ollama
import json

system_prompt = """You are an expert AI assistant specializing in task decomposition and workflow planning. Your primary function is to act as a reasoning engine. You will be given a user's command, often in a mix of English and Filipino (Taglish), and your goal is to break it down into a precise, logical, and actionable sequence of steps.

You MUST adhere to the following strict rules:
1.  **Identify Core Intent:** Your first priority is to understand the user's ultimate goal. Focus only on the concrete, actionable parts of the command.
2.  **Decompose Logically:** Break down the command into the smallest possible logical steps. The plan must be sequential, but you must also identify conditional branches and opportunities for parallel execution.
3.  **Use Structured Tags:** Annotate specific steps with the following tags for clarity:
    *   `[PREREQUISITE]` for steps that must be completed before the main action.
    *   `[CONDITIONAL]` for steps that depend on an if/else outcome.
    *   `[PARALLEL]` for steps that can be executed concurrently.
4.  **Ensure Completeness:** Do not omit any steps mentioned in the user's command.
5.  **Eliminate Redundancy:** Do not create duplicate or overlapping steps. Each step in your plan must be unique and distinct.
6.  **Output Format is CRITICAL:** Your entire output MUST be a single, valid JSON object with a 'steps' key containing an array of strings.

Example output:
```json
{
  "steps": [
    "[PREREQUISITE] First step description",
    "[CONDITIONAL] If X happens: do Y",
    "[PARALLEL] These steps can run simultaneously"
  ]
}
```"""

user_prompt = """
- Phase 1: System Analysis & Cleanup
    - Inventory all existing Docker/Podman containers, images, and compose files.
    - Delete all old containers/images/compose files.
    - Identify all agent groups, dependencies, and required libraries.
- Phase 2: Logical Grouping & Compose Generation
    - Design optimal container groupings (by function, dependency, resource needs).
    - Generate new docker-compose SoT with correct build contexts, volumes, networks, and healthchecks.
    - Ensure requirements.txt per container is minimal and correct.
- Phase 3: Validation & Optimization
    - Build and start all containers in dependency-correct order.
    - Validate agent startup, health, and inter-container communication.
    - Optimize for image size, startup time, and resource usage.
    - Document the new architecture and compose setup.
"""
print("Sending Docker/Podman task decomposition request to Ollama...")
result = call_ollama(user_prompt, system_prompt=system_prompt)

# Process the response
if isinstance(result, dict) and 'raw_response' in result:
    print("\nRaw response from Ollama:")
    print("-" * 50)
    print(result['raw_response'])
    
    # Try to extract and parse JSON
    def extract_json_from_response(text):
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                fixed = match.group(0).replace('\n', ' ').replace('  ', ' ')
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
        return {"error": "failed_to_parse_json", "raw_response": text}
    
    print("\nAttempting to extract JSON...")
    json_data = extract_json_from_response(result['raw_response'])
    print("\nExtracted JSON:")
    print(json.dumps(json_data, indent=2))
else:
    print("\nResponse from Ollama:")
    print(json.dumps(result, indent=2))
