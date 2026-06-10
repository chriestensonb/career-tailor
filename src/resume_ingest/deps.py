from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass
class IngestDeps:
    ask_user: Callable[[str], Awaitable[str]]


async def cli_ask_user(question: str) -> str:
    return input(f"\n{question}\n> ")
