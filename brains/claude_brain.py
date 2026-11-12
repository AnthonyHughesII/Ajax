"""
brains/claude_brain.py  -  Adapter for the Claude API (paid, most capable)
==========================================================================
Job: translate Ajax's neutral messages INTO Claude's format, call Claude,
then translate Claude's answer BACK into the neutral format.
"""

import os

from anthropic import Anthropic

from .base import Brain


class ClaudeBrain(Brain):
    def __init__(self):
        # Reads ANTHROPIC_API_KEY from the environment (loaded from .env).
        self.client = Anthropic()
        # Which Claude model to use; change it in .env without touching code.
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
        self.name = f"claude/{self.model}"

    # ------------------------------------------------------------------
    # TRANSLATION 1: neutral history -> Claude's message format
    # ------------------------------------------------------------------
    def _to_claude_messages(self, messages: list) -> list:
        converted = []
        for m in messages:
            if m["role"] == "user":
                # Plain text from you stays plain text.
                converted.append({"role": "user", "content": m["text"]})

            elif m["role"] == "assistant":
                # Claude wants assistant messages as a list of "blocks":
                # a text block, plus one tool_use block per tool request.
                blocks = []
                if m["text"]:
                    blocks.append({"type": "text", "text": m["text"]})
                for call in m["tool_calls"]:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": call["id"],
                            "name": call["name"],
                            "input": call["args"],
                        }
                    )
                # Claude rejects empty messages, so add a placeholder if needed.
                if not blocks:
                    blocks.append({"type": "text", "text": "(no response)"})
                converted.append({"role": "assistant", "content": blocks})

            elif m["role"] == "tool":
                # Claude expects tool results inside a "user" message, with
                # each result linked to its request by the matching id.
                converted.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": r["id"],
                                "content": r["output"],
                            }
                            for r in m["results"]
                        ],
                    }
                )
        return converted

    # ------------------------------------------------------------------
    # THE MAIN JOB: call Claude and translate the answer back
    # ------------------------------------------------------------------
    def think(self, system: str, messages: list, tools: list) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=system,
            tools=tools,  # our tool schemas are already in Claude's format
            messages=self._to_claude_messages(messages),
        )

        # TRANSLATION 2: Claude's blocks -> neutral assistant message.
        text = "".join(b.text for b in response.content if b.type == "text")
        calls = [
            {"id": b.id, "name": b.name, "args": b.input}
            for b in response.content
            if b.type == "tool_use"
        ]
        return {"role": "assistant", "text": text, "tool_calls": calls}
