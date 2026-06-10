# Roadmap

Career Tailor is early alpha software. The near-term goal is to make it a
trustworthy, local-first resume tailoring workflow that job seekers and coding
agents can use without leaking private documents into the repository.

## Near Term

- Add more provider examples for OpenAI and Anthropic model strings.
- Add a privacy check that scans generated outputs for common accidental leaks.
- Add a deterministic example workflow with fake profile and job-description data.
- Improve CLI error messages for missing provider keys, missing profile files, and
  PDF rendering failures.
- Add regression tests for resume grounding so generated claims stay tied to the
  source profile.

## Community Milestones

- Label beginner-friendly issues for docs, examples, and provider setup.
- Add contribution notes for testing resume workflows without real personal data.
- Publish small, fake sample datasets that downstream agents can use for demos.
- Document agent-friendly usage patterns for Codex, Claude Code, Cline, and other
  coding assistants.

## Longer Term

- Support additional resume import formats.
- Add evaluation fixtures for job-description parsing and resume tailoring quality.
- Add optional redaction workflows before sending text to a model provider.
- Explore maintainer automation for issue triage, PR review, release notes, and
  security checks.
