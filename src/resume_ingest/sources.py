from pathlib import Path

# Extensions handled natively. Add to this set when new sources are implemented.
_TEXT_EXTENSIONS = {".txt", ".md"}


def from_text(text: str) -> str:
    """Pass raw text through — the identity source."""
    return text.strip()


def from_file(path: Path) -> str:
    """Read plain text from a .txt or .md file.

    Raises ValueError for unsupported types with a hint toward the right function.
    PDF support: use from_pdf() once resume_ingest.sources.from_pdf is available.
    """
    if path.suffix.lower() not in _TEXT_EXTENSIONS:
        supported = ", ".join(sorted(_TEXT_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type '{path.suffix}'. "
            f"Supported: {supported}. "
            "For PDF use from_pdf() when available."
        )
    return path.read_text().strip()
