"""
tools/file_tools.py  -  Ajax's file abilities
==============================================

HOW TOOLS WORK (the big idea)
-----------------------------
Claude can't touch your computer by itself. It can only *ask* for something
to be done. The flow looks like this:

    1. We tell Claude what tools exist (the TOOL_SCHEMAS list at the bottom).
    2. Claude decides it needs one and replies: "please run write_file with
       these arguments".
    3. OUR code (the Python functions below) does the real work.
    4. We send the result back to Claude so it can continue.

So this file has three parts:
    PART 1 - Safety: keep every file action inside one folder.
    PART 2 - The actual Python functions that do the work.
    PART 3 - The "menu" that describes those functions to Claude.
"""

from pathlib import Path  # Path makes working with file paths easy and safe


# ---------------------------------------------------------------------------
# PART 1: THE SANDBOX (safety first)
# ---------------------------------------------------------------------------

# __file__ is this file's location. We climb up two levels (tools/ -> ajax/)
# and then point at a folder called "workspace". This is the ONLY place
# Ajax is allowed to read or write.
SANDBOX = Path(__file__).resolve().parent.parent / "workspace"

# Create the workspace folder if it doesn't exist yet.
# exist_ok=True means "don't crash if it's already there".
SANDBOX.mkdir(exist_ok=True)


def _safe_path(relative_path: str) -> Path:
    """
    Turn a path Claude gives us (like "notes/ideas.md") into a full path,
    and REFUSE anything that tries to escape the workspace.

    Why this matters: without this check, Claude (or a bad instruction hidden
    in a web page, later on) could ask for "../../secret.txt" and read files
    anywhere on your computer. The leading underscore in the name is a Python
    habit meaning "internal helper, not meant to be called from outside".
    """
    # Join the sandbox folder + the requested path, then .resolve() cleans it
    # up (it collapses tricks like ".." into the real final location).
    path = (SANDBOX / relative_path).resolve()

    # Check: is the final location still inside the sandbox? If not, stop.
    if not path.is_relative_to(SANDBOX):
        raise ValueError("Path is outside the workspace sandbox.")

    return path


# ---------------------------------------------------------------------------
# PART 2: THE TOOL FUNCTIONS (the real work happens here)
# ---------------------------------------------------------------------------
# Each function takes simple inputs and returns a short text result, because
# the result gets sent back to Claude as text.

def write_file(path: str, content: str) -> str:
    """Create a new file, or overwrite it if it already exists."""
    # Step 1: validate the path (raises an error if it's outside the sandbox).
    target = _safe_path(path)

    # Step 2: make sure any parent folders exist. If Claude asks for
    # "projects/ajax/plan.md", this creates "projects" and "ajax" first.
    target.parent.mkdir(parents=True, exist_ok=True)

    # Step 3: remember whether the file was already there, so we can report
    # accurately whether we created or overwrote it.
    existed = target.exists()

    # Step 4: actually write the text to disk.
    target.write_text(content, encoding="utf-8")

    # Step 5: return a plain-English result for Claude to read.
    verb = "Overwrote" if existed else "Created"
    return f"{verb} {path} ({len(content)} characters)"


def read_file(path: str) -> str:
    """Return the text inside an existing file."""
    # Validate the path, then read and return the contents.
    # If the file doesn't exist Python raises an error, which main.py catches
    # and passes back to Claude so it knows what went wrong.
    return _safe_path(path).read_text(encoding="utf-8")


def list_files() -> str:
    """Show every file currently in the workspace."""
    # rglob("*") walks through the sandbox and every subfolder.
    # We keep only real files (not folders), show each path relative to the
    # workspace, and sort them alphabetically.
    files = sorted(
        str(p.relative_to(SANDBOX)) for p in SANDBOX.rglob("*") if p.is_file()
    )
    # "\n".join puts one filename per line. If the list is empty, the
    # "or" part provides a friendly fallback message instead.
    return "\n".join(files) or "(workspace is empty)"


# ---------------------------------------------------------------------------
# PART 3: THE MENU FOR CLAUDE
# ---------------------------------------------------------------------------

# A lookup table: tool name (what Claude says) -> Python function (what we run).
# main.py uses this to find the right function when Claude asks for a tool.
TOOL_FUNCTIONS = {
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
}

# The descriptions Claude actually sees. Think of it as a restaurant menu:
#   "name"         - what the tool is called (must match TOOL_FUNCTIONS above)
#   "description"  - plain English telling Claude WHEN to use it
#   "input_schema" - what arguments it needs, written in JSON Schema format
# Clear descriptions = Claude picks the right tool more often.
TOOL_SCHEMAS = [
    {
        "name": "write_file",
        "description": "Create or overwrite a text file in the workspace folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path, e.g. notes/ideas.md",
                },
                "content": {"type": "string", "description": "Full file contents"},
            },
            # Claude must provide both of these every time.
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a text file from the workspace folder.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Relative path"}},
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files in the workspace folder.",
        # This tool needs no arguments, so "properties" is empty.
        "input_schema": {"type": "object", "properties": {}},
    },
]
