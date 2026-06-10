import os
from pathlib import Path

from .models import ResumeProfile

_DEFAULT_PATH = Path("data/profile.json")


def _resolve(path: Path | None) -> Path:
    return path or Path(os.environ.get("RESUME_DATA_PATH", _DEFAULT_PATH))


def load_profile(path: Path | None = None) -> ResumeProfile:
    """Load a ResumeProfile from JSON. Raises FileNotFoundError if missing."""
    return ResumeProfile.model_validate_json(_resolve(path).read_text())


def save_profile(profile: ResumeProfile, path: Path | None = None) -> None:
    """Persist a ResumeProfile as indented JSON, creating parent dirs as needed."""
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(profile.model_dump_json(indent=2))
