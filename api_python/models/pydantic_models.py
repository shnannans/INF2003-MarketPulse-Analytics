from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

# Request models
class CompanyQuery(BaseModel):
    limit: Optional[int] = Field(default=100, ge=1, le=1000)
    sector: Optional[str] = None

class CompanyCreateRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")

class CompanyUpdateRequest(BaseModel):
    """Request model for PUT /api/companies/{ticker} - Full update (replace entire company)"""
    ticker: Optional[str] = Field(None, min_length=1, max_length=10, description="Stock ticker symbol (must match URL parameter)")
    company_name: Optional[str] = Field(None, max_length=255, description="Company name")
    sector: Optional[str] = Field(None, max_length=100, description="Company sector")
    market_cap: Optional[int] = Field(None, description="Market capitalization")

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

# Request models for news ingestion
class SentimentAnalysisRequest(BaseModel):
    """Optional pre-computed sentiment analysis"""
    polarity: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Sentiment polarity (-1 to 1)")
    subjectivity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Subjectivity score (0 to 1)")
    overall_score: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Overall sentiment score (-1 to 1)")
    textblob_score: Optional[float] = Field(None, ge=-1.0, le=1.0, description="TextBlob sentiment score")
    vader_score: Optional[float] = Field(None, ge=-1.0, le=1.0, description="VADER sentiment score")
    vader_breakdown: Optional[Dict[str, float]] = Field(None, description="VADER breakdown (positive, negative, neutral)")
    method: Optional[str] = Field(None, description="Sentiment analysis method used")
    analysis_timestamp: Optional[str] = Field(None, description="When sentiment was analyzed")

class NewsArticleIngestRequest(BaseModel):
    """Request model for POST /api/news/ingest - Single article ingestion"""
    title: str = Field(..., min_length=1, max_length=500, description="Article title")
    content: str = Field(..., min_length=1, description="Full article content")
    published_date: str = Field(..., description="Published date in ISO format (e.g., '2024-01-15T10:30:00Z')")
    source: Optional[str] = Field(None, max_length=200, description="News source (e.g., 'TechCrunch')")
    ticker: Optional[str] = Field(None, max_length=10, description="Stock ticker symbol this article relates to")
    url: Optional[str] = Field(None, max_length=500, description="Article URL")
    sentiment_analysis: Optional[SentimentAnalysisRequest] = Field(None, description="Pre-computed sentiment analysis (optional)")
    extracted_entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities from the article")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class NewsBulkIngestRequest(BaseModel):
    """Request model for POST /api/news/ingest - Bulk article ingestion"""
    articles: List[NewsArticleIngestRequest] = Field(..., min_items=1, max_items=100, description="List of articles to ingest")

class NewsArticlePatchRequest(BaseModel):
    """Request model for PATCH /api/news/{id} - Partial update (update only provided fields)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Article title")
    content: Optional[str] = Field(None, min_length=1, description="Full article content")
    published_date: Optional[str] = Field(None, description="Published date in ISO format (e.g., '2024-01-15T10:30:00Z')")
    source: Optional[str] = Field(None, max_length=200, description="News source (e.g., 'TechCrunch')")
    ticker: Optional[str] = Field(None, max_length=10, description="Stock ticker symbol this article relates to")
    url: Optional[str] = Field(None, max_length=500, description="Article URL")
    sentiment_analysis: Optional[SentimentAnalysisRequest] = Field(None, description="Pre-computed sentiment analysis (optional)")
    extracted_entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities from the article")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class SentimentStats(BaseModel):
    total_articles: int
    avg_sentiment: float
    positive_count: int
    negative_count: int
    neutral_count: int

# User Management Models
class UserCreateRequest(BaseModel):
    """Request model for POST /api/users - Create new user"""
    username: str = Field(..., min_length=3, max_length=50, description="Username (must be unique)")
    email: str = Field(..., description="Email address (must be unique and valid format)")
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    role: Optional[str] = Field("user", description="User role: 'user' or 'admin' (default: 'user')")

class UserResponse(BaseModel):
    """Response model for user data (excludes password)"""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    deleted_at: Optional[str]

class UserUpdateRequest(BaseModel):
    """Request model for PUT /api/users/{user_id} - Full update (replace entire user, except password)"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username (must be unique)")
    email: Optional[str] = Field(None, description="Email address (must be unique and valid format)")
    role: Optional[str] = Field(None, description="User role: 'user' or 'admin'")
    is_active: Optional[bool] = Field(None, description="Active status (true/false)")

class PasswordChangeRequest(BaseModel):
    """Request model for PATCH /api/users/{user_id}/password - Change user password"""
    current_password: Optional[str] = Field(None, description="Current password (required for users changing their own password, optional for admins)")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")

class RoleChangeRequest(BaseModel):
    """Request model for PATCH /api/users/{user_id}/role - Change user role"""
    role: str = Field(..., description="New role: 'user' or 'admin'")

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