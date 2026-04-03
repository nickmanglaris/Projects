from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ResearchRequest(BaseModel):
    player_name: str
    year: Optional[int] = None
    variation: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    max_results: int = 20


class CardAnalysis(BaseModel):
    psa10_potential: str = "Unknown"  # High / Medium / Low / Unknown / Not analyzed
    verdict: Optional[str] = None
    centering: Optional[str] = None
    corners: Optional[str] = None
    edges: Optional[str] = None
    surface: Optional[str] = None


class ResearchResult(BaseModel):
    title: str
    price: float
    sale_date: Optional[str] = None
    image_url: Optional[str] = None
    listing_url: Optional[str] = None
    grade: Optional[str] = None
    analysis: Optional[CardAnalysis] = None


class ResearchResponse(BaseModel):
    results: list[ResearchResult]
    query: str
    scraped_at: datetime
    total_found: int
    avg_price: Optional[float] = None
    price_range: Optional[dict] = None
    ai_analysis_enabled: bool = False
