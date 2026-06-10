"""Quick manual test script — not part of the module."""

import asyncio
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from common.cli import spinner
from common.telemetry import configure_logging
from resume_builder import (
    TweakDeps,
    list_tailored,
    load_css,
    load_tailored,
    save_default_css,
    save_tailored,
    to_pdf,
    tweak_content,
    tweak_visual,
)
from resume_ingest import cli_ask_user

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)


def _pick_resume() -> Path:
    saved = list_tailored()
    if not saved:
        print(
            "No saved resumes found in tailored/. "
            "Run scripts/try_resume_build.py first."
        )
        raise SystemExit(1)
    print("Saved resumes:")
    for i, path in enumerate(saved, 1):
        print(f"  {i}. {path.stem}")
    while True:
        raw = input(f"Pick a resume (1-{len(saved)}): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(saved):
            return saved[int(raw) - 1]
        print("  Invalid choice.")


def _pick_mode() -> str:
    while True:
        raw = input("Tweak (content / visual / both): ").strip().lower()
        if raw in {"content", "visual", "both"}:
            return raw
        print("  Enter 'content', 'visual', or 'both'.")


async def main() -> None:
    load_dotenv()
    configure_logging()

    json_path = _pick_resume()
    css_path = json_path.with_suffix(".css")

    resume = load_tailored(json_path)
    css = load_css(css_path)
    mode = _pick_mode()
    print()

    deps = TweakDeps(ask_user=cli_ask_user)

    if mode in {"content", "both"}:
        resume = await tweak_content(resume, deps)

    if mode in {"visual", "both"}:
        css = await tweak_visual(css, deps)
        confirm = await cli_ask_user(
            "Update your default style with these changes? (yes/no)"
        )
        if confirm.strip().lower() in {"yes", "y"}:
            save_default_css(css)
            print("Default style updated.")

    # Re-render
    today = date.today().isoformat()
    stem = f"{resume.full_name} - {resume.target_role} - {today}"
    html = resume.to_html(css)
    base = save_tailored(resume, stem, css)
    pdf_path = base.with_suffix(".pdf")

    async with spinner("Rendering PDF"):
        await to_pdf(html, pdf_path)

    print(f"\nSaved to: {pdf_path}")


asyncio.run(main())
