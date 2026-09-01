"""Project-local runtime paths and environment helpers."""
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"
DOCUMENTS_DIR = DATA_ROOT / "documents"
COMTRADE_DIR = DATA_ROOT / "comtrade"
INCIDENTS_FILE = DATA_ROOT / "seed" / "incidents.json"
