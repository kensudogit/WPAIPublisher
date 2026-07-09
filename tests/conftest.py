"""pytest 共通設定"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(SCRIPTS / "intake") not in sys.path:
    sys.path.insert(0, str(SCRIPTS / "intake"))
