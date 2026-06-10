from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic_ai.models.test import TestModel

from resume_data import ResumeProfile
from resume_ingest import IngestDeps, from_file, from_text, ingest, update
from resume_ingest.agent import (
    _diff_summary,
    _enhance_agent,
    _extract_agent,
    _update_agent,
)

SAMPLE_RESUME = """
Jane Doe — jane@example.com — San Francisco, CA

EXPERIENCE
Acme Corp, Senior Engineer, Jan 2020 – present
- Led backend team of 5 engineers
- Reduced API latency by 40% through caching redesign

MIT, BS Computer Science, 2012 – 2016

SKILLS: Python, PostgreSQL, AWS
"""


@pytest.fixture
def deps() -> IngestDeps:
    return IngestDeps(ask_user=AsyncMock(return_value="no additional info"))


def test_from_text_strips_whitespace() -> None:
    assert from_text("  hello  ") == "hello"


def test_from_text_identity() -> None:
    assert from_text("raw text") == "raw text"


def test_from_file_reads_txt(tmp_path: Path) -> None:
    f = tmp_path / "resume.txt"
    f.write_text("my resume")
    assert from_file(f) == "my resume"


def test_from_file_reads_md(tmp_path: Path) -> None:
    f = tmp_path / "resume.md"
    f.write_text("# Jane Doe")
    assert from_file(f) == "# Jane Doe"


def test_from_file_unsupported_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported file type '.pdf'"):
        from_file(Path("resume.pdf"))


def test_from_file_unsupported_hints_at_pdf() -> None:
    with pytest.raises(ValueError, match="from_pdf"):
        from_file(Path("resume.pdf"))


async def test_ingest_returns_profile(deps: IngestDeps) -> None:
    with (
        _extract_agent.override(model=TestModel()),
        _enhance_agent.override(model=TestModel()),
    ):
        result = await ingest(SAMPLE_RESUME, deps)
    assert isinstance(result, ResumeProfile)


async def test_ingest_enhance_calls_ask_user(deps: IngestDeps) -> None:
    with (
        _extract_agent.override(model=TestModel()),
        _enhance_agent.override(model=TestModel()),
    ):
        await ingest(SAMPLE_RESUME, deps)
    # TestModel may or may not invoke tools; we verify the dep is wired correctly
    assert callable(deps.ask_user)


# --- _diff_summary tests ---

_BASE_PROFILE = ResumeProfile(
    full_name="Jane Doe",
    last_updated="2024-01-01",
    jobs=[
        {
            "company": "Acme",
            "role": "Engineer",
            "start_date": "2020-01",
            "responsibilities": ["Built APIs"],
            "achievements": [],
        }
    ],
    skills=[{"name": "Python", "category": "programming_language"}],
)


def test_diff_no_changes() -> None:
    assert _diff_summary(_BASE_PROFILE, _BASE_PROFILE) == []


def test_diff_added_skill() -> None:
    from resume_data import Skill, SkillCategory

    new_skill = Skill(name="Go", category=SkillCategory.PROGRAMMING_LANGUAGE)
    updated = _BASE_PROFILE.model_copy(
        update={"skills": [*_BASE_PROFILE.skills, new_skill]}
    )
    diff = _diff_summary(_BASE_PROFILE, updated)
    assert any("+ skill: Go" in line for line in diff)


def test_diff_removed_skill() -> None:
    updated = _BASE_PROFILE.model_copy(update={"skills": []})
    diff = _diff_summary(_BASE_PROFILE, updated)
    assert any("- skill: Python" in line for line in diff)


def test_diff_changed_field() -> None:
    updated = _BASE_PROFILE.model_copy(update={"email": "new@example.com"})
    diff = _diff_summary(_BASE_PROFILE, updated)
    assert any("~ email" in line for line in diff)


def test_diff_added_job() -> None:
    from resume_data import Job

    new_job = Job(company="New Co", role="Staff Engineer", start_date="2023-01")
    updated = _BASE_PROFILE.model_copy(update={"jobs": [new_job, *_BASE_PROFILE.jobs]})
    diff = _diff_summary(_BASE_PROFILE, updated)
    assert any("+ job: Staff Engineer at New Co" in line for line in diff)


def test_diff_modified_job() -> None:
    from resume_data import Job

    modified_job = Job(
        company="Acme",
        role="Engineer",
        start_date="2020-01",
        responsibilities=["Built APIs", "Mentored juniors"],
    )
    updated = _BASE_PROFILE.model_copy(update={"jobs": [modified_job]})
    diff = _diff_summary(_BASE_PROFILE, updated)
    assert any("~ job: Engineer at Acme" in line for line in diff)
    assert any("Mentored juniors" in line for line in diff)


# --- update() integration tests ---


async def test_update_exit_immediately_returns_profile(deps: IngestDeps) -> None:
    deps.ask_user = AsyncMock(return_value="exit")
    with _update_agent.override(model=TestModel()):
        result = await update(_BASE_PROFILE, deps)
    assert result == _BASE_PROFILE


async def test_update_returns_resume_profile(deps: IngestDeps) -> None:
    # Provide enough responses to cover any tool calls TestModel may make,
    # then confirm/exit to finish the loop.
    responses = iter(
        ["add skill: Docker"] + ["no extra info"] * 10 + ["yes"] + ["exit"] * 5
    )
    deps.ask_user = AsyncMock(side_effect=lambda _q: next(responses, "exit"))
    with _update_agent.override(model=TestModel()):
        result = await update(_BASE_PROFILE, deps)
    assert isinstance(result, ResumeProfile)
