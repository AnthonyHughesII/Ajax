"""
brains/__init__.py  -  The brain "switchboard"
==============================================
main.py asks this file for a brain by name and gets one back, without
needing to know how any brain works inside.

TO ADD A NEW BRAIN LATER: write brains/yourbrain.py (a class with a think()
method), then add one entry to the if/elif below. Nothing else changes.
"""

import os


def get_brain(name: str | None = None):
    """Return a ready-to-use brain. Defaults to AJAX_BRAIN from your .env."""
    name = (name or os.getenv("AJAX_BRAIN", "ollama")).lower()

    # Imports happen INSIDE each branch on purpose: if you only use Ollama,
    # you don't need the Anthropic library or an API key (and vice versa).
    if name == "claude":
        from .claude_brain import ClaudeBrain
        return ClaudeBrain()
    if name == "ollama":
        from .ollama_brain import OllamaBrain
        return OllamaBrain()

    raise ValueError(f"Unknown brain '{name}'. Choose 'claude' or 'ollama'.")
