"""Quick manual test script — not part of the module."""

import asyncio

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from common.telemetry import configure_logging
from resume_data.store import load_profile, save_profile
from resume_ingest import IngestDeps, cli_ask_user, update

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)


async def main() -> None:
    load_dotenv()
    configure_logging()

    profile = load_profile()
    print(f"Loaded profile: {profile.full_name}")
    print(f"  Jobs: {len(profile.jobs)}  Skills: {len(profile.skills)}")
    print()

    deps = IngestDeps(ask_user=cli_ask_user)
    updated = await update(profile, deps)

    save_profile(updated)
    print(f"\nSaved profile for: {updated.full_name}")
    print(f"  Jobs: {len(updated.jobs)}  Skills: {len(updated.skills)}")


asyncio.run(main())
