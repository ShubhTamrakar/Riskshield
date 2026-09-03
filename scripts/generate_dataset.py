"""
Root-level entry point for generating synthetic datasets.
Run from anywhere: python scripts/generate_dataset.py --size dev --seed 42
"""
import runpy
import os
import sys

_script = os.path.join(os.path.dirname(__file__), "..", "backend", "scripts", "generate_dataset.py")
runpy.run_path(os.path.abspath(_script), run_name="__main__")
