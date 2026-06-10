from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ResultType(StrEnum):
    WEB = "web"
    NEWS = "news"
    DISCUSSIONS = "discussions"
    FAQ = "faq"
    INFOBOX = "infobox"
    VIDEOS = "videos"
    LOCATIONS = "locations"
    # SUMMARIZER = "summarizer"  # Brave Pro tier — uncomment when upgrading


_RESULT_TYPES = ", ".join(ResultType)


class SearchParams(BaseModel):
    query: str = Field(description="Search query")
    count: int = Field(default=5, ge=1, le=20, description="Number of results (max 20)")
    offset: int = Field(default=0, ge=0, le=9, description="Pagination offset")
    country: str | None = Field(default=None, description="Country code e.g. 'US'")
    search_lang: str | None = Field(default=None, description="Language code e.g. 'en'")
    safesearch: Literal["off", "moderate", "strict"] = Field(
        default="moderate", description="Content filter level"
    )
    freshness: str | None = Field(
        default=None,
        description="pd=day pw=week pm=month py=year or YYYY-MM-DDtoYYYY-MM-DD",
    )
    extra_snippets: bool = Field(
        default=False, description="Include extra text snippets per web result"
    )
    result_filter: list[ResultType] | None = Field(
        default=None,
        description=f"Sections to return: {_RESULT_TYPES}. Defaults to Brave's choice.",
    )


class WebResult(BaseModel):
    title: str
    url: str
    description: str | None = None
    age: str | None = None
    extra_snippets: list[str] | None = None


class NewsResult(BaseModel):
    title: str
    url: str
    description: str | None = None
    age: str | None = None
    source: str | None = None


class DiscussionResult(BaseModel):
    title: str
    url: str
    description: str | None = None
    forum_name: str | None = None
    num_answers: int | None = None


class FaqResult(BaseModel):
    question: str
    answer: str | None = None
    title: str | None = None
    url: str | None = None


class Infobox(BaseModel):
    title: str | None = None
    description: str | None = None
    long_desc: str | None = None
    url: str | None = None
    website_url: str | None = None


class VideoResult(BaseModel):
    title: str
    url: str
    description: str | None = None
    age: str | None = None


class LocationResult(BaseModel):
    title: str
    url: str | None = None
    description: str | None = None
    address: dict | None = None  # schema.org address object
    phone: str | None = None
    rating: float | None = None


class SearchResponse(BaseModel):
    query: str
    web: list[WebResult] = []
    news: list[NewsResult] | None = None
    discussions: list[DiscussionResult] | None = None
    faq: list[FaqResult] | None = None
    infobox: Infobox | None = None
    videos: list[VideoResult] | None = None
    locations: list[LocationResult] | None = None
