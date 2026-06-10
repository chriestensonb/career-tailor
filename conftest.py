import os
from unittest.mock import AsyncMock

# Allows importing agent modules without a real key; TestModel overrides at run time
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import pytest

from brave_search import BraveSearchClient, SearchResponse, WebResult
from brave_search.config import BraveSearchConfig


@pytest.fixture
def brave_config() -> BraveSearchConfig:
    return BraveSearchConfig(api_key="test-key")


@pytest.fixture
def mock_search_client() -> AsyncMock:
    client = AsyncMock(spec=BraveSearchClient)
    client.search.return_value = SearchResponse(
        query="test",
        web=[WebResult(title="R1", url="https://example.com", description="Desc")],
    )
    return client
