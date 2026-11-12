"""
brains/ollama_brain.py  -  Adapter for Ollama (free, runs on your computer)
===========================================================================
Ollama runs open models (Qwen, Llama, Gemma...) locally. No API key, no
per-use cost. Same job as claude_brain.py, different translation rules.

BEFORE USING: install Ollama, then download a model once, e.g.
    ollama pull qwen2.5:7b
Ollama must be running in the background when Ajax starts.
"""

import os
import uuid

import ollama

from .base import Brain


class OllamaBrain(Brain):
    def __init__(self):
        # The model to run, and where the Ollama server lives (your own PC).
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = ollama.Client(host=host)
        self.name = f"ollama/{self.model}"

    # ------------------------------------------------------------------
    # TRANSLATION 0: tool menu. Ollama wants a slightly different layout
    # than Claude, so we re-wrap the same information.
    # ------------------------------------------------------------------
    def _to_ollama_tools(self, tools: list) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],  # same schema, new label
                },
            }
            for t in tools
        ]

    # ------------------------------------------------------------------
    # TRANSLATION 1: neutral history -> Ollama's message format
    # ------------------------------------------------------------------
    def _to_ollama_messages(self, system: str, messages: list) -> list:
        # Ollama takes the system prompt as the first message in the list
        # (Claude takes it as a separate setting).
        converted = [{"role": "system", "content": system}]

        for m in messages:
            if m["role"] == "user":
                converted.append({"role": "user", "content": m["text"]})

            elif m["role"] == "assistant":
                msg = {"role": "assistant", "content": m["text"]}
                if m["tool_calls"]:
                    msg["tool_calls"] = [
                        {"function": {"name": c["name"], "arguments": c["args"]}}
                        for c in m["tool_calls"]
                    ]
                converted.append(msg)

            elif m["role"] == "tool":
                # Ollama wants ONE "tool" message per result, matched by
                # tool name (it doesn't use ids like Claude does).
                for r in m["results"]:
                    converted.append(
                        {"role": "tool", "tool_name": r["name"], "content": r["output"]}
                    )
        return converted

    # ------------------------------------------------------------------
    # THE MAIN JOB: call the local model and translate the answer back
    # ------------------------------------------------------------------
    def think(self, system: str, messages: list, tools: list) -> dict:
        response = self.client.chat(
            model=self.model,
            messages=self._to_ollama_messages(system, messages),
            tools=self._to_ollama_tools(tools),
        )
        msg = response.message

        # TRANSLATION 2: Ollama's answer -> neutral assistant message.
        # Ollama doesn't create ids for tool requests, but our neutral format
        # (and Claude) need them, so we generate unique ones ourselves.
        calls = [
            {
                "id": "call_" + uuid.uuid4().hex[:12],
                "name": tc.function.name,
                "args": dict(tc.function.arguments),
            }
            for tc in (msg.tool_calls or [])
        ]
        return {"role": "assistant", "text": msg.content or "", "tool_calls": calls}
