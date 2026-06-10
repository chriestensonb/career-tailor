"""Quick manual test script — not part of the module."""

import asyncio
import json

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from brave_search import BraveSearchClient
from career_agent import CareerAgentDeps, cli_ask_user, research_career
from common.telemetry import configure_logging

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)


async def main() -> None:
    load_dotenv()
    configure_logging()
    name = input("Name to research: ").strip()
    async with BraveSearchClient() as client:
        deps = CareerAgentDeps(search_client=client, ask_user=cli_ask_user)
        result = await research_career(name, deps)
    print(json.dumps(result.model_dump(exclude_none=True), indent=2))


asyncio.run(main())
