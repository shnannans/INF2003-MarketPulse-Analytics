from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from contextlib import asynccontextmanager
from routers import companies, stock_analysis, news, sentiment, alerts, dashboard, indices, correlation, timeline

# Import database config
from config.database import init_database, close_database, test_all_connections

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MarketPulse API...")
    await init_database()
    yield
    # Shutdown  
    logger.info("Shutting down MarketPulse API...")
    await close_database()

# Create FastAPI app
app = FastAPI(
    title="MarketPulse API",
    description="Stock News Analytics Platform - Python FastAPI Backend",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        connections = await test_all_connections()
        return {
            "status": "healthy",
            "database_connections": connections,
            "message": "MarketPulse API is running"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "MarketPulse Stock Analytics API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Import and include routers (only include ones that exist)
app.include_router(companies.router, prefix="/api", tags=["companies"])
app.include_router(stock_analysis.router, prefix="/api", tags=["stock-analysis"])
app.include_router(news.router, prefix="/api", tags=["news"])
app.include_router(sentiment.router, prefix="/api", tags=["sentiment"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(indices.router, prefix="/api", tags=["indices"])
app.include_router(correlation.router, prefix="/api", tags=["correlation"])
app.include_router(timeline.router, prefix="/api", tags=["timeline"])

# Global exception handlers - FIXED VERSION
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)