import argparse
import asyncio
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from career_tailor.privacy import format_findings, scan_paths
from common.cli import spinner
from common.telemetry import configure_logging
from resume_builder import build, load_css, stem_for, to_pdf
from resume_data import load_profile, save_profile
from resume_ingest import IngestDeps, cli_ask_user, from_file, from_text, ingest


class CLIError(Exception):
    """A user-facing command-line error."""


_PROVIDER_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def _format_path(path: Path) -> str:
    return str(path.expanduser())


def _require_provider_key() -> None:
    model = os.environ.get("CAREER_TAILOR_MODEL", "anthropic:claude-sonnet-4-6")
    provider, has_separator, _ = model.partition(":")
    if not has_separator:
        raise CLIError(
            "CAREER_TAILOR_MODEL must include a provider prefix, for example "
            "'anthropic:claude-sonnet-4-6' or 'openai:<model-name>'."
        )

    env_var = _PROVIDER_KEYS.get(provider)
    if env_var is None:
        known = ", ".join(sorted(_PROVIDER_KEYS))
        raise CLIError(
            f"Unsupported model provider '{provider}' in CAREER_TAILOR_MODEL. "
            f"Known providers: {known}."
        )
    if not os.environ.get(env_var):
        raise CLIError(
            f"Missing {env_var} for CAREER_TAILOR_MODEL='{model}'. "
            f"Add {env_var}=... to your env file or shell environment, or choose "
            "a model provider you have configured."
        )


def _read_stdin_or_file(path: str | None, prompt: str) -> str:
    if path:
        source = Path(path)
        try:
            return from_file(source)
        except FileNotFoundError as exc:
            raise CLIError(
                f"Input file not found: {_format_path(source)}. "
                "Check the path or omit it to paste text via stdin."
            ) from exc
        except ValueError as exc:
            raise CLIError(str(exc)) from exc
    if sys.stdin.isatty():
        print(prompt)
    return from_text(sys.stdin.read())


def _save_tailored(resume, css: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / stem_for(resume, date.today().isoformat())
    base.with_suffix(".json").write_text(resume.model_dump_json(indent=2))
    base.with_suffix(".css").write_text(css)
    base.with_suffix(".md").write_text(resume.to_markdown())
    return base


async def _ingest(args: argparse.Namespace) -> int:
    raw = _read_stdin_or_file(
        args.resume,
        "Paste your resume text, then press Ctrl+D when done:",
    )
    deps = IngestDeps(ask_user=cli_ask_user)
    async with spinner("Extracting profile"):
        profile = await ingest(raw, deps)
    save_profile(profile, Path(args.output))
    print(f"Saved profile for {profile.full_name}: {args.output}")
    return 0


async def _tailor(args: argparse.Namespace) -> int:
    profile_path = Path(args.profile)
    try:
        profile = load_profile(profile_path)
    except FileNotFoundError as exc:
        raise CLIError(
            f"Profile JSON not found: {_format_path(profile_path)}. "
            "Run 'career-tailor ingest <resume.md>' first, or pass an existing "
            "profile with '--profile <path>'."
        ) from exc
    jd_text = _read_stdin_or_file(
        args.job_description,
        "Paste the job description, then press Ctrl+D when done:",
    )

    async with spinner("Building tailored resume"):
        resume = await build(profile, jd_text)

    css = load_css(Path(args.css) if args.css else None)
    base = _save_tailored(resume, css, Path(args.output_dir))
    print(f"Saved markdown: {base.with_suffix('.md')}")
    print(f"Saved JSON: {base.with_suffix('.json')}")

    if args.pdf:
        pdf_path = base.with_suffix(".pdf")
        async with spinner("Rendering PDF"):
            try:
                await to_pdf(resume.to_html(css), pdf_path)
            except Exception as exc:
                message = str(exc)
                missing_browser = (
                    "playwright install" in message
                    or "Executable doesn't exist" in message
                )
                if missing_browser:
                    raise CLIError(
                        "PDF rendering needs Playwright's Chromium browser. "
                        "Install it with: uv run playwright install chromium. "
                        "You can also rerun this command with '--no-pdf'."
                    ) from exc
                raise
        print(f"Saved PDF: {pdf_path}")
    return 0


async def _scan(args: argparse.Namespace) -> int:
    paths = [Path(path) for path in args.paths]
    try:
        result = scan_paths(paths)
    except FileNotFoundError as exc:
        missing = Path(exc.filename or exc.args[0])
        raise CLIError(f"Scan path not found: {_format_path(missing)}") from exc

    if result.findings:
        print(
            f"Privacy scan found {len(result.findings)} possible issue(s) "
            f"across {result.files_scanned} scanned file(s):"
        )
        for line in format_findings(result.findings):
            print(line)
        print(
            "Review these best-effort findings before sharing, committing, "
            "or uploading generated outputs."
        )
        return 1

    print(f"Privacy scan passed: {result.files_scanned} file(s) scanned.")
    if result.skipped_paths and args.verbose:
        print(f"Skipped {len(result.skipped_paths)} unsupported file(s).")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="career-tailor",
        description="Turn a master resume into job-specific resume drafts.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to an env file with model provider keys. Default: .env",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Extract a structured profile from a resume file or stdin.",
    )
    ingest_parser.add_argument("resume", nargs="?", help="Resume text/Markdown file.")
    ingest_parser.add_argument(
        "-o",
        "--output",
        default="data/profile.json",
        help="Profile JSON output path. Default: data/profile.json",
    )
    ingest_parser.set_defaults(func=_ingest, needs_model_provider=True)

    tailor_parser = subparsers.add_parser(
        "tailor",
        help="Create a tailored resume from a profile and job description.",
    )
    tailor_parser.add_argument(
        "job_description",
        nargs="?",
        help="Job description text/Markdown file. Reads stdin when omitted.",
    )
    tailor_parser.add_argument(
        "-p",
        "--profile",
        default="data/profile.json",
        help="Profile JSON path. Default: data/profile.json",
    )
    tailor_parser.add_argument(
        "-o",
        "--output-dir",
        default="tailored",
        help="Directory for generated resume files. Default: tailored",
    )
    tailor_parser.add_argument("--css", help="Optional custom CSS file.")
    tailor_parser.add_argument(
        "--pdf",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Render a PDF with Playwright. Default: true",
    )
    tailor_parser.set_defaults(func=_tailor, needs_model_provider=True)

    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan generated output files for common accidental privacy leaks.",
    )
    scan_parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to scan. Supports .md, .json, .css, .html, .txt.",
    )
    scan_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show unsupported skipped file count.",
    )
    scan_parser.set_defaults(func=_scan, needs_model_provider=False)

    return parser


async def _run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    load_dotenv(args.env_file)
    configure_logging()
    try:
        if getattr(args, "needs_model_provider", True):
            _require_provider_key()
        return await args.func(args)
    except CLIError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
