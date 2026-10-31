"""Makes `import app...` work when you run plain `pytest` from backend/."""

import sys
from pathlib import Path

# backend/ is the parent of this tests/ folder; `app` lives directly inside it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
