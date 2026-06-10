"""Quick manual test script — not part of the module."""

import asyncio
import json

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from brave_search import BraveSearchClient, SearchParams
from common.telemetry import configure_logging

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)


async def main() -> None:
    load_dotenv()
    configure_logging()
    query = input("Query: ").strip()
    async with BraveSearchClient() as client:
        response = await client.search(SearchParams(query=query, count=5))
    print(json.dumps(response.model_dump(exclude_none=True), indent=2))


asyncio.run(main())
