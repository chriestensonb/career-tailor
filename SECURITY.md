# Security Policy

## Reporting Security Issues

Please report security issues privately by opening a GitHub security advisory or
emailing the maintainer listed on the GitHub profile.

Do not include live API keys, private resumes, or other personal data in public
issues.

## Local Secrets

Career Tailor reads provider credentials from environment variables or a local
`.env` file. `.env`, `data/`, and `tailored/` are ignored by Git because they may
contain API keys or personal information.

If you accidentally commit a secret, revoke and rotate it immediately. Removing
it from a later commit is not enough once it has entered Git history.
