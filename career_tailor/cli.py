import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from common.cli import spinner
from common.telemetry import configure_logging
from resume_builder import build, load_css, stem_for, to_pdf
from resume_data import load_profile, save_profile
from resume_ingest import IngestDeps, cli_ask_user, from_file, from_text, ingest


def _read_stdin_or_file(path: str | None, prompt: str) -> str:
    if path:
        return from_file(Path(path))
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
    profile = load_profile(Path(args.profile))
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
            await to_pdf(resume.to_html(css), pdf_path)
        print(f"Saved PDF: {pdf_path}")
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
    ingest_parser.set_defaults(func=_ingest)

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
    tailor_parser.set_defaults(func=_tailor)
    return parser


async def _run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    load_dotenv(args.env_file)
    configure_logging()
    return await args.func(args)


def main() -> None:
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
