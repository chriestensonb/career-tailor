from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai.models.test import TestModel

from career_agent.agent import agent, ask_clarification, research_career, search_web
from career_agent.deps import CareerAgentDeps
from career_agent.models import CareerHistory


@pytest.fixture
def deps(mock_search_client: AsyncMock) -> CareerAgentDeps:
    return CareerAgentDeps(
        search_client=mock_search_client,
        ask_user=AsyncMock(return_value="no additional info"),
    )


async def test_research_career_returns_history(deps: CareerAgentDeps) -> None:
    with agent.override(model=TestModel()):
        result = await research_career("Jane Doe", deps)
    assert isinstance(result, CareerHistory)


async def test_search_web_formats_results(mock_search_client: AsyncMock) -> None:
    ctx = MagicMock()
    ctx.deps = CareerAgentDeps(search_client=mock_search_client, ask_user=AsyncMock())
    result = await search_web(ctx, "Jane Doe engineer")
    assert "R1" in result
    assert "https://example.com" in result
    mock_search_client.search.assert_called_once()


async def test_search_web_enforces_limit(mock_search_client: AsyncMock) -> None:
    ctx = MagicMock()
    ctx.deps = CareerAgentDeps(
        search_client=mock_search_client, ask_user=AsyncMock(), searches_remaining=0
    )
    result = await search_web(ctx, "anything")
    assert "limit reached" in result.lower()
    mock_search_client.search.assert_not_called()


async def test_ask_clarification_delegates_to_ask_user() -> None:
    ask_user = AsyncMock(return_value="Google, 2018-2022")
    ctx = MagicMock()
    ctx.deps.ask_user = ask_user
    result = await ask_clarification(ctx, "Which company did you work at?")
    assert result == "Google, 2018-2022"
    ask_user.assert_called_once_with("Which company did you work at?")
