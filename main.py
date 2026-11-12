"""
main.py  -  Project Ajax, Phase 1.5 (swappable brains)
======================================================

WHAT CHANGED FROM BEFORE
------------------------
main.py no longer talks to Claude directly. It talks to a "brain" object that
could be Claude or Ollama. All the provider-specific code now lives in the
brains/ folder, so this file stays clean and never needs to change when you
add new brains.

THE FLOW
--------
    You type a message
          |
          v
    brain.think(...)  <------------------------------+
          |                                          |
          v                                          |
    Did the brain request tools?                     |
       |-- YES -> run them, add results to history --+
       |-- NO  -> print the answer, wait for you

COMMANDS YOU CAN TYPE IN THE CHAT
---------------------------------
    /brain claude    switch to Claude (paid, smartest)
    /brain ollama    switch to the free local model
    exit             quit
"""

# ---------------------------------------------------------------------------
# STEP 1: IMPORTS
# ---------------------------------------------------------------------------
from dotenv import load_dotenv  # loads your .env settings

from brains import get_brain  # the brain switchboard
from tools.file_tools import TOOL_FUNCTIONS, TOOL_SCHEMAS  # tool menu + code

# Load .env FIRST so every setting (API key, brain choice) is available.
load_dotenv()

# ---------------------------------------------------------------------------
# STEP 2: THE SYSTEM PROMPT - Ajax's personality, shared by ALL brains
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are Ajax, a personal AI assistant built by and for your user.
You help run, automate, and improve their businesses, ideas, and projects.
Be direct, practical, and concise. Use your tools when they help, and tell the
user plainly what you did. If a request is risky or unclear, ask first."""


# ---------------------------------------------------------------------------
# STEP 3: RUNNING A TOOL (unchanged: the brain only ASKS, this code ACTS)
# ---------------------------------------------------------------------------
def run_tool(name: str, args: dict) -> str:
    try:
        # Look up the real Python function by name and call it with the
        # arguments the brain provided. ** unpacks the dictionary.
        return str(TOOL_FUNCTIONS[name](**args))
    except Exception as exc:
        # Errors go back to the brain as text so it can adapt (never crash).
        return f"Error: {exc}"


# ---------------------------------------------------------------------------
# STEP 4: ONE FULL TURN - works with ANY brain
# ---------------------------------------------------------------------------
def chat_turn(brain, messages: list) -> str:
    """Get the brain's final answer, running any requested tools on the way."""
    while True:
        # 4a. Ask the brain to think. We pass the neutral history; the brain
        # translates it to its own format internally.
        reply = brain.think(SYSTEM_PROMPT, messages, TOOL_SCHEMAS)

        # 4b. Save the reply in the history (already in neutral format).
        messages.append(reply)

        # 4c. No tool requests? The brain is done, so return its text.
        if not reply["tool_calls"]:
            return reply["text"]

        # 4d. Otherwise run every requested tool and collect the results.
        results = []
        for call in reply["tool_calls"]:
            print(f"  [tool] {call['name']}({call['args']})")
            results.append(
                {
                    "id": call["id"],  # links the result to its request
                    "name": call["name"],
                    "output": run_tool(call["name"], call["args"]),
                }
            )

        # 4e. Add the results to the history; the loop runs again so the
        # brain can read them and continue.
        messages.append({"role": "tool", "results": results})


# ---------------------------------------------------------------------------
# STEP 5: THE MAIN LOOP - talking to YOU
# ---------------------------------------------------------------------------
def main():
    # Pick the starting brain from your .env (AJAX_BRAIN=claude or ollama).
    brain = get_brain()
    print(f"Ajax online using {brain.name}.")
    print("Commands: /brain claude | /brain ollama | exit\n")

    # The neutral conversation history. Lives outside the loop, so Ajax
    # remembers earlier messages while the program runs.
    messages = []

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue

        # Handle the /brain command: swap brains without losing the chat.
        if user_input.lower().startswith("/brain"):
            try:
                brain = get_brain(user_input.split(maxsplit=1)[1])
                print(f"Switched to {brain.name}.\n")
            except Exception as exc:
                print(f"Couldn't switch brain: {exc}\n")
            continue

        # Remember how long the history was, so we can undo this turn if the
        # brain fails (for example, Ollama isn't running).
        history_length = len(messages)
        messages.append({"role": "user", "text": user_input})

        try:
            print(f"\nAjax: {chat_turn(brain, messages)}\n")
        except Exception as exc:
            # Roll back the failed turn so the history stays valid, then
            # report the problem instead of crashing.
            del messages[history_length:]
            print(f"\n[brain error] {exc}\n")


# ---------------------------------------------------------------------------
# STEP 6: START THE PROGRAM (only when run directly: python main.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
