from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class TweakDeps:
    ask_user: Callable[[str], Awaitable[str]]
