import os
import time
from datetime import date

from pydantic_ai import Agent, RunContext
from pydantic_ai.usage import UsageLimits

from common.telemetry import get_logger, get_tracer
from resume_data import ResumeProfile

from .deps import IngestDeps

tracer = get_tracer("resume_ingest")
logger = get_logger("resume_ingest")

_MODEL = os.environ.get("CAREER_TAILOR_MODEL", "anthropic:claude-sonnet-4-6")
_TODAY = date.today().isoformat()

_extract_agent: Agent[None, ResumeProfile] = Agent(
    _MODEL,
    output_type=ResumeProfile,
    defer_model_check=True,
    system_prompt=(
        f"Extract a complete structured resume profile from the text provided. "
        f"Today's date is {_TODAY} — use it for last_updated and to infer "
        f"relative dates where needed.\n\n"
        "Rules:\n"
        "- Separate responsibilities (day-to-day duties, verb phrases) from "
        "achievements (quantified impact with numbers where present)\n"
        "- Use YYYY-MM date format; YYYY alone if month is unknown\n"
        "- Leave fields as null rather than guessing\n"
        "- Jobs should be ordered newest first\n"
        "- Capture all skills mentioned, categorised appropriately"
    ),
)

_enhance_agent: Agent[IngestDeps, ResumeProfile] = Agent(
    _MODEL,
    output_type=ResumeProfile,
    deps_type=IngestDeps,
    defer_model_check=True,
    system_prompt=(
        "You are reviewing an extracted resume profile for gaps and weak spots. "
        "Your goal is to improve quality by asking the user targeted questions.\n\n"
        "Look for:\n"
        "- Jobs with no achievements (only responsibilities) — ask for impact\n"
        "- Missing start or end dates — ask which month/year\n"
        "- Vague skill descriptions — ask for context or proficiency level\n"
        "- Responsibilities phrased as achievements without numbers — ask for metrics\n"
        "- Missing patent numbers, publication venues, or URLs if applicable\n\n"
        "Ask one focused question at a time. Stop when the profile is sufficiently "
        "complete or the user indicates they have no more to add. "
        "Return the updated profile with all clarifications incorporated."
    ),
)

_update_agent: Agent[IngestDeps, ResumeProfile] = Agent(
    _MODEL,
    output_type=ResumeProfile,
    deps_type=IngestDeps,
    defer_model_check=True,
    system_prompt=(
        "You are a collaborative resume coach helping the user improve their "
        "profile.\n\n"
        "When the user tells you what they want to work on:\n"
        "- Engage with their intent — ask clarifying questions if needed\n"
        "- Proactively flag related gaps or opportunities you notice "
        "(e.g. missing achievements, vague dates, weak phrasing)\n"
        "- Offer concrete suggestions and get agreement before applying\n"
        "- Once you and the user are aligned on the changes, return the "
        "updated profile\n\n"
        "Rules:\n"
        "- Preserve all existing content that wasn't discussed\n"
        "- For new jobs: order newest-first\n"
        "- Use YYYY-MM date format; YYYY alone if month unknown\n"
        "- Leave fields as null rather than guessing\n"
        "- Never fabricate facts — only capture what the user confirms"
    ),
)


@_enhance_agent.tool
@_update_agent.tool
async def ask_clarification(ctx: RunContext[IngestDeps], question: str) -> str:
    """Ask the user a question to gather or clarify resume information."""
    return await ctx.deps.ask_user(question)


def _diff_summary(before: ResumeProfile, after: ResumeProfile) -> list[str]:
    changes: list[str] = []

    for field in ("full_name", "email", "phone", "location", "summary"):
        b, a = getattr(before, field), getattr(after, field)
        if b != a:
            changes.append(f"  ~ {field}: {b!r} → {a!r}")

    before_skills = {s.name for s in before.skills}
    after_skills = {s.name for s in after.skills}
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
        for f in ("start_date", "end_date", "location", "remote", "summary"):
            b, a = getattr(bj, f), getattr(aj, f)
            if b != a:
                changes.append(f"      ~ {f}: {b!r} → {a!r}")
        before_bullets = set(bj.responsibilities + bj.achievements)
        after_bullets = set(aj.responsibilities + aj.achievements)
        for b in sorted(after_bullets - before_bullets):
            changes.append(f"      + {b}")
        for b in sorted(before_bullets - after_bullets):
            changes.append(f"      - {b}")

    return changes


async def update(profile: ResumeProfile, deps: IngestDeps) -> ResumeProfile:
    """Interactively update an existing ResumeProfile via Q&A.

    Loops until the user types 'exit' or 'done'. Each change is diffed
    and confirmed before being applied.
    """
    current = profile
    with tracer.start_as_current_span("resume_ingest.update"):
        while True:
            request = await deps.ask_user(
                "What would you like to update? (or 'exit' to finish)"
            )
            if request.strip().lower() in {"exit", "done", "quit", "q"}:
                break

            result = await _update_agent.run(
                f"Current profile:\n{current.model_dump_json(indent=2)}\n\n"
                f"Update request: {request}",
                deps=deps,
                usage_limits=UsageLimits(request_limit=20),
            )
            updated = result.output

            diff = _diff_summary(current, updated)
            if not diff:
                await deps.ask_user(
                    "No changes detected — please try rephrasing. (press Enter)"
                )
                continue

            diff_text = "\n".join(diff)
            confirm = await deps.ask_user(
                f"Changes to apply:\n{diff_text}\n\nConfirm? (yes/no)"
            )
            if confirm.strip().lower() in {"yes", "y"}:
                current = updated
                logger.info("update.applied", changes=len(diff))

    return current


async def ingest(raw_text: str, deps: IngestDeps) -> ResumeProfile:
    """Extract and enhance a ResumeProfile from raw resume text.

    Does not save — call save_profile() on the result.
    """
    with tracer.start_as_current_span("resume_ingest.ingest") as span:
        t0 = time.perf_counter()

        extract_result = await _extract_agent.run(
            f"Resume text:\n\n{raw_text}",
            usage_limits=UsageLimits(request_limit=5),
        )
        profile = extract_result.output
        span.set_attribute("ingest.jobs_extracted", len(profile.jobs))
        logger.info(
            "ingest.extracted", jobs=len(profile.jobs), skills=len(profile.skills)
        )

        enhance_result = await _enhance_agent.run(
            f"Review and enhance this extracted profile:\n\n"
            f"{profile.model_dump_json(indent=2)}",
            deps=deps,
            usage_limits=UsageLimits(request_limit=30),
        )
        enhanced = enhance_result.output

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        usage = extract_result.usage() + enhance_result.usage()
        span.set_attribute("ingest.elapsed_ms", elapsed_ms)
        span.set_attribute("llm.input_tokens", usage.input_tokens)
        span.set_attribute("llm.output_tokens", usage.output_tokens)
        logger.info(
            "ingest.complete",
            elapsed_ms=elapsed_ms,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
        return enhanced
