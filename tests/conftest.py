"""Test configuration: make the repo root importable.

The harness is run from the repo root (python cli.py / python gui.py), so
top-level imports like `ai_helper` and `cli_backends` expect the root on
sys.path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
