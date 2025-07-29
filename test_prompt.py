from ollama_client import call_ollama
import json
import re

def extract_json_from_response(text):
    """Extract JSON from text response, handling malformed JSON"""
    # Try to find JSON object in the response
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            # If JSON is malformed, try to fix common issues
            fixed = match.group(0).replace('\n', ' ').replace('  ', ' ')
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
    return {"error": "failed_to_parse_json", "raw_response": text}

system_prompt = """You are an expert AI assistant specializing in task decomposition and workflow planning. Your primary function is to act as a reasoning engine. You will be given a user's command, often in a mix of English and Filipino (Taglish), and your goal is to break it down into a precise, logical, and actionable sequence of steps.

You MUST adhere to the following strict rules:
1.  **Identify Core Intent:** Your first priority is to understand the user's ultimate goal. Ignore introductory, conversational phrases like "Let's build..." or "Gawin natin...". Focus only on the concrete, actionable parts of the command.
2.  **Decompose Logically:** Break down the command into the smallest possible logical steps. The plan must be sequential, but you must also identify conditional branches and opportunities for parallel execution.
3.  **Use Structured Tags:** Annotate specific steps with the following tags for clarity:
    *   `[PREREQUISITE]` for steps that must be completed before the main action.
    *   `[CONDITIONAL]` for steps that depend on an if/else outcome.
    *   `[PARALLEL]` for steps that can be executed concurrently.
4.  **Ensure Completeness:** Do not omit any steps mentioned in the user's command.
5.  **Eliminate Redundancy:** Do not create duplicate or overlapping steps. Each step in your plan must be unique and distinct.
6.  **Output Format is CRITICAL:** Your entire output MUST be a single, valid JSON object. This JSON object must contain a single key, `"steps"`, whose value is a list of strings. Each string in the list represents one decomposed step from the plan. Do not output any text, explanation, or markdown before or after the JSON object.

Example output:
```json
{
  "steps": [
    "[PREREQUISITE] Update database schema to include users table",
    "[CONDITIONAL] If credentials are correct: generate JWT token",
    "[CONDITIONAL] If credentials are incorrect: return 401 Unauthorized error"
  ]
}
```"""

user_prompt = """Let's build the new user authentication feature. First, update the database schema to include a 'users' table. If the credentials are correct, it must return a JWT. If they are incorrect, it must return a 401 Unauthorized error."""

print("Sending prompt to Ollama...")
result = call_ollama(user_prompt, system_prompt=system_prompt)

# Process the response
if isinstance(result, dict) and 'raw_response' in result:
    print("\nRaw response from Ollama:")
    print("-" * 50)
    print(result['raw_response'])
    
    # Try to extract and parse JSON
    print("\nAttempting to extract JSON...")
    json_data = extract_json_from_response(result['raw_response'])
    print("\nExtracted JSON:")
    print(json.dumps(json_data, indent=2))
else:
    print("\nResponse from Ollama:")
    print(json.dumps(result, indent=2))
