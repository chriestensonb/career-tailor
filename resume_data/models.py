from enum import StrEnum

from pydantic import BaseModel


class EmploymentType(StrEnum):
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    CONSULTING = "consulting"
    INTERNSHIP = "internship"


class SkillCategory(StrEnum):
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    TOOL = "tool"
    CLOUD = "cloud"
    DATABASE = "database"
    METHODOLOGY = "methodology"
    DOMAIN = "domain"
    SOFT = "soft"


class Proficiency(StrEnum):
    FAMILIAR = "familiar"
    PROFICIENT = "proficient"
    EXPERT = "expert"


class PatentStatus(StrEnum):
    FILED = "filed"
    PENDING = "pending"
    GRANTED = "granted"


class Job(BaseModel):
    company: str
    role: str
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    start_date: str  # "YYYY-MM" preferred; "YYYY" accepted when month unknown
    end_date: str | None = None  # None = current role
    location: str | None = None
    remote: bool | None = None
    summary: str | None = None
    responsibilities: list[str] = []  # day-to-day duties (verb phrases)
    achievements: list[str] = []  # quantified impact — kept separate for tailoring
    skills_used: list[str] = []  # tools/tech used specifically in this role
    keywords: list[str] = []  # domain terms for JD matching


class Education(BaseModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: float | None = None
    highlights: list[str] = []  # coursework, thesis, honours


class Skill(BaseModel):
    name: str
    category: SkillCategory
    proficiency: Proficiency | None = None
    years: int | None = None


class Publication(BaseModel):
    title: str
    venue: str | None = None  # journal or conference name
    date: str | None = None
    co_authors: list[str] = []
    url: str | None = None
    summary: str | None = None  # one-sentence abstract


class Patent(BaseModel):
    title: str
    patent_number: str | None = None
    status: PatentStatus = PatentStatus.GRANTED
    date: str | None = None
    co_inventors: list[str] = []
    url: str | None = None
    summary: str | None = None


class Project(BaseModel):
    name: str
    description: str
    url: str | None = None
    date: str | None = None
    skills_used: list[str] = []
    highlights: list[str] = []


class Award(BaseModel):
    title: str
    issuer: str | None = None
    date: str | None = None
    description: str | None = None


class ResumeProfile(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    website_url: str | None = None
    summary: str | None = None  # professional elevator pitch
    jobs: list[Job] = []  # newest first
    education: list[Education] = []
    skills: list[Skill] = []
    publications: list[Publication] = []
    patents: list[Patent] = []
    projects: list[Project] = []
    awards: list[Award] = []
    last_updated: str  # "YYYY-MM-DD"
    notes: list[str] = []  # unresolved gaps from Q&A
