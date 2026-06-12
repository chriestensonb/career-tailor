from pathlib import Path

from career_tailor.privacy import format_findings, scan_paths


def test_scan_clean_directory_passes(tmp_path: Path) -> None:
    output = tmp_path / "resume.md"
    output.write_text("# Jane Doe\n\nBuilt reliable Python tools.\n")

    result = scan_paths([tmp_path])

    assert result.files_scanned == 1
    assert result.findings == []


def test_scan_flags_common_privacy_leaks(tmp_path: Path) -> None:
    output = tmp_path / "resume.json"
    output.write_text(
        "\n".join(
            [
                '{"email": "jane@example.com",',
                '"phone": "303-555-1212",',
                '"debug_path": "/Users/jane/private/resume.md",',
                '"token": "OPENAI_API_KEY=sk-testsecret123456789012345"}',
            ]
        )
    )

    result = scan_paths([output])
    kinds = {finding.kind for finding in result.findings}

    assert {"email", "phone", "absolute-path", "openai-key"} <= kinds
    formatted = "\n".join(format_findings(result.findings))
    assert "jane@example.com" in formatted
    assert "resume.json:1: email" in formatted


def test_scan_skips_unsupported_files(tmp_path: Path) -> None:
    (tmp_path / "resume.md").write_text("Clean generated output.")
    binary = tmp_path / "resume.pdf"
    binary.write_bytes(b"%PDF")

    result = scan_paths([tmp_path])

    assert result.files_scanned == 1
    assert result.skipped_paths == [binary]
