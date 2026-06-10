"""Quick manual test script — not part of the module."""

import asyncio
import sys

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from common.cli import spinner
from common.telemetry import configure_logging
from resume_data import save_profile
from resume_ingest import IngestDeps, cli_ask_user, from_file, from_text, ingest

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)


async def main() -> None:
    load_dotenv()
    if len(sys.argv) > 1:
        raw = from_file(__import__("pathlib").Path(sys.argv[1]))
        print(f"Loaded file: {sys.argv[1]}")
    else:
        print("Paste your resume text, then press Ctrl+D when done:")
        raw = from_text(sys.stdin.read())

    configure_logging()
    deps = IngestDeps(ask_user=cli_ask_user)
    async with spinner("Extracting profile"):
        profile = await ingest(raw, deps)
    save_profile(profile)
    print(f"\nSaved profile for: {profile.full_name}")
    print(f"  Jobs: {len(profile.jobs)}")
    print(f"  Skills: {len(profile.skills)}")
    print("  Saved to: data/profile.json")


asyncio.run(main())
