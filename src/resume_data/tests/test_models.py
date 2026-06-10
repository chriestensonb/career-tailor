import pytest

from resume_data import (
    Education,
    EmploymentType,
    Job,
    Patent,
    PatentStatus,
    Proficiency,
    ResumeProfile,
    Skill,
    SkillCategory,
    load_profile,
    save_profile,
)


@pytest.fixture
def minimal_profile() -> ResumeProfile:
    return ResumeProfile(full_name="Jane Doe", last_updated="2026-04-07")


@pytest.fixture
def full_profile() -> ResumeProfile:
    return ResumeProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        location="San Francisco, CA",
        summary="Senior engineer with 10 years experience.",
        last_updated="2026-04-07",
        jobs=[
            Job(
                company="Acme Corp",
                role="Senior Engineer",
                employment_type=EmploymentType.FULL_TIME,
                start_date="2020-01",
                responsibilities=["Led backend team of 5"],
                achievements=["Reduced API latency 40%"],
                skills_used=["Python", "PostgreSQL"],
                keywords=["distributed systems"],
            )
        ],
        education=[
            Education(
                institution="MIT",
                degree="BS",
                field="Computer Science",
                end_date="2016-05",
            )
        ],
        skills=[
            Skill(
                name="Python",
                category=SkillCategory.PROGRAMMING_LANGUAGE,
                proficiency=Proficiency.EXPERT,
                years=10,
            )
        ],
        patents=[
            Patent(
                title="Widget Optimizer",
                patent_number="US1234567",
                status=PatentStatus.GRANTED,
                date="2022-03",
            )
        ],
        notes=["Exact dates for early career roles unknown"],
    )


def test_minimal_profile_valid(minimal_profile: ResumeProfile) -> None:
    assert minimal_profile.full_name == "Jane Doe"
    assert minimal_profile.jobs == []
    assert minimal_profile.skills == []


def test_full_profile_valid(full_profile: ResumeProfile) -> None:
    assert full_profile.jobs[0].company == "Acme Corp"
    assert full_profile.jobs[0].achievements == ["Reduced API latency 40%"]
    assert full_profile.patents[0].patent_number == "US1234567"


def test_job_current_role_has_no_end_date() -> None:
    job = Job(company="Acme", role="Engineer", start_date="2023-06")
    assert job.end_date is None


def test_json_round_trip(full_profile: ResumeProfile) -> None:
    restored = ResumeProfile.model_validate_json(full_profile.model_dump_json())
    assert restored == full_profile


def test_missing_full_name_raises() -> None:
    with pytest.raises(Exception):
        ResumeProfile(last_updated="2026-04-07")  # type: ignore[call-arg]


def test_store_round_trip(full_profile: ResumeProfile, tmp_path) -> None:
    path = tmp_path / "profile.json"
    save_profile(full_profile, path)
    assert load_profile(path) == full_profile


def test_save_creates_parent_dirs(minimal_profile: ResumeProfile, tmp_path) -> None:
    path = tmp_path / "nested" / "dir" / "profile.json"
    save_profile(minimal_profile, path)
    assert path.exists()


def test_load_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_profile(tmp_path / "nonexistent.json")
