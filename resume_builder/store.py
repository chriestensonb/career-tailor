import re
from pathlib import Path

from .models import TailoredResume

_TAILORED_DIR = Path("tailored")
_DEFAULT_CSS = Path(__file__).parent / "style.css"


def _stem(name: str, role: str, date: str) -> str:
    slug = re.sub(r'[<>:"/\\|?*]', "", role)
    return f"{name} - {slug} - {date}"


def save_tailored(resume: TailoredResume, stem: str, css: str) -> Path:
    """Save JSON + CSS to tailored/. Returns the stem path (no extension)."""
    _TAILORED_DIR.mkdir(exist_ok=True)
    base = _TAILORED_DIR / stem
    base.with_suffix(".json").write_text(resume.model_dump_json(indent=2))
    base.with_suffix(".css").write_text(css)
    return base


def load_tailored(json_path: Path) -> TailoredResume:
    return TailoredResume.model_validate_json(json_path.read_text())


def load_css(path: Path | None = None) -> str:
    return (path or _DEFAULT_CSS).read_text()


def save_css(css: str, path: Path) -> None:
    path.write_text(css)


def save_default_css(css: str) -> None:
    save_css(css, _DEFAULT_CSS)


def list_tailored() -> list[Path]:
    """Return sorted list of saved JSON resume paths."""
    if not _TAILORED_DIR.exists():
        return []
    return sorted(_TAILORED_DIR.glob("*.json"))


def stem_for(resume: TailoredResume, date: str) -> str:
    return _stem(resume.full_name, resume.target_role, date)
