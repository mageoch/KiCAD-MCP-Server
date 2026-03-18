"""
pytest configuration — mock pcbnew (KiCAD C extension) before any import.
"""
import sys
from unittest.mock import MagicMock

# pcbnew is a C extension bundled with KiCAD and unavailable in the test venv.
# Inject a mock module so that `import pcbnew` in production code succeeds.
sys.modules.setdefault("pcbnew", MagicMock())

# Make sure the python/ directory is on the path so tests can import commands.
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
