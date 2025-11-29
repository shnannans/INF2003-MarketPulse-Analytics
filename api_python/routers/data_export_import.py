"""
Data Export/Import Endpoints (Task 57: Data Export/Import)
Provides endpoints for exporting and importing data
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Optional
import logging
from pathlib import Path
import tempfile
import os
from datetime import datetime

from config.database import get_mysql_session
from utils.data_export_import import DataExporter, DataImporter
from models.database_models import Company, StockPrice

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/export/companies", response_model=dict)
async def export_companies(
    format: str = Query("json", description="Export format: json, csv, excel"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Export companies to file (Task 57: Data Export/Import).
    """
    try:
        async for db_session in db:
            query = select(Company).where(Company.deleted_at.is_(None))
            
            # Create temp directory
            temp_dir = Path(tempfile.gettempdir()) / "marketpulse_exports"
            temp_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == "json":
                output_path = temp_dir / f"companies_{timestamp}.json"
                result = await DataExporter.export_to_json(db_session, query, str(output_path))
            elif format.lower() == "csv":
                output_path = temp_dir / f"companies_{timestamp}.csv"
                result = await DataExporter.export_to_csv(db_session, query, str(output_path))
            elif format.lower() == "excel":
                output_path = temp_dir / f"companies_{timestamp}.xlsx"
                result = await DataExporter.export_to_excel(db_session, query, str(output_path), "Companies")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported format: {format}. Supported formats: json, csv, excel"
                )
            
            if result["status"] == "success":
                return FileResponse(
                    path=output_path,
                    filename=output_path.name,
                    media_type="application/octet-stream"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("error", "Export failed")
                )
            break
        
    except Exception as e:
        logger.error(f"Error exporting companies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting companies: {str(e)}"
        )


@router.get("/export/stock-prices", response_model=dict)
async def export_stock_prices(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    format: str = Query("json", description="Export format: json, csv, excel"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Export stock prices to file (Task 57: Data Export/Import).
    """
    try:
        async for db_session in db:
            query = select(StockPrice)
            if ticker:
                query = query.where(StockPrice.ticker == ticker.upper())
            
            # Create temp directory
            temp_dir = Path(tempfile.gettempdir()) / "marketpulse_exports"
            temp_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_prefix = f"stock_prices_{ticker or 'all'}_{timestamp}"
            
            if format.lower() == "json":
                output_path = temp_dir / f"{filename_prefix}.json"
                result = await DataExporter.export_to_json(db_session, query, str(output_path))
            elif format.lower() == "csv":
                output_path = temp_dir / f"{filename_prefix}.csv"
                result = await DataExporter.export_to_csv(db_session, query, str(output_path))
            elif format.lower() == "excel":
                output_path = temp_dir / f"{filename_prefix}.xlsx"
                result = await DataExporter.export_to_excel(db_session, query, str(output_path), "Stock Prices")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported format: {format}. Supported formats: json, csv, excel"
                )
            
            if result["status"] == "success":
                return FileResponse(
                    path=output_path,
                    filename=output_path.name,
                    media_type="application/octet-stream"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("error", "Export failed")
                )
            break
        
    except Exception as e:
        logger.error(f"Error exporting stock prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting stock prices: {str(e)}"
        )


@router.get("/export/query", response_model=dict)
async def export_custom_query(
    sql: str = Query(..., description="SQL query to execute"),
    format: str = Query("json", description="Export format: json, csv, excel"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Export custom SQL query results (Task 57: Data Export/Import).
    """
    try:
        async for db_session in db:
            query = text(sql)
            
            # Create temp directory
            temp_dir = Path(tempfile.gettempdir()) / "marketpulse_exports"
            temp_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == "json":
                output_path = temp_dir / f"query_{timestamp}.json"
                result = await DataExporter.export_to_json(db_session, query, str(output_path))
            elif format.lower() == "csv":
                output_path = temp_dir / f"query_{timestamp}.csv"
                result = await DataExporter.export_to_csv(db_session, query, str(output_path))
            elif format.lower() == "excel":
                output_path = temp_dir / f"query_{timestamp}.xlsx"
                result = await DataExporter.export_to_excel(db_session, query, str(output_path), "Query Results")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported format: {format}. Supported formats: json, csv, excel"
                )
            
            if result["status"] == "success":
                return FileResponse(
                    path=output_path,
                    filename=output_path.name,
                    media_type="application/octet-stream"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("error", "Export failed")
                )
            break
        
    except Exception as e:
        logger.error(f"Error exporting query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting query: {str(e)}"
        )

