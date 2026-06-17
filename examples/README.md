# Examples

This directory contains fake sample inputs for trying Career Tailor without using
personal resume data.

```bash
career-tailor tailor examples/sample_job_description.md \
  --profile examples/sample_profile.json \
  --output-dir tailored-demo \
  --no-pdf
```

The generated files in `tailored-demo/` should be treated like ordinary resume
outputs and kept out of Git.

The same fake-data command works with Anthropic or OpenAI. Configure one model
provider in `.env` as shown in the root README, then rerun the command above.
The resume and job-description text are sent to whichever provider you configure.
