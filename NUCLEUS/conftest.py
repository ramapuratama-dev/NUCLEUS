"""Make the project root importable so tests can import the top-level modules."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
