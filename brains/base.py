"""
brains/base.py  -  The contract every brain must follow
=======================================================

WHY THIS FILE EXISTS
--------------------
Claude and Ollama speak different "languages" (different message and tool
formats). If main.py had to know both, every new brain would mean rewriting
main.py. Instead, we define ONE neutral format that Ajax uses internally, and
each brain file translates between that format and its own provider.

THE NEUTRAL MESSAGE FORMAT (used everywhere inside Ajax)
--------------------------------------------------------
Every message in the conversation history is a dictionary shaped like one of
these three:

  You speaking:
    {"role": "user", "text": "make me a file"}

  The brain speaking (text and/or tool requests):
    {"role": "assistant",
     "text": "Sure, creating it now.",
     "tool_calls": [{"id": "call_1", "name": "write_file", "args": {...}}]}

  Tool results going back to the brain:
    {"role": "tool",
     "results": [{"id": "call_1", "name": "write_file", "output": "Created..."}]}

Because the history is neutral, you can even switch brains in the MIDDLE of a
conversation and the new brain can read everything that came before.
"""


class Brain:
    """The parent class. Every brain inherits from this and fills in think()."""

    # A readable label shown when the brain starts, e.g. "claude/claude-sonnet-5-5".
    name = "base"

    def think(self, system: str, messages: list, tools: list) -> dict:
        """
        Read the conversation and return the brain's next message.

        system   -> Ajax's personality/rules text
        messages -> the neutral history described above
        tools    -> the tool menu (written in Claude's schema format)

        Must return a neutral "assistant" message (see top of file).
        """
        raise NotImplementedError("Each brain must implement think().")
