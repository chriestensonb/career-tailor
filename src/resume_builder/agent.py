import os
import time

from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

from common.telemetry import get_logger, get_tracer
from resume_data import ResumeProfile

from .models import ParsedJD, TailoredResume

tracer = get_tracer("resume_builder")
logger = get_logger("resume_builder")

_MODEL = os.environ.get("CAREER_TAILOR_MODEL", "anthropic:claude-sonnet-4-6")

_jd_agent: Agent[None, ParsedJD] = Agent(
    _MODEL,
    output_type=ParsedJD,
    defer_model_check=True,
    system_prompt=(
        "Extract a structured summary from the job description provided.\n\n"
        "Rules:\n"
        "- required_skills: explicitly stated as required/must-have\n"
        "- preferred_skills: stated as nice-to-have, preferred, or bonus\n"
        "- keywords: important domain terms and buzzwords throughout the JD\n"
        "- responsibilities: key duties the role will own\n"
        "- Leave fields null rather than guessing"
    ),
)

_tailor_agent: Agent[None, TailoredResume] = Agent(
    _MODEL,
    output_type=TailoredResume,
    defer_model_check=True,
    system_prompt=(
        "You are tailoring a resume profile to a specific job description.\n\n"
        "Rules:\n"
        "- Keep ALL jobs from the profile in newest-first order — no gaps\n"
        "- For each job, merge responsibilities and achievements into bullets:\n"
        "  * Drop bullets that are irrelevant to the JD\n"
        "  * Rewrite remaining bullets to mirror JD language and keywords"
        " where truthful\n"
        "  * Order bullets most-relevant-to-JD first\n"
        "- summary: write a compelling 2-3 sentence professional summary"
        " targeting the role\n"
        "- skills: include all relevant skills ordered by JD relevance\n"
        "- keywords_matched: list JD keywords that appear in the tailored resume\n"
        "- Never fabricate facts — only reframe what exists in the profile"
    ),
)


async def build(profile: ResumeProfile, jd_text: str) -> TailoredResume:
    """Parse a JD and tailor the profile to it. Returns a TailoredResume."""
    with tracer.start_as_current_span("resume_builder.build") as span:
        t0 = time.perf_counter()

        jd_result = await _jd_agent.run(
            f"Job description:\n\n{jd_text}",
            usage_limits=UsageLimits(request_limit=5),
        )
        parsed_jd = jd_result.output
        span.set_attribute("builder.role_title", parsed_jd.role_title)
        logger.info(
            "builder.jd_parsed", role=parsed_jd.role_title, company=parsed_jd.company
        )

        tailor_result = await _tailor_agent.run(
            f"Profile:\n{profile.model_dump_json(indent=2)}\n\n"
            f"Job description (parsed):\n{parsed_jd.model_dump_json(indent=2)}",
            usage_limits=UsageLimits(request_limit=10),
        )
        resume = tailor_result.output

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        usage = jd_result.usage() + tailor_result.usage()
        span.set_attribute("builder.elapsed_ms", elapsed_ms)
        span.set_attribute("llm.input_tokens", usage.input_tokens)
        span.set_attribute("llm.output_tokens", usage.output_tokens)
        span.set_attribute("builder.keywords_matched", len(resume.keywords_matched))
        logger.info(
            "builder.complete",
            elapsed_ms=elapsed_ms,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            keywords_matched=len(resume.keywords_matched),
        )
        return resume
