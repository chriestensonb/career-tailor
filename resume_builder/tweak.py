import difflib

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from common.telemetry import get_logger, get_tracer

from .deps import TweakDeps
from .models import TailoredResume

tracer = get_tracer("resume_builder")
logger = get_logger("resume_builder")

_MODEL = "anthropic:claude-sonnet-4-6"


class _CSSOutput(BaseModel):
    css: str


_content_tweak_agent: Agent[TweakDeps, TailoredResume] = Agent(
    _MODEL,
    output_type=TailoredResume,
    deps_type=TweakDeps,
    defer_model_check=True,
    system_prompt=(
        "You are a collaborative resume coach helping the user refine a "
        "tailored resume.\n\n"
        "When the user describes what they want to change:\n"
        "- Engage with their intent, ask clarifying questions if needed\n"
        "- Flag related improvements you notice while you're in there\n"
        "- Confirm what you're about to change before returning the result\n\n"
        "Rules:\n"
        "- Preserve all content that wasn't discussed\n"
        "- Never fabricate facts — only capture what the user confirms\n"
        "- Keep bullets concise and impact-focused"
    ),
)

_visual_tweak_agent: Agent[TweakDeps, _CSSOutput] = Agent(
    _MODEL,
    output_type=_CSSOutput,
    deps_type=TweakDeps,
    defer_model_check=True,
    system_prompt=(
        "You are helping the user adjust the visual style of their resume "
        "by editing CSS.\n\n"
        "The CSS uses these classes:\n"
        "  body, h1, h2, header, .contact, .section\n"
        "  .job, .job-header, .job-title, .job-company, .job-meta\n"
        "  ul, li, .skills\n"
        "  .edu, .edu-header, .edu-degree, .edu-dates, .edu-highlights\n\n"
        "When the user describes a visual change:\n"
        "- Ask clarifying questions if the request is ambiguous\n"
        "- Explain what you're changing and why before applying\n"
        "- Make targeted edits — don't restructure unrelated rules\n"
        "- Return the complete updated CSS"
    ),
)


@_content_tweak_agent.tool
@_visual_tweak_agent.tool
async def ask_clarification(ctx: RunContext[TweakDeps], question: str) -> str:
    """Ask the user a question to clarify or confirm a change."""
    return await ctx.deps.ask_user(question)


def _diff_tailored(before: TailoredResume, after: TailoredResume) -> list[str]:
    changes: list[str] = []

    for field in (
        "full_name",
        "email",
        "phone",
        "location",
        "summary",
        "target_role",
        "target_company",
    ):
        b, a = getattr(before, field), getattr(after, field)
        if b != a:
            changes.append(f"  ~ {field}: {b!r} → {a!r}")

    before_skills = set(before.skills)
    after_skills = set(after.skills)
    for s in sorted(after_skills - before_skills):
        changes.append(f"  + skill: {s}")
    for s in sorted(before_skills - after_skills):
        changes.append(f"  - skill: {s}")

    before_jobs = {(j.company, j.role): j for j in before.jobs}
    after_jobs = {(j.company, j.role): j for j in after.jobs}
    for company, role in sorted(set(after_jobs) - set(before_jobs)):
        changes.append(f"  + job: {role} at {company}")
    for company, role in sorted(set(before_jobs) - set(after_jobs)):
        changes.append(f"  - job: {role} at {company}")
    for key in set(before_jobs) & set(after_jobs):
        bj, aj = before_jobs[key], after_jobs[key]
        if bj == aj:
            continue
        company, role = key
        changes.append(f"  ~ job: {role} at {company}")
        before_bullets = set(bj.bullets)
        after_bullets = set(aj.bullets)
        for b in sorted(after_bullets - before_bullets):
            changes.append(f"      + {b}")
        for b in sorted(before_bullets - after_bullets):
            changes.append(f"      - {b}")

    return changes


def _diff_css(before: str, after: str) -> list[str]:
    return list(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="current",
            tofile="updated",
            lineterm="",
            n=2,
        )
    )


async def tweak_content(resume: TailoredResume, deps: TweakDeps) -> TailoredResume:
    """Interactively refine resume content. Loops until user types exit/done."""
    current = resume
    with tracer.start_as_current_span("resume_builder.tweak_content"):
        while True:
            request = await deps.ask_user(
                "What would you like to change? (or 'exit' to finish)"
            )
            if request.strip().lower() in {"exit", "done", "quit", "q"}:
                break

            result = await _content_tweak_agent.run(
                f"Current resume:\n{current.model_dump_json(indent=2)}\n\n"
                f"Change request: {request}",
                deps=deps,
                usage_limits=UsageLimits(request_limit=20),
            )
            updated = result.output
            diff = _diff_tailored(current, updated)
            if not diff:
                await deps.ask_user(
                    "No changes detected — please try rephrasing. (press Enter)"
                )
                continue

            confirm = await deps.ask_user(
                "Changes to apply:\n" + "\n".join(diff) + "\n\nConfirm? (yes/no)"
            )
            if confirm.strip().lower() in {"yes", "y"}:
                current = updated
                logger.info("tweak_content.applied", changes=len(diff))

    return current


async def tweak_visual(css: str, deps: TweakDeps) -> str:
    """Interactively refine resume CSS. Loops until user types exit/done."""
    current = css
    with tracer.start_as_current_span("resume_builder.tweak_visual"):
        while True:
            request = await deps.ask_user(
                "What would you like to adjust visually? (or 'exit' to finish)"
            )
            if request.strip().lower() in {"exit", "done", "quit", "q"}:
                break

            result = await _visual_tweak_agent.run(
                f"Current CSS:\n{current}\n\nChange request: {request}",
                deps=deps,
                usage_limits=UsageLimits(request_limit=20),
            )
            updated = result.output.css
            diff = _diff_css(current, updated)
            if not diff:
                await deps.ask_user(
                    "No changes detected — please try rephrasing. (press Enter)"
                )
                continue

            confirm = await deps.ask_user(
                "CSS changes to apply:\n" + "\n".join(diff) + "\n\nConfirm? (yes/no)"
            )
            if confirm.strip().lower() in {"yes", "y"}:
                current = updated
                logger.info("tweak_visual.applied", diff_lines=len(diff))

    return current
