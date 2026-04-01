from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ResearchRequest(BaseModel):
    player_name: str
    year: Optional[int] = None
    variation: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    max_results: int = 25


class ResearchResult(BaseModel):
    title: str
    price: float
    sale_date: Optional[str] = None
    image_url: Optional[str] = None
    listing_url: Optional[str] = None
    grade: Optional[str] = None


class ResearchResponse(BaseModel):
    results: list[ResearchResult]
    query: str
    scraped_at: datetime
    total_found: int
    avg_price: Optional[float] = None
    price_range: Optional[dict] = None
