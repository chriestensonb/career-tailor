from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from brave_search import BraveSearchClient


@dataclass
class CareerAgentDeps:
    search_client: BraveSearchClient
    ask_user: Callable[[str], Awaitable[str]]
    searches_remaining: int = 10


async def cli_ask_user(question: str) -> str:
    return input(f"\n{question}\n> ")
