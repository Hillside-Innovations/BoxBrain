"""Pytest config: use a temp dir for DB and storage so tests don't touch real data."""
import os
from pathlib import Path
import tempfile

# Set env before any backend module imports config (conftest runs first).
_tmp = Path(tempfile.mkdtemp(prefix="boxbrain_test_"))
os.environ.setdefault("DB_PATH", str(_tmp / "boxbrain.db"))
os.environ.setdefault("CHROMA_PATH", str(_tmp / "chroma"))
os.environ.setdefault("UPLOADS_DIR", str(_tmp / "uploads"))
os.environ.setdefault("FRAMES_DIR", str(_tmp / "frames"))
os.environ.setdefault("DATA_DIR", str(_tmp))
os.environ.setdefault("MOCK_VISION", "1")
