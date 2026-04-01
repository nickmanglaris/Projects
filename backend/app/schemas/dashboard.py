from datetime import date
from typing import Optional
from pydantic import BaseModel


class DashboardSummary(BaseModel):
    revenue_total: float
    cost_total: float
    profit_total: float
    roi_pct: float
    period: str
    is_mock: bool = False
    transaction_count: int = 0
    avg_profit_per_card: float = 0.0


class TrajectoryPoint(BaseModel):
    date: str
    revenue: float
    cost: float
    profit: float
    cumulative_profit: float


class TrajectoryResponse(BaseModel):
    data: list[TrajectoryPoint]
    period: str
    is_mock: bool = False
