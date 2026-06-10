from html import escape

from pydantic import BaseModel

from resume_data import Education


class ParsedJD(BaseModel):
    role_title: str
    company: str | None = None
    seniority: str | None = None
    company_context: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    keywords: list[str] = []
    responsibilities: list[str] = []


class TailoredJob(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str | None = None  # None = current role
    location: str | None = None
    remote: bool | None = None
    # selected, reordered, rewritten for JD; most relevant first
    bullets: list[str] = []


class TailoredResume(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str  # AI-generated, targeted to the role
    jobs: list[TailoredJob]  # all jobs, newest-first, no gaps
    skills: list[str]  # ordered by JD relevance
    education: list[Education] = []
    target_role: str
    target_company: str | None = None
    keywords_matched: list[str] = []

    def to_markdown(self) -> str:
        lines: list[str] = []

        # Header
        lines.append(f"# {self.full_name}")
        contact_parts = [p for p in [self.email, self.phone, self.location] if p]
        if contact_parts:
            lines.append(" | ".join(contact_parts))
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append(self.summary)
        lines.append("")

        # Experience
        lines.append("## Experience")
        for job in self.jobs:
            end = job.end_date or "Present"
            remote_tag = " (Remote)" if job.remote else ""
            header = f"### {job.role} — {job.company}"
            date_loc = f"*{job.start_date} – {end}"
            if job.location:
                date_loc += f" | {job.location}{remote_tag}"
            date_loc += "*"
            lines.append(header)
            lines.append(date_loc)
            for bullet in job.bullets:
                lines.append(f"- {bullet}")
            lines.append("")

        # Skills
        if self.skills:
            lines.append("## Skills")
            lines.append(", ".join(self.skills))
            lines.append("")

        # Education
        if self.education:
            lines.append("## Education")
            for edu in self.education:
                degree_field = " ".join(filter(None, [edu.degree, edu.field]))
                heading = (
                    f"### {degree_field} — {edu.institution}"
                    if degree_field
                    else f"### {edu.institution}"
                )
                lines.append(heading)
                dates = " – ".join(filter(None, [edu.start_date, edu.end_date]))
                if dates:
                    lines.append(f"*{dates}*")
                for h in edu.highlights:
                    lines.append(f"- {h}")
                lines.append("")

        return "\n".join(lines).rstrip()

    def to_html(self, css: str) -> str:
        def e(s: str | None) -> str:
            return escape(s or "")

        parts: list[str] = []
        parts.append("<!DOCTYPE html>")
        parts.append('<html lang="en"><head><meta charset="utf-8">')
        parts.append(f"<style>\n{css}\n</style></head><body>")

        # Header
        parts.append("<header>")
        parts.append(f"<h1>{e(self.full_name)}</h1>")
        contact = " | ".join(e(p) for p in [self.email, self.phone, self.location] if p)
        if contact:
            parts.append(f'<p class="contact">{contact}</p>')
        parts.append("</header>")

        # Summary
        parts.append('<section class="section">')
        parts.append("<h2>Summary</h2>")
        parts.append(f'<p class="summary">{e(self.summary)}</p>')
        parts.append("</section>")

        # Experience
        parts.append('<section class="section">')
        parts.append("<h2>Experience</h2>")
        for job in self.jobs:
            end = e(job.end_date) if job.end_date else "Present"
            remote = " (Remote)" if job.remote else ""
            parts.append('<div class="job">')
            parts.append('<div class="job-header">')
            parts.append(f'<span class="job-title">{e(job.role)}</span>')
            parts.append(f'<span class="job-company">{e(job.company)}</span>')
            parts.append("</div>")
            meta = f"{e(job.start_date)} – {end}"
            if job.location:
                meta += f" | {e(job.location)}{remote}"
            parts.append(f'<p class="job-meta">{meta}</p>')
            if job.bullets:
                parts.append("<ul>")
                for b in job.bullets:
                    parts.append(f"<li>{e(b)}</li>")
                parts.append("</ul>")
            parts.append("</div>")
        parts.append("</section>")

        # Skills
        if self.skills:
            parts.append('<section class="section">')
            parts.append("<h2>Skills</h2>")
            skills_str = ", ".join(e(s) for s in self.skills)
            parts.append(f'<p class="skills">{skills_str}</p>')
            parts.append("</section>")

        # Education
        if self.education:
            parts.append('<section class="section">')
            parts.append("<h2>Education</h2>")
            for edu in self.education:
                degree_field = " ".join(filter(None, [edu.degree, edu.field]))
                label = (
                    f"{e(degree_field)} — {e(edu.institution)}"
                    if degree_field
                    else e(edu.institution)
                )
                dates = " – ".join(filter(None, [edu.start_date, edu.end_date]))
                parts.append('<div class="edu">')
                parts.append('<div class="edu-header">')
                parts.append(f'<span class="edu-degree">{label}</span>')
                if dates:
                    parts.append(f'<span class="edu-dates">{e(dates)}</span>')
                parts.append("</div>")
                if edu.highlights:
                    parts.append('<ul class="edu-highlights">')
                    for h in edu.highlights:
                        parts.append(f"<li>{e(h)}</li>")
                    parts.append("</ul>")
                parts.append("</div>")
            parts.append("</section>")

        parts.append("</body></html>")
        return "\n".join(parts)
