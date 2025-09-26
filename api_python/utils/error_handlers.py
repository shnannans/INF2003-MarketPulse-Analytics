from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Union

# Custom exception classes
class DatabaseConnectionError(Exception):
    def __init__(self, message: str = "Database connection failed"):
        self.message = message
        super().__init__(self.message)

class InvalidTickerError(Exception):
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.message = f"Invalid or unknown ticker: {ticker}"
        super().__init__(self.message)

class DataNotFoundError(Exception):
    def __init__(self, message: str = "Data not found"):
        self.message = message
        super().__init__(self.message)

# Exception handlers
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status": "error",
            "status_code": exc.status_code
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": errors,
            "status": "error",
            "status_code": 422
        }
    )

async def database_exception_handler(request: Request, exc: DatabaseConnectionError):
    logging.error(f"Database connection error: {exc.message}")
    return JSONResponse(
        status_code=503,
        content={
            "error": "Database service unavailable",
            "status": "error",
            "status_code": 503
        }
    )

async def ticker_exception_handler(request: Request, exc: InvalidTickerError):
    return JSONResponse(
        status_code=404,
        content={
            "error": exc.message,
            "ticker": exc.ticker,
            "status": "error",
            "status_code": 404
        }
    )

async def data_not_found_exception_handler(request: Request, exc: DataNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": exc.message,
            "status": "error",
            "status_code": 404
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status": "error",
            "status_code": 500
        }
    )

# Utility function to handle common database errors
def handle_database_error(e: Exception) -> HTTPException:
    error_msg = str(e)
    logging.error(f"Database error: {error_msg}")

    if "connection" in error_msg.lower():
        raise HTTPException(status_code=503, detail="Database connection failed")
    elif "timeout" in error_msg.lower():
        raise HTTPException(status_code=504, detail="Database operation timeout")
    else:
        raise HTTPException(status_code=500, detail="Database operation failed")

# Utility function to validate and format responses
def create_error_response(status_code: int, message: str, details: dict = None):
    response = {
        "error": message,
        "status": "error",
        "status_code": status_code
    }
    if details:
        response["details"] = details
    return response

def create_success_response(data: Union[dict, list], message: str = "Success"):
    if isinstance(data, dict):
        data["status"] = "success"
        return data
    else:
        return {
            "data": data,
            "status": "success",
            "message": message
        }