from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SCANNED_EXTENSIONS = {".css", ".html", ".json", ".md", ".txt"}

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(
    r"""
    (?<!\w)
    (?:\+?1[\s.-]?)?
    (?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}
    (?!\w)
    """,
    re.VERBOSE,
)
_ENV_ASSIGNMENT = re.compile(
    r"(?m)^\s*(?:export\s+)?[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)\s*="
)
_OPENAI_KEY = re.compile(r"\bsk-(?!ant-)[A-Za-z0-9_-]{20,}\b")
_ANTHROPIC_KEY = re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")
_ABSOLUTE_PATH = re.compile(r"(?<![\w.-])(?:/Users|/home|/var/folders|/tmp)/[^\s)\"']+")


@dataclass(frozen=True)
class PrivacyFinding:
    path: Path
    line: int
    kind: str
    message: str
    sample: str


@dataclass(frozen=True)
class ScanResult:
    files_scanned: int
    findings: list[PrivacyFinding]
    skipped_paths: list[Path]


@dataclass(frozen=True)
class _Rule:
    kind: str
    message: str
    pattern: re.Pattern[str]


_RULES = [
    _Rule("email", "Possible email address", _EMAIL),
    _Rule("phone", "Possible phone number", _PHONE),
    _Rule("env-secret", "Possible env-style secret assignment", _ENV_ASSIGNMENT),
    _Rule("openai-key", "Possible OpenAI API key", _OPENAI_KEY),
    _Rule("anthropic-key", "Possible Anthropic API key", _ANTHROPIC_KEY),
    _Rule("absolute-path", "Possible local absolute path", _ABSOLUTE_PATH),
]


def _iter_files(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    skipped: list[Path] = []
    for path in paths:
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if not child.is_file():
                    continue
                if child.suffix.lower() in SCANNED_EXTENSIONS:
                    files.append(child)
                else:
                    skipped.append(child)
        elif path.is_file() and path.suffix.lower() in SCANNED_EXTENSIONS:
            files.append(path)
        elif path.exists():
            skipped.append(path)
        else:
            raise FileNotFoundError(path)
    return files, skipped


def _line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _sample(value: str) -> str:
    compact = " ".join(value.strip().split())
    return compact[:80]


def scan_paths(paths: list[Path]) -> ScanResult:
    """Scan supported text output files for common accidental privacy leaks."""
    files, skipped = _iter_files(paths)
    findings: list[PrivacyFinding] = []

    for path in files:
        text = path.read_text(errors="replace")
        for rule in _RULES:
            for match in rule.pattern.finditer(text):
                findings.append(
                    PrivacyFinding(
                        path=path,
                        line=_line_number(text, match.start()),
                        kind=rule.kind,
                        message=rule.message,
                        sample=_sample(match.group(0)),
                    )
                )

    return ScanResult(
        files_scanned=len(files),
        findings=findings,
        skipped_paths=skipped,
    )


def format_findings(findings: list[PrivacyFinding]) -> list[str]:
    lines: list[str] = []
    for finding in findings:
        lines.append(
            f"{finding.path}:{finding.line}: {finding.kind}: "
            f"{finding.message}: {finding.sample}"
        )
    return lines
