import time

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from brave_search import SearchParams
from common.telemetry import get_logger, get_tracer

from .config import CareerAgentConfig
from .deps import CareerAgentDeps
from .models import CareerHistory

tracer = get_tracer("career_agent")
logger = get_logger("career_agent")

_cfg = CareerAgentConfig()

agent: Agent[CareerAgentDeps, CareerHistory] = Agent(
    _cfg.model,
    output_type=CareerHistory,
    deps_type=CareerAgentDeps,
    defer_model_check=True,  # key read from ANTHROPIC_API_KEY at run time, not import
    system_prompt=(
        "You research professional career histories from web sources.\n\n"
        "You have exactly 10 searches. Budget them — each search costs one.\n\n"
        "Strategy:\n"
        "- Review your conversation history before each search — never repeat "
        "a query or a close variant of one you already ran\n"
        "- Start broad (name + 'career' or 'LinkedIn'), then narrow only if needed\n"
        "- Extract everything useful from each result before deciding whether "
        "to search again\n"
        "- When the tool tells you searches are exhausted, immediately compile "
        "your best answer from what you have — do not attempt another search\n\n"
        "Use ask_clarification only when you genuinely cannot proceed — e.g. a "
        "very common name with no distinguishing context, or conflicting records "
        "requiring the user to confirm.\n\n"
        "Be honest about confidence. Partial info is better than guessing. "
        "Record source URLs per employment entry."
    ),
)


@agent.tool
async def search_web(ctx: RunContext[CareerAgentDeps], query: str) -> str:
    """Search the web for career information about a person."""
    if ctx.deps.searches_remaining <= 0:
        return (
            "Search limit reached — no searches remaining. "
            "Compile your final answer from the information already gathered."
        )
    ctx.deps.searches_remaining -= 1
    remaining = ctx.deps.searches_remaining
    response = await ctx.deps.search_client.search(
        SearchParams(query=query, count=5, extra_snippets=True)
    )
    header = f"[{remaining} searches remaining]"
    if not response.web:
        return f"{header} No results found."
    lines = [header]
    for i, r in enumerate(response.web, 1):
        lines.append(f"{i}. {r.title} — {r.url}")
        if r.description:
            lines.append(f"   {r.description}")
        if r.extra_snippets:
            lines.extend(f"   {s}" for s in r.extra_snippets)
    return "\n".join(lines)


@agent.tool
async def ask_clarification(ctx: RunContext[CareerAgentDeps], question: str) -> str:
    """Ask the user a clarifying question and return their answer."""
    return await ctx.deps.ask_user(question)


async def research_career(name: str, deps: CareerAgentDeps) -> CareerHistory:
    with tracer.start_as_current_span("career_agent.research") as span:
        span.set_attribute("career.name", name)
        t0 = time.perf_counter()
        result = await agent.run(
            f"Research the complete career history for: {name}",
            deps=deps,
            usage_limits=UsageLimits(request_limit=_cfg.request_limit),
        )
        usage = result.usage()
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        span.set_attribute("career.elapsed_ms", elapsed_ms)
        span.set_attribute("llm.requests", usage.requests)
        span.set_attribute("llm.tool_calls", usage.tool_calls)
        span.set_attribute("llm.input_tokens", usage.input_tokens)
        span.set_attribute("llm.output_tokens", usage.output_tokens)
        logger.info(
            "research.complete",
            name=name,
            elapsed_ms=elapsed_ms,
            employments=len(result.output.employments),
            confidence=result.output.confidence,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            requests=usage.requests,
            tool_calls=usage.tool_calls,
        )
        return result.output
