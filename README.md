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

## Project Status

This is early alpha software. It is useful as a local CLI today, and the next
good open-source milestones are provider examples, safer redaction workflows,
more resume import formats, and package publishing.
