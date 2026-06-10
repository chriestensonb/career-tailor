# Career Tailor

Career Tailor is a local-first command line tool that turns a master resume into
job-specific drafts. It extracts a structured profile from your resume, compares
that profile against a job description, and generates tailored Markdown, JSON,
CSS, and optionally PDF output.

The goal is not to fabricate experience. The agent is prompted to preserve the
facts in your profile and reframe them in the language of the job description.

## Why

Many applicant tracking systems and recruiter workflows reward resumes that use
the same language as the job posting. Career Tailor helps job seekers build
truthful, role-specific versions of a resume without manually rewriting the same
material for every application.

Career Tailor is also designed to be friendly to coding agents. A user or agent
can keep a private structured profile locally, pass in a job description, and
generate reviewable Markdown/JSON output before deciding what to export or send.

## Install

```bash
uvx career-tailor --help
```

For local development:

```bash
git clone https://github.com/chriestensonb/career-tailor.git
cd career-tailor
uv sync
cp .env.example .env
```

You can also run the latest unreleased GitHub version directly:

```bash
uvx --from git+https://github.com/chriestensonb/career-tailor career-tailor --help
```

Set your model provider key in `.env`. By default the project uses a Pydantic AI
Anthropic model string, but OpenAI model strings are supported too:

```bash
CAREER_TAILOR_MODEL=anthropic:claude-sonnet-4-6
ANTHROPIC_API_KEY=...
```

Or:

```bash
CAREER_TAILOR_MODEL=openai:<model-name>
OPENAI_API_KEY=...
```

## Usage

Create a structured profile from an existing resume:

```bash
career-tailor ingest ./my-resume.md
```

Generate a tailored resume from a job description:

```bash
career-tailor tailor ./job-description.md
```

Skip PDF rendering when you only want Markdown and JSON:

```bash
career-tailor tailor ./job-description.md --no-pdf
```

The default profile path is `data/profile.json`. Generated outputs go to
`tailored/`. Both directories are ignored by Git because they commonly contain
personal information.

## Example

The `examples/` directory contains fake sample data for trying the CLI without
using a real resume:

```bash
career-tailor tailor examples/sample_job_description.md \
  --profile examples/sample_profile.json \
  --output-dir tailored-demo \
  --no-pdf
```

The example is intentionally fictional. Do not commit generated outputs from real
resume data.

## Data And Privacy

Career Tailor runs locally, but it sends resume and job description text to the
model provider you configure. Do not use it with sensitive data unless you are
comfortable with that provider's data handling terms.

The repository ignores:

- `.env` and other local env files
- `data/`, which stores extracted profile data
- `tailored/`, which stores generated resumes
- local caches and virtual environments

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check .
```

If PDF rendering fails the first time, install Playwright's Chromium browser:

```bash
uv run playwright install chromium
```

## Project Layout

- `src/` contains the importable Python packages and CLI entry point.
- `examples/` contains fictional sample data for demos and tests.
- `scripts/` contains local development helpers and manual smoke-test scripts.
- `.github/workflows/` contains CI and PyPI publishing workflows.
- `data/` and `tailored/` are local-only output folders ignored by Git.

## Project Status

This is early alpha software. It is useful as a local CLI today, and the next
good open-source milestones are provider examples, safer redaction workflows,
more resume import formats, and better agent-facing workflows. See
`ROADMAP.md` for the current plan.

## API Credits And Maintainer Automation

API credits would directly support core open-source work for this project:

- regression tests that compare generated resumes against source profiles
- privacy and redaction checks before model-provider calls
- example workflows across OpenAI, Anthropic, and local development setups
- issue triage, PR review, release-note drafting, and package-publishing checks
- agent-friendly documentation so coding assistants can discover and use the CLI

The goal is to make resume tailoring safer, more transparent, and easier for
job seekers to run locally while keeping private career data out of Git history.
