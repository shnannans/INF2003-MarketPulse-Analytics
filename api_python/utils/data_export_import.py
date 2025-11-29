"""
Data Export/Import Utilities (Task 57: Data Export/Import)
Provides utilities for exporting and importing data in various formats
"""
import logging
import csv
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import pandas as pd

logger = logging.getLogger(__name__)


class DataExporter:
    """
    Data exporter utility (Task 57: Data Export/Import).
    Exports data to various formats (JSON, CSV, Excel).
    """
    
    @staticmethod
    async def export_to_json(
        session: AsyncSession,
        query: Any,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Export query results to JSON (Task 57: Data Export/Import).
        
        Args:
            session: Database session
            query: SQLAlchemy query object
            output_path: Optional file path to save JSON
        
        Returns:
            Dictionary with exported data
        """
        try:
            result = await session.execute(query)
            rows = result.fetchall()
            
            # Convert to list of dictionaries
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in rows]
            
            # Convert datetime objects to strings
            for item in data:
                for key, value in item.items():
                    if isinstance(value, datetime):
                        item[key] = value.isoformat()
                    elif hasattr(value, 'isoformat'):  # date objects
                        item[key] = value.isoformat()
            
            # Save to file if path provided
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.info(f"Exported {len(data)} records to {output_path}")
            
            return {
                "status": "success",
                "record_count": len(data),
                "data": data,
                "output_path": output_path
            }
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    @staticmethod
    async def export_to_csv(
        session: AsyncSession,
        query: Any,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Export query results to CSV (Task 57: Data Export/Import).
        
        Args:
            session: Database session
            query: SQLAlchemy query object
            output_path: File path to save CSV
        
        Returns:
            Dictionary with export results
        """
        try:
            result = await session.execute(query)
            rows = result.fetchall()
            columns = result.keys()
            
            # Write to CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    # Convert datetime objects
                    for key, value in row_dict.items():
                        if isinstance(value, datetime):
                            row_dict[key] = value.isoformat()
                        elif hasattr(value, 'isoformat'):
                            row_dict[key] = value.isoformat()
                    writer.writerow(row_dict)
            
            logger.info(f"Exported {len(rows)} records to {output_path}")
            
            return {
                "status": "success",
                "record_count": len(rows),
                "output_path": output_path
            }
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    @staticmethod
    async def export_to_excel(
        session: AsyncSession,
        query: Any,
        output_path: str,
        sheet_name: str = "Data"
    ) -> Dict[str, Any]:
        """
        Export query results to Excel (Task 57: Data Export/Import).
        
        Args:
            session: Database session
            query: SQLAlchemy query object
            output_path: File path to save Excel file
            sheet_name: Name of the Excel sheet
        
        Returns:
            Dictionary with export results
        """
        try:
            result = await session.execute(query)
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to DataFrame
            data = [dict(zip(columns, row)) for row in rows]
            df = pd.DataFrame(data)
            
            # Write to Excel
            df.to_excel(output_path, sheet_name=sheet_name, index=False)
            
            logger.info(f"Exported {len(rows)} records to {output_path}")
            
            return {
                "status": "success",
                "record_count": len(rows),
                "output_path": output_path
            }
            
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


class DataImporter:
    """
    Data importer utility (Task 57: Data Export/Import).
    Imports data from various formats (JSON, CSV, Excel).
    """
    
    @staticmethod
    async def import_from_json(
        session: AsyncSession,
        file_path: str,
        model_class,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Import data from JSON file (Task 57: Data Export/Import).
        
        Args:
            session: Database session
            file_path: Path to JSON file
            model_class: SQLAlchemy model class
            batch_size: Number of records to import per batch
        
        Returns:
            Dictionary with import results
        """
        try:
            # Read JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                return {
                    "status": "error",
                    "error": "JSON file must contain an array of objects"
                }
            
            # Import in batches
            from utils.batch_operations import BatchProcessor
            
            result = await BatchProcessor.batch_insert(
                session, model_class, data, batch_size
            )
            
            return {
                "status": "success",
                "imported_count": result["inserted_count"],
                "errors": result["errors"]
            }
            
        except Exception as e:
            logger.error(f"Error importing from JSON: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    @staticmethod
    async def import_from_csv(
        session: AsyncSession,
        file_path: str,
        model_class,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Import data from CSV file (Task 57: Data Export/Import).
        
        Args:
            session: Database session
            file_path: Path to CSV file
            model_class: SQLAlchemy model class
            batch_size: Number of records to import per batch
        
        Returns:
            Dictionary with import results
        """
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Convert to list of dictionaries
            data = df.to_dict('records')
            
            # Import in batches
            from utils.batch_operations import BatchProcessor
            
            result = await BatchProcessor.batch_insert(
                session, model_class, data, batch_size
            )
            
            return {
                "status": "success",
                "imported_count": result["inserted_count"],
                "errors": result["errors"]
            }
            
        except Exception as e:
            logger.error(f"Error importing from CSV: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    @staticmethod
    async def import_from_excel(
        session: AsyncSession,
        file_path: str,
        model_class,
        sheet_name: str = 0,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Import data from Excel file (Task 57: Data Export/Import).
        
        Args:
            session: Database session
            file_path: Path to Excel file
            model_class: SQLAlchemy model class
            sheet_name: Name or index of the Excel sheet
            batch_size: Number of records to import per batch
        
        Returns:
            Dictionary with import results
        """
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Convert to list of dictionaries
            data = df.to_dict('records')
            
            # Import in batches
            from utils.batch_operations import BatchProcessor
            
            result = await BatchProcessor.batch_insert(
                session, model_class, data, batch_size
            )
            
            return {
                "status": "success",
                "imported_count": result["inserted_count"],
                "errors": result["errors"]
            }
            
        except Exception as e:
            logger.error(f"Error importing from Excel: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

