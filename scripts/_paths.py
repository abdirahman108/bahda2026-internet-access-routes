"""Put the shared modules in lib/ on the import path for the numbered scripts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
