import httpx
import pytest
import respx

from brave_search import BraveSearchClient, ResultType, SearchParams
from brave_search.config import BraveSearchConfig

MOCK_WEB = {
    "web": {
        "results": [
            {"title": "R1", "url": "https://example.com/1", "description": "Desc"},
            {"title": "R2", "url": "https://example.com/2"},
        ]
    }
}


@pytest.fixture
def config() -> BraveSearchConfig:
    return BraveSearchConfig(api_key="test-key")


@respx.mock
async def test_search_returns_web_results(config: BraveSearchConfig) -> None:
    respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=httpx.Response(200, json=MOCK_WEB)
    )
    async with BraveSearchClient(config) as client:
        response = await client.search(SearchParams(query="python"))

    assert response.query == "python"
    assert len(response.web) == 2
    assert response.web[0].title == "R1"
    assert response.web[1].description is None


@respx.mock
async def test_search_sends_auth_header(config: BraveSearchConfig) -> None:
    route = respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=httpx.Response(200, json=MOCK_WEB)
    )
    async with BraveSearchClient(config) as client:
        await client.search(SearchParams(query="python"))

    assert route.calls[0].request.headers["X-Subscription-Token"] == "test-key"


@respx.mock
async def test_search_raises_on_http_error(config: BraveSearchConfig) -> None:
    respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=httpx.Response(401)
    )
    async with BraveSearchClient(config) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.search(SearchParams(query="python"))


@respx.mock
async def test_search_empty_results(config: BraveSearchConfig) -> None:
    respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=httpx.Response(200, json={"web": {"results": []}})
    )
    async with BraveSearchClient(config) as client:
        response = await client.search(SearchParams(query="xyzzy"))

    assert response.web == []


@respx.mock
async def test_search_result_filter_and_news(config: BraveSearchConfig) -> None:
    mock_data = {
        "web": {"results": [{"title": "R1", "url": "https://example.com"}]},
        "news": {
            "results": [
                {"title": "N1", "url": "https://news.example.com", "source": "BBC"}
            ]
        },
    }
    route = respx.get("https://api.search.brave.com/res/v1/web/search").mock(
        return_value=httpx.Response(200, json=mock_data)
    )
    async with BraveSearchClient(config) as client:
        response = await client.search(
            SearchParams(
                query="news",
                result_filter=[ResultType.WEB, ResultType.NEWS],
            )
        )

    assert "result_filter=web%2Cnews" in str(route.calls[0].request.url)
    assert response.news is not None
    assert response.news[0].source == "BBC"
