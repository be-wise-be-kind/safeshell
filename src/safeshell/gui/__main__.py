"""
File: src/safeshell/gui/__main__.py
Purpose: Entry point for running GUI as module (python -m safeshell.gui)
"""
# ruff: noqa: E402 - must configure logger before importing gui

import os

from loguru import logger

# Suppress loguru output for GUI (must be before importing gui module)
logger.remove()
logger.add(os.devnull, level="DEBUG")

from safeshell.gui import run_gui

if __name__ == "__main__":
    run_gui()
