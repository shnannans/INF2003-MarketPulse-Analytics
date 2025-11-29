"""
Error Handling Middleware (Task 55: Error Handling and Recovery)
Provides comprehensive error handling and recovery mechanisms
"""
import logging
import traceback
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from pymysql.err import OperationalError as PyMySQLOperationalError
import time

logger = logging.getLogger(__name__)


class ErrorHandler:
    """
    Error handler utility (Task 55: Error Handling and Recovery).
    Provides centralized error handling and recovery.
    """
    
    @staticmethod
    def handle_database_error(error: Exception, request: Request) -> JSONResponse:
        """
        Handle database-related errors (Task 55: Error Handling and Recovery).
        
        Args:
            error: Database error exception
            request: FastAPI request object
        
        Returns:
            JSONResponse with error details
        """
        error_type = type(error).__name__
        
        # Connection errors
        if isinstance(error, (OperationalError, PyMySQLOperationalError)):
            logger.error(f"Database connection error: {error}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "database_connection_error",
                    "message": "Database connection failed. Please try again later.",
                    "type": error_type,
                    "recoverable": True
                }
            )
        
        # Integrity errors (constraint violations)
        if isinstance(error, IntegrityError):
            logger.error(f"Database integrity error: {error}")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "database_integrity_error",
                    "message": "Data integrity constraint violation. Please check your input.",
                    "type": error_type,
                    "recoverable": True
                }
            )
        
        # Generic SQLAlchemy errors
        if isinstance(error, SQLAlchemyError):
            logger.error(f"Database error: {error}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "database_error",
                    "message": "A database error occurred. Please try again later.",
                    "type": error_type,
                    "recoverable": True
                }
            )
        
        # Unknown database error
        logger.error(f"Unknown database error: {error}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "unknown_database_error",
                "message": "An unexpected database error occurred.",
                "type": error_type,
                "recoverable": False
            }
        )
    
    @staticmethod
    def handle_validation_error(error: RequestValidationError, request: Request) -> JSONResponse:
        """
        Handle validation errors (Task 55: Error Handling and Recovery).
        
        Args:
            error: Validation error exception
            request: FastAPI request object
        
        Returns:
            JSONResponse with validation error details
        """
        errors = []
        for err in error.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in err.get("loc", [])),
                "message": err.get("msg", "Validation error"),
                "type": err.get("type", "unknown")
            })
        
        logger.warning(f"Validation error: {errors}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "errors": errors,
                "recoverable": True
            }
        )
    
    @staticmethod
    def handle_http_error(error: HTTPException, request: Request) -> JSONResponse:
        """
        Handle HTTP errors (Task 55: Error Handling and Recovery).
        
        Args:
            error: HTTP exception
            request: FastAPI request object
        
        Returns:
            JSONResponse with error details
        """
        logger.warning(f"HTTP error {error.status_code}: {error.detail}")
        
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": "http_error",
                "message": error.detail,
                "status_code": error.status_code,
                "recoverable": error.status_code < 500
            }
        )
    
    @staticmethod
    def handle_generic_error(error: Exception, request: Request) -> JSONResponse:
        """
        Handle generic errors (Task 55: Error Handling and Recovery).
        
        Args:
            error: Generic exception
            request: FastAPI request object
        
        Returns:
            JSONResponse with error details
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        logger.error(f"Unhandled error: {error_type} - {error_message}")
        logger.error(traceback.format_exc())
        
        # Don't expose internal error details in production
        from config.environment import config
        if config.is_production():
            message = "An internal server error occurred. Please try again later."
        else:
            message = f"{error_type}: {error_message}"
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": message,
                "type": error_type,
                "recoverable": False
            }
        )


async def error_handler_middleware(request: Request, call_next):
    """
    Error handling middleware (Task 55: Error Handling and Recovery).
    Catches and handles all exceptions.
    """
    start_time = time.time()
    
    try:
        response = await call_next(request)
        return response
    except RequestValidationError as e:
        return ErrorHandler.handle_validation_error(e, request)
    except HTTPException as e:
        return ErrorHandler.handle_http_error(e, request)
    except (SQLAlchemyError, PyMySQLOperationalError) as e:
        return ErrorHandler.handle_database_error(e, request)
    except Exception as e:
        return ErrorHandler.handle_generic_error(e, request)
    finally:
        duration = time.time() - start_time
        if duration > 1.0:  # Log slow requests
            logger.warning(f"Slow request: {request.method} {request.url.path} took {duration:.2f}s")

