"""Quick manual test script — not part of the module."""

import asyncio  # noqa: F401 — used by asyncio.run()
import sys
from datetime import date

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from common.cli import spinner
from common.telemetry import configure_logging
from resume_builder import (
    build,
    load_css,
    save_tailored,
    stem_for,
    to_pdf,
)
from resume_data.store import load_profile

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)


async def main() -> None:
    load_dotenv()
    configure_logging()

    profile = load_profile()
    print(f"Loaded profile: {profile.full_name}")

    if len(sys.argv) > 1:
        jd_text = open(sys.argv[1]).read()
        print(f"Loaded JD from: {sys.argv[1]}")
    else:
        print("Paste the job description, then press Ctrl+D when done:")
        jd_text = sys.stdin.read()

    async with spinner("Building tailored resume"):
        resume = await build(profile, jd_text)

    print(f"\nTailored for: {resume.target_role}", end="")
    print(f" at {resume.target_company}" if resume.target_company else "")
    print(f"Keywords matched: {len(resume.keywords_matched)}")

    today = date.today().isoformat()
    stem = stem_for(resume, today)
    css = load_css()
    html = resume.to_html(css)

    base = save_tailored(resume, stem, css)
    pdf_path = base.with_suffix(".pdf")

    async with spinner("Rendering PDF"):
        await to_pdf(html, pdf_path)

    print(f"\nSaved to: {pdf_path}")


asyncio.run(main())
