from pathlib import Path

import pytest

from career_tailor import cli
from resume_builder.models import TailoredJob, TailoredResume
from resume_data.models import ResumeProfile


def _profile(path: Path) -> Path:
    profile = ResumeProfile(
        full_name="Jane Doe",
        summary="Python developer.",
        last_updated="2026-06-11",
    )
    path.write_text(profile.model_dump_json(indent=2))
    return path


def _resume() -> TailoredResume:
    return TailoredResume(
        full_name="Jane Doe",
        summary="Python developer focused on reliable tools.",
        jobs=[
            TailoredJob(
                company="Acme",
                role="Engineer",
                start_date="2024-01",
                bullets=["Built reliable Python tools."],
            )
        ],
        skills=["Python"],
        target_role="Software Engineer",
    )


def _configured_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAREER_TAILOR_MODEL", "anthropic:test-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


@pytest.mark.asyncio
async def test_missing_provider_key_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CAREER_TAILOR_MODEL", "anthropic:test-model")

    code = await cli._run(["--env-file", "does-not-exist.env", "ingest"])

    assert code == 2
    assert "Missing ANTHROPIC_API_KEY" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_invalid_model_provider_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CAREER_TAILOR_MODEL", "local:test-model")

    code = await cli._run(["--env-file", "does-not-exist.env", "ingest"])

    assert code == 2
    err = capsys.readouterr().err
    assert "Unsupported model provider 'local'" in err
    assert "Known providers" in err


@pytest.mark.asyncio
async def test_missing_profile_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configured_env(monkeypatch)
    job = tmp_path / "job.md"
    job.write_text("Build reliable Python tools.")

    code = await cli._run(
        [
            "--env-file",
            "does-not-exist.env",
            "tailor",
            str(job),
            "--profile",
            str(tmp_path / "missing-profile.json"),
            "--no-pdf",
        ]
    )

    assert code == 2
    err = capsys.readouterr().err
    assert "Profile JSON not found" in err
    assert "career-tailor ingest" in err


@pytest.mark.asyncio
async def test_missing_job_description_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configured_env(monkeypatch)
    profile = _profile(tmp_path / "profile.json")

    code = await cli._run(
        [
            "--env-file",
            "does-not-exist.env",
            "tailor",
            str(tmp_path / "missing-job.md"),
            "--profile",
            str(profile),
            "--no-pdf",
        ]
    )

    assert code == 2
    err = capsys.readouterr().err
    assert "Input file not found" in err
    assert "omit it to paste text via stdin" in err


@pytest.mark.asyncio
async def test_pdf_browser_error_mentions_playwright_install(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _configured_env(monkeypatch)
    profile = _profile(tmp_path / "profile.json")
    job = tmp_path / "job.md"
    job.write_text("Build reliable Python tools.")

    async def fake_build(*args, **kwargs):  # noqa: ANN002, ANN003
        return _resume()

    async def fake_to_pdf(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("Executable doesn't exist at /tmp/chromium")

    monkeypatch.setattr(cli, "build", fake_build)
    monkeypatch.setattr(cli, "to_pdf", fake_to_pdf)

    code = await cli._run(
        [
            "--env-file",
            "does-not-exist.env",
            "tailor",
            str(job),
            "--profile",
            str(profile),
            "--output-dir",
            str(tmp_path / "tailored"),
        ]
    )

    assert code == 2
    err = capsys.readouterr().err
    assert "uv run playwright install chromium" in err
    assert "--no-pdf" in err


@pytest.mark.asyncio
async def test_scan_does_not_require_provider_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    output = tmp_path / "resume.md"
    output.write_text("Clean generated output.")

    code = await cli._run(
        ["--env-file", "does-not-exist.env", "scan", str(tmp_path)]
    )

    assert code == 0
    assert "Privacy scan passed: 1 file(s) scanned." in capsys.readouterr().out


@pytest.mark.asyncio
async def test_scan_returns_one_when_findings_exist(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "resume.md"
    output.write_text("Contact me at jane@example.com")

    code = await cli._run(
        ["--env-file", "does-not-exist.env", "scan", str(tmp_path)]
    )

    assert code == 1
    out = capsys.readouterr().out
    assert "Privacy scan found 1 possible issue" in out
    assert "email" in out


@pytest.mark.asyncio
async def test_scan_missing_path_has_actionable_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = await cli._run(
        ["--env-file", "does-not-exist.env", "scan", str(tmp_path / "missing")]
    )

    assert code == 2
    assert "Scan path not found" in capsys.readouterr().err
