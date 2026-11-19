"""
Work-around for a qiskit-aer import bug.

On import, qiskit-aer looks three folders above itself for a `.git` folder and,
if it finds one, asks git for the commit hash. When the virtual environment
lives inside a git repository (as here: the venv folder *is* the project
repository) that code path crashes with
    AttributeError: 'str' object has no attribute 'decode'

Registering qiskit_aer.version ourselves, with the version read from the
package's VERSION.txt, skips the broken git lookup. On a normal setup (venv
outside the repo) this changes nothing. Import this module before qiskit_aer.
"""

import importlib.util
import sys
import types
from pathlib import Path


def apply():
    if "qiskit_aer.version" in sys.modules:
        return
    spec = importlib.util.find_spec("qiskit_aer")
    if spec is None or spec.origin is None:
        return  # Aer not installed; the caller reports that.
    version_file = Path(spec.origin).parent / "VERSION.txt"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "unknown"
    stub = types.ModuleType("qiskit_aer.version")
    stub.VERSION = version
    stub.__version__ = version
    stub.get_version_info = lambda: version
    stub.git_version = lambda: "Unknown"
    sys.modules["qiskit_aer.version"] = stub


apply()
