# Contributing

Contributions are welcome. This project is intentionally small and practical:
improvements should help job seekers produce truthful, role-specific resumes
with less repetitive editing.

Good first areas:

- provider setup examples
- import support for additional resume formats
- redaction and privacy checks
- better CLI ergonomics
- tests around resume generation edge cases

Before opening a pull request:

```bash
uv run pytest
uv run ruff check .
```

Please do not add real resumes, generated personal artifacts, or API keys to
fixtures.
