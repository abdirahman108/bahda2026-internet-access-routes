"""Let the numbered scripts import the shared code in the lib/ folder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
