from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
import asyncio
from routers import companies, stock_analysis, news, sentiment, alerts, dashboard, indices, correlation, timeline, firestore_test, users, advanced_analytics, transaction_demo, pool_monitoring, cache_monitoring, data_warehouse, stored_procedures, performance, auth
from middleware.security import SecurityHeadersMiddleware
from middleware.rate_limiting import RateLimitMiddleware
from middleware.logging_middleware import RequestLoggingMiddleware
from utils.logging_config import setup_logging

# Import database config
from config import database as db_config
from config.database import init_database, close_database, test_all_connections
# Import startup sync
from utils.startup_sync import sync_all_data

# Configure logging (Task 50: Logging and Monitoring)
logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", "logs/marketpulse.log")
)
logger.info("Logging configured successfully")

# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MarketPulse API...")
    await init_database()
    
    # Run startup data synchronization in background (non-blocking)
    async def run_startup_sync():
        """Run startup sync in background without blocking server startup"""
        try:
            # Small delay to ensure server is ready
            await asyncio.sleep(1)
            
            # Access AsyncSessionLocal from the module after initialization
            if db_config.AsyncSessionLocal:
                async with db_config.AsyncSessionLocal() as session:
                    logger.info("Starting background data synchronization...")
                    sync_summary = await sync_all_data(session)
                    logger.info(f"Background startup sync completed: {sync_summary}")
            else:
                logger.warning("Database session not available, skipping startup sync")
        except Exception as e:
            logger.error(f"Background startup synchronization failed: {e}")
            logger.info("Continuing despite sync errors...")
    
    # Start sync in background task (non-blocking)
    sync_task = asyncio.create_task(run_startup_sync())
    logger.info("Server ready - startup sync running in background")
    
    yield
    
    # Cancel sync task on shutdown if still running
    if not sync_task.done():
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            logger.info("Startup sync task cancelled during shutdown")
    # Shutdown  
    logger.info("Shutting down MarketPulse API...")
    await close_database()

# Create FastAPI app (Task 51: API Documentation Enhancements)
app = FastAPI(
    title="MarketPulse Analytics API",
    description="""
    ## MarketPulse Analytics Platform - Python FastAPI Backend
    
    A comprehensive stock market analytics platform providing:
    
    * **Stock Data Management**: CRUD operations for companies and stock prices
    * **Advanced Analytics**: Window functions, CTEs, rolling aggregations
    * **News Integration**: News article ingestion with sentiment analysis
    * **User Management**: User authentication and role-based access control
    * **Data Warehouse**: Star schema design with materialized views
    * **Performance Optimization**: Query optimization, caching, connection pooling
    * **Security**: Input validation, rate limiting, security headers
    * **Monitoring**: Health checks, metrics, logging
    
    ### Features
    
    - Real-time stock price tracking
    - Sentiment analysis from news articles
    - Advanced SQL analytics (window functions, CTEs)
    - Data warehouse with ETL pipeline
    - Optimized queries with indexing strategies
    - Transaction management and concurrency control
    - Comprehensive security and rate limiting
    - System monitoring and logging
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "MarketPulse API Support",
        "email": "support@marketpulse.com",
    },
    license_info={
        "name": "MIT",
    },
    servers=[
        {
            "url": "http://localhost:8080",
            "description": "Development server"
        },
        {
            "url": "https://api.marketpulse.com",
            "description": "Production server"
        }
    ]
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Security Headers Middleware (Task 48: Security Best Practices)
app.add_middleware(SecurityHeadersMiddleware)

# Add Rate Limiting Middleware (Task 49: API Rate Limiting)
# Configure: 500 requests per minute, 10000 requests per hour
app.add_middleware(RateLimitMiddleware, requests_per_minute=500, requests_per_hour=10000)

# Add Request Logging Middleware (Task 50: Logging and Monitoring)
app.add_middleware(RequestLoggingMiddleware)

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
app.include_router(auth.router, prefix="/api", tags=["authentication"])
app.include_router(companies.router, prefix="/api", tags=["companies"])
app.include_router(stock_analysis.router, prefix="/api", tags=["stock-analysis"])
app.include_router(news.router, prefix="/api", tags=["news"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(sentiment.router, prefix="/api", tags=["sentiment"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(indices.router, prefix="/api", tags=["indices"])
app.include_router(correlation.router, prefix="/api", tags=["correlation"])
app.include_router(timeline.router, prefix="/api", tags=["timeline"])
app.include_router(firestore_test.router, prefix="/api", tags=["firestore-test"])
app.include_router(advanced_analytics.router, prefix="/api", tags=["advanced-analytics"])
app.include_router(transaction_demo.router, prefix="/api", tags=["transaction-demo"])
app.include_router(pool_monitoring.router, prefix="/api", tags=["pool-monitoring"])
app.include_router(cache_monitoring.router, prefix="/api", tags=["cache-monitoring"])
app.include_router(data_warehouse.router, prefix="/api", tags=["data-warehouse"])
app.include_router(stored_procedures.router, prefix="/api", tags=["stored-procedures"])
app.include_router(performance.router, prefix="/api", tags=["performance"])

# Import and register security router
from routers import security
app.include_router(security.router, prefix="/api", tags=["security"])

# Import and register monitoring router
from routers import monitoring
app.include_router(monitoring.router, prefix="/api", tags=["monitoring"])

# Import and register deployment router
from routers import deployment
app.include_router(deployment.router, prefix="/api", tags=["deployment"])

# Import and register versioned router
from routers import versioned
app.include_router(versioned.router, prefix="/api", tags=["versioning"])

# Mount static files (HTML, JS, CSS)
# IMPORTANT: Mount static files AFTER all API routes to avoid conflicts
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    # Mount JS and CSS at their respective paths
    app.mount("/js", StaticFiles(directory=str(static_dir / "js")), name="js")
    app.mount("/css", StaticFiles(directory=str(static_dir / "css")), name="css")
    # Mount HTML files at root (must be last to avoid route conflicts)
    # html=True enables directory index and serves index.html for /
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="root")
    logger.info(f"Static files mounted from: {static_dir}")
    logger.info(f"  - HTML files accessible at: http://localhost:8080/login.html")
    logger.info(f"  - JS files accessible at: http://localhost:8080/js/")
    logger.info(f"  - CSS files accessible at: http://localhost:8080/css/")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Batch operations router removed

# Import and register data export/import router
from routers import data_export_import
app.include_router(data_export_import.router, prefix="/api", tags=["data-export-import"])

# Import and register financial metrics router
from routers import financial_metrics
app.include_router(financial_metrics.router, prefix="/api", tags=["financial-metrics"])

# Import and register system status router
from routers import system_status
app.include_router(system_status.router, prefix="/api", tags=["system-status"])

# Import and register health dashboard router
from routers import health_dashboard
app.include_router(health_dashboard.router, prefix="/api", tags=["health-dashboard"])

# Import and register search filtering router
from routers import search_filtering
app.include_router(search_filtering.router, prefix="/api", tags=["search-filtering"])

# Import and register error states router
from routers import error_states
app.include_router(error_states.router, prefix="/api", tags=["error-states"])

# Import and register loading states router
from routers import loading_states
app.include_router(loading_states.router, prefix="/api", tags=["loading-states"])

# Import and register advanced charts router
from routers import advanced_charts
app.include_router(advanced_charts.router, prefix="/api", tags=["advanced-charts"])

# Import and register real-time updates router
from routers import realtime_updates
app.include_router(realtime_updates.router, prefix="/api", tags=["realtime-updates"])

# Mobile responsiveness router removed

# Accessibility router removed

# Import and register performance optimization router
from routers import performance_optimization
app.include_router(performance_optimization.router, prefix="/api", tags=["performance-optimization"])

# Import and register testing router
from routers import testing
app.include_router(testing.router, prefix="/api", tags=["testing"])

# Import and register documentation router
from routers import documentation
app.include_router(documentation.router, prefix="/api", tags=["documentation"])

# Import and register frontend security router
from routers import security_frontend
app.include_router(security_frontend.router, prefix="/api", tags=["security-frontend"])

# Import and register state management router
from routers import state_management
app.include_router(state_management.router, prefix="/api", tags=["state-management"])

# Import and register API integration router
from routers import api_integration
app.include_router(api_integration.router, prefix="/api", tags=["api-integration"])

# Import and register notifications router
from routers import notifications
app.include_router(notifications.router, prefix="/api", tags=["notifications"])

# Global exception handlers (Task 55: Error Handling and Recovery)
from middleware.error_handler import ErrorHandler

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return ErrorHandler.handle_validation_error(exc, request)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return ErrorHandler.handle_http_error(HTTPException(status_code=exc.status_code, detail=exc.detail), request)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return ErrorHandler.handle_generic_error(exc, request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)