"""
Root-level entry point for seeding — delegates to backend/scripts/seed.py.
Run from anywhere: python scripts/seed.py
"""
import runpy
import os
import sys

# Resolve the actual seed script relative to this file
_seed = os.path.join(os.path.dirname(__file__), "..", "backend", "scripts", "seed.py")
runpy.run_path(os.path.abspath(_seed), run_name="__main__")
