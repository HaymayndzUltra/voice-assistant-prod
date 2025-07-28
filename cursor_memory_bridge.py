import os
from datetime import datetime
from typing import Dict, Any

from cursor_session_manager import session_manager

# Path where the markdown representation of the current session lives
MEMORY_FOLDER = os.path.join(os.getcwd(), "memory-bank")
os.makedirs(MEMORY_FOLDER, exist_ok=True)
SESSION_NOTE = os.path.join(MEMORY_FOLDER, "current-session.md")


# ------------------------------------------------------------------
# Markdown persistence helpers -------------------------------------
# ------------------------------------------------------------------

def _state_to_markdown(state: Dict[str, Any]) -> str:
    """Transform the JSON state into a human-readable Markdown block."""
    cursor = state.get("cursor_session", {})
    lines = [
        f"# 📝 Current Cursor Session — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "| Field | Value |",
        "|-------|-------|",
    ]
    for key in [
        "current_file",
        "cursor_line",
        "current_task",
        "progress",
        "last_activity",
        "disconnected_at",
    ]:
        lines.append(f"| {key} | {cursor.get(key, '—')} |")
    lines.append("")

    # Task history (optional)
    if "task_history" in state and state["task_history"]:
        lines.append("## ✅ Recently completed tasks")
        lines.append("| When | Task |")
        lines.append("|------|------|")
        for item in state["task_history"][-10:]:
            lines.append(f"| {item.get('completed', '—')} | {item.get('task', '—')} |")
        lines.append("")
    return "\n".join(lines)


def dump_markdown() -> None:
    """Persist the current runtime state to the markdown note."""
    md = _state_to_markdown(session_manager.get_state())
    try:
        with open(SESSION_NOTE, "w", encoding="utf-8") as fp:
            fp.write(md)
    except OSError:
        pass


# ------------------------------------------------------------------
# Natural language command interface --------------------------------
# ------------------------------------------------------------------

COMMAND_ALIASES = {
    "anong susunod na task": "next_task",
    "ipagpatuloy muna": "resume",
    "kung saan ako natigil": "where_left_off",
    "tumingin ka sa memory hub folder": "analyze_memory",
}


def _normalize_cmd(cmd: str) -> str:
    return cmd.strip().lower()


def handle_command(command: str) -> str:
    """Basic NL command dispatcher.

    The implementation purposefully stays *very simple* — pattern-matching the
    few Filipino/English phrases outlined in the spec.  Feel free to expand.
    """
    action = COMMAND_ALIASES.get(_normalize_cmd(command), "unknown")

    if action == "next_task":
        return _cmd_next_task()
    if action == "resume":
        return _cmd_resume()
    if action == "where_left_off":
        return _cmd_where_left_off()
    if action == "analyze_memory":
        return _cmd_analyze_memory()
    return "🤔 Pasensya, hindi ko naintindihan ang utos mo. (Unknown command)"


# ------------------------------------------------------------------
# Command implementations -------------------------------------------
# ------------------------------------------------------------------

def _cmd_next_task() -> str:
    state = session_manager.get_state()
    task = state.get("cursor_session", {}).get("current_task")
    if task:
        return f"🔜 Susunod na task: {task}"
    return "📭 Wala pang nakatakdang susunod na task."


def _cmd_resume() -> str:
    state = session_manager.resume_state()
    cursor = state.get("cursor_session", {})
    if cursor:
        file = cursor.get("current_file", "(unknown file)")
        line = cursor.get("cursor_line", "?")
        return (
            "⏯️  Ipagpapatuloy ko mula sa huling posisyon — "
            f"{file} : line {line}."
        )
    return "📭 Walang nakuhang huling session state."


def _cmd_where_left_off() -> str:
    state = session_manager.resume_state()
    cursor = state.get("cursor_session", {})
    if cursor:
        return (
            "📌 Huling estado:\n"
            f"  • File: {cursor.get('current_file', '—')}\n"
            f"  • Line: {cursor.get('cursor_line', '—')}\n"
            f"  • Task: {cursor.get('current_task', '—')}\n"
            f"  • Progress: {cursor.get('progress', '—')}"
        )
    return "ℹ️  No previous state recorded."


def _cmd_analyze_memory() -> str:
    files = [f for f in os.listdir(MEMORY_FOLDER) if f.endswith(".md")]
    bullet = "\n".join(f"  – {name}" for name in files)
    return f"🗂️  The memory hub contains {len(files)} markdown files:\n{bullet}"


# ------------------------------------------------------------------
# CLI entry-point ----------------------------------------------------
# ------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Interact with Cursor memory bridge")
    parser.add_argument("command", nargs="*", help="natural language command to execute")
    parser.add_argument("--dump", action="store_true", help="force markdown dump of state")
    args = parser.parse_args()

    if args.dump:
        dump_markdown()
        print(f"✅ Session state written to {SESSION_NOTE}!")
    else:
        cmd = " ".join(args.command)
        print(handle_command(cmd))