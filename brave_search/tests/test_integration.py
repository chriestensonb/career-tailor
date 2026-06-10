import os

import pytest

from brave_search import BraveSearchClient

pytestmark = pytest.mark.skipif(
    os.getenv("BRAVE_API_KEY") is None,
    reason="BRAVE_API_KEY not set",
)


async def test_real_search() -> None:
    async with BraveSearchClient() as client:
        response = await client.search("python programming", count=3)

    assert len(response.results) > 0
    assert all(r.url.startswith("http") for r in response.results)
