from pydantic import BaseModel, Field


class Employment(BaseModel):
    company: str
    role: str | None = None
    start_date: str | None = None  # keep as string — don't fight LLM date formats yet
    end_date: str | None = None  # None = current or unknown
    source_url: str | None = None


class CareerHistory(BaseModel):
    name: str
    employments: list[Employment]
    confidence: float = Field(ge=0, le=1)
    gaps: list[str] = []
    notes: list[str] = []  # unresolved ambiguities — will grow as failure modes emerge
