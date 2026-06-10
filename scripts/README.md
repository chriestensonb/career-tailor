# Scripts

These scripts are manual development helpers and smoke tests. They are not part
of the installed `career-tailor` command.

Run them from the repository root with `uv run`, for example:

```bash
uv run python scripts/try_resume_build.py
```

Most scripts read local `.env`, `data/`, or `tailored/` files, so keep using fake
or throwaway data when testing workflows that should be safe to share publicly.
