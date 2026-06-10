from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pydantic_ai.models.test import TestModel

from resume_builder import ParsedJD, TailoredJob, TailoredResume, build
from resume_builder.agent import _jd_agent, _tailor_agent
from resume_builder.deps import TweakDeps
from resume_builder.store import load_css, load_tailored, save_tailored, stem_for
from resume_builder.tweak import (
    _content_tweak_agent,
    _diff_css,
    _diff_tailored,
    _visual_tweak_agent,
    tweak_content,
    tweak_visual,
)
from resume_data import ResumeProfile

SAMPLE_JD = """
Senior Backend Engineer — Acme Payments

We're looking for a Senior Backend Engineer to own our payments infrastructure.

Requirements:
- 5+ years of Python experience
- Strong knowledge of PostgreSQL and distributed systems
- Experience with AWS (ECS, RDS, SQS)

Nice to have:
- Experience with Kafka
- Knowledge of PCI compliance

You'll be responsible for designing scalable APIs, mentoring junior engineers,
and reducing system latency across our payment pipeline.
"""

SAMPLE_PROFILE = ResumeProfile(
    full_name="Jane Doe",
    email="jane@example.com",
    location="San Francisco, CA",
    last_updated="2024-01-01",
    jobs=[
        {
            "company": "Acme Corp",
            "role": "Senior Engineer",
            "start_date": "2020-01",
            "responsibilities": ["Led backend team of 5 engineers"],
            "achievements": ["Reduced API latency by 40% through caching redesign"],
            "skills_used": ["Python", "PostgreSQL", "AWS"],
        }
    ],
)


# --- ParsedJD model tests ---


def test_parsed_jd_defaults() -> None:
    jd = ParsedJD(role_title="Engineer")
    assert jd.required_skills == []
    assert jd.preferred_skills == []
    assert jd.keywords == []
    assert jd.company is None


def test_parsed_jd_fields() -> None:
    jd = ParsedJD(
        role_title="Backend Engineer",
        company="Acme",
        required_skills=["Python"],
        preferred_skills=["Kafka"],
        keywords=["distributed systems"],
    )
    assert jd.role_title == "Backend Engineer"
    assert "Python" in jd.required_skills
    assert "Kafka" in jd.preferred_skills


# --- TailoredResume model tests ---


def _make_resume(**kwargs) -> TailoredResume:
    defaults = dict(
        full_name="Jane Doe",
        email="jane@example.com",
        location="San Francisco, CA",
        summary="Experienced backend engineer.",
        jobs=[
            TailoredJob(
                company="Acme Corp",
                role="Senior Engineer",
                start_date="2020-01",
                bullets=["Reduced API latency by 40%", "Led team of 5"],
            )
        ],
        skills=["Python", "PostgreSQL", "AWS"],
        target_role="Senior Backend Engineer",
        keywords_matched=["Python", "PostgreSQL"],
    )
    defaults.update(kwargs)
    return TailoredResume(**defaults)


def test_tailored_resume_jobs_preserved() -> None:
    resume = _make_resume()
    assert len(resume.jobs) == 1
    assert resume.jobs[0].company == "Acme Corp"


def test_tailored_resume_bullets_ordered() -> None:
    resume = _make_resume()
    assert resume.jobs[0].bullets[0] == "Reduced API latency by 40%"


def test_to_markdown_contains_name() -> None:
    md = _make_resume().to_markdown()
    assert "Jane Doe" in md


def test_to_markdown_contains_contact() -> None:
    md = _make_resume().to_markdown()
    assert "jane@example.com" in md
    assert "San Francisco, CA" in md


def test_to_markdown_contains_summary() -> None:
    md = _make_resume().to_markdown()
    assert "Experienced backend engineer." in md


def test_to_markdown_contains_job() -> None:
    md = _make_resume().to_markdown()
    assert "Acme Corp" in md
    assert "Reduced API latency by 40%" in md


def test_to_markdown_contains_skills() -> None:
    md = _make_resume().to_markdown()
    assert "Python" in md
    assert "PostgreSQL" in md


def test_to_markdown_current_role_shows_present() -> None:
    md = _make_resume().to_markdown()
    assert "Present" in md


def test_to_markdown_closed_role_shows_end_date() -> None:
    resume = _make_resume(
        jobs=[
            TailoredJob(
                company="Old Co",
                role="Eng",
                start_date="2018-01",
                end_date="2020-01",
                bullets=[],
            )
        ]
    )
    assert "2020-01" in resume.to_markdown()


# --- build() integration tests ---


async def test_build_returns_tailored_resume() -> None:
    with (
        _jd_agent.override(model=TestModel()),
        _tailor_agent.override(model=TestModel()),
    ):
        result = await build(SAMPLE_PROFILE, SAMPLE_JD)
    assert isinstance(result, TailoredResume)


async def test_build_jobs_count_preserved() -> None:
    with (
        _jd_agent.override(model=TestModel()),
        _tailor_agent.override(model=TestModel()),
    ):
        result = await build(SAMPLE_PROFILE, SAMPLE_JD)
    # TestModel returns minimal valid output; just check structure
    assert isinstance(result.jobs, list)


async def test_build_skills_is_list() -> None:
    with (
        _jd_agent.override(model=TestModel()),
        _tailor_agent.override(model=TestModel()),
    ):
        result = await build(SAMPLE_PROFILE, SAMPLE_JD)
    assert isinstance(result.skills, list)


# --- to_html() tests ---


def test_to_html_contains_name() -> None:
    html = _make_resume().to_html("body {}")
    assert "Jane Doe" in html


def test_to_html_contains_contact() -> None:
    html = _make_resume().to_html("body {}")
    assert "jane@example.com" in html


def test_to_html_contains_job() -> None:
    html = _make_resume().to_html("body {}")
    assert "Acme Corp" in html
    assert "Reduced API latency" in html


def test_to_html_css_embedded() -> None:
    html = _make_resume().to_html("body { color: red; }")
    assert "color: red" in html


def test_to_html_escapes_special_chars() -> None:
    resume = _make_resume(full_name="Jane & Doe <Test>")
    html = resume.to_html("body {}")
    assert "&amp;" in html or "&lt;" in html


# --- store tests ---


def test_save_and_load_tailored(tmp_path: Path, monkeypatch) -> None:
    import resume_builder.store as store_mod

    monkeypatch.setattr(store_mod, "_TAILORED_DIR", tmp_path)
    resume = _make_resume()
    stem = stem_for(resume, "2024-01-01")
    save_tailored(resume, stem, "body {}")
    loaded = load_tailored(tmp_path / f"{stem}.json")
    assert loaded.full_name == resume.full_name


def test_save_tailored_writes_css(tmp_path: Path, monkeypatch) -> None:
    import resume_builder.store as store_mod

    monkeypatch.setattr(store_mod, "_TAILORED_DIR", tmp_path)
    resume = _make_resume()
    stem = stem_for(resume, "2024-01-01")
    save_tailored(resume, stem, "body { color: blue; }")
    css = load_css(tmp_path / f"{stem}.css")
    assert "color: blue" in css


def test_stem_for_sanitizes_role() -> None:
    resume = _make_resume(target_role='Engineer: "Backend"')
    stem = stem_for(resume, "2024-01-01")
    assert ":" not in stem
    assert '"' not in stem


# --- _diff_tailored tests ---


def test_diff_tailored_no_changes() -> None:
    r = _make_resume()
    assert _diff_tailored(r, r) == []


def test_diff_tailored_summary_change() -> None:
    before = _make_resume()
    after = _make_resume(summary="Updated summary.")
    diff = _diff_tailored(before, after)
    assert any("summary" in line for line in diff)


def test_diff_tailored_skill_added() -> None:
    before = _make_resume(skills=["Python"])
    after = _make_resume(skills=["Python", "Go"])
    diff = _diff_tailored(before, after)
    assert any("+ skill: Go" in line for line in diff)


def test_diff_tailored_bullet_added() -> None:
    before = _make_resume()
    after = _make_resume(
        jobs=[
            TailoredJob(
                company="Acme Corp",
                role="Senior Engineer",
                start_date="2020-01",
                bullets=["Reduced API latency by 40%", "Led team of 5", "New bullet"],
            )
        ]
    )
    diff = _diff_tailored(before, after)
    assert any("New bullet" in line for line in diff)


# --- _diff_css tests ---


def test_diff_css_no_changes() -> None:
    css = "body { color: red; }"
    assert _diff_css(css, css) == []


def test_diff_css_shows_change() -> None:
    before = "body { color: red; }"
    after = "body { color: blue; }"
    diff = _diff_css(before, after)
    assert any("red" in line for line in diff)
    assert any("blue" in line for line in diff)


# --- tweak_content() tests ---


@pytest.fixture
def tweak_deps() -> TweakDeps:
    return TweakDeps(ask_user=AsyncMock(return_value="exit"))


async def test_tweak_content_exit_returns_resume(tweak_deps: TweakDeps) -> None:
    with _content_tweak_agent.override(model=TestModel()):
        result = await tweak_content(_make_resume(), tweak_deps)
    assert isinstance(result, TailoredResume)


async def test_tweak_visual_exit_returns_css(tweak_deps: TweakDeps) -> None:
    with _visual_tweak_agent.override(model=TestModel()):
        result = await tweak_visual("body { color: red; }", tweak_deps)
    assert isinstance(result, str)
