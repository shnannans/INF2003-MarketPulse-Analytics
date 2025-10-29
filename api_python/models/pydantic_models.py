from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

# Request models
class CompanyQuery(BaseModel):
    limit: Optional[int] = Field(default=100, ge=1, le=1000)
    sector: Optional[str] = None

class StockAnalysisQuery(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    days: Optional[int] = Field(default=90, ge=1, le=365)

class NewsQuery(BaseModel):
    ticker: Optional[str] = Field(default="", max_length=10)
    days: Optional[int] = Field(default=7, ge=1, le=30)
    sentiment: Optional[str] = Field(default="", pattern="^(positive|negative|neutral|)$")
    limit: Optional[int] = Field(default=20, ge=1, le=100)

class SentimentQuery(BaseModel):
    ticker: Optional[str] = Field(default="", max_length=10)
    days: Optional[int] = Field(default=7, ge=1, le=30)

class AlertsQuery(BaseModel):
    limit: Optional[int] = Field(default=10, ge=1, le=50)

class CorrelationQuery(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    date: Optional[str] = None

class IndicesQuery(BaseModel):
    days: Optional[int] = Field(default=30, ge=1, le=365)

# Response models
class CompanyResponse(BaseModel):
    ticker: str
    company_name: str
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[Decimal]
    description: Optional[str]
    pe_ratio: Optional[float]
    dividend_yield: Optional[float]
    current_market_cap: Optional[Decimal]
    beta: Optional[float]
    price_records_count: Optional[int]
    latest_price_date: Optional[date]

class StockPriceResponse(BaseModel):
    date: date
    open_price: Optional[Decimal]
    high_price: Optional[Decimal]
    low_price: Optional[Decimal]
    close_price: Optional[Decimal]
    adj_close: Optional[Decimal]
    volume: Optional[int]
    ma_5: Optional[Decimal]
    ma_20: Optional[Decimal]
    ma_50: Optional[Decimal]
    ma_200: Optional[Decimal]
    price_change_pct: Optional[float]
    volume_change_pct: Optional[float]

class StockAnalysisResponse(BaseModel):
    ticker: str
    company: Optional[CompanyResponse]
    current_price: Optional[Decimal]
    volatility: Optional[float]
    analysis: List[StockPriceResponse]
    count: int
    status: str

class NewsArticleResponse(BaseModel):
    id: str = Field(alias="_id")
    article_id: Optional[str]
    ticker: Optional[str]
    title: Optional[str]
    content: Optional[str]
    published_date: Optional[str]
    source: Optional[str]
    sentiment_analysis: Optional[Dict[str, Any]]
    extracted_entities: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]

    class Config:
        populate_by_name = True

class NewsResponse(BaseModel):
    articles: List[NewsArticleResponse]
    count: int
    filters: Dict[str, Any]
    status: str

class SentimentStats(BaseModel):
    total_articles: int
    avg_sentiment: float
    positive_count: int
    negative_count: int
    neutral_count: int

class SentimentTrend(BaseModel):
    date: str
    avg_sentiment: float
    article_count: int

class SentimentResponse(BaseModel):
    statistics: SentimentStats
    trends: List[SentimentTrend]
    filters: Dict[str, Any]
    status: str

class AlertResponse(BaseModel):
    ticker: str
    type: str
    message: str
    severity: str

class AlertsResponse(BaseModel):
    alerts: List[AlertResponse]
    count: int
    status: str

class CorrelationResponse(BaseModel):
    ticker: str
    date: Optional[str]
    correlation: float

class IndexData(BaseModel):
    name: str
    values: List[float]

class IndexSummary(BaseModel):
    name: str
    change_percent: float

class IndicesResponse(BaseModel):
    trend: List[Dict[str, str]]
    indices: List[IndexData]
    summary: List[IndexSummary]
    status: str
    note: Optional[str] = None

class DashboardSummaryResponse(BaseModel):
    total_companies: int
    total_articles: int
    recent_articles: int
    total_price_records: int
    latest_price_date: str
    avg_sentiment: float
    portfolio_value: str
    status: str

class ErrorResponse(BaseModel):
    error: str
    status: str
    debug_info: Optional[Dict[str, Any]] = None

class SuccessResponse(BaseModel):
    status: str = "success"
    message: str