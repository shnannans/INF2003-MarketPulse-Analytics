"""
Test endpoint for Firestore connection
"""
from fastapi import APIRouter
from config.firestore import get_firestore_client, get_firestore_collection
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/test-firestore")
async def test_firestore():
    """Test Firestore connection and basic operations"""
    try:
        # Test client connection
        client = get_firestore_client()
        if not client:
            return {"status": "error", "message": "Failed to initialize Firestore client"}
        
        # Test collection access
        news_collection = get_firestore_collection('financial_news')
        sentiment_collection = get_firestore_collection('sentiment_trends')
        
        if not news_collection or not sentiment_collection:
            return {"status": "error", "message": "Failed to access Firestore collections"}
        
        # Test basic write operation
        test_doc = {
            'test': True,
            'timestamp': '2024-01-15T10:30:00Z',
            'message': 'Firestore connection test'
        }
        
        # Write test document
        news_collection.document('test_connection').set(test_doc)
        
        # Read test document
        doc = news_collection.document('test_connection').get()
        if doc.exists:
            doc_data = doc.to_dict()
            # Clean up test document
            news_collection.document('test_connection').delete()
            
            return {
                "status": "success", 
                "message": "Firestore connected and working",
                "project_id": client.project,
                "database_id": "databaseproj",
                "test_data": doc_data
            }
        else:
            return {"status": "error", "message": "Failed to read test document"}
            
    except Exception as e:
        logger.error(f"Firestore test error: {e}")
        return {"status": "error", "message": f"Firestore test failed: {str(e)}"}

@router.get("/firestore-stats")
async def get_firestore_stats():
    """Get basic statistics from Firestore collections"""
    try:
        client = get_firestore_client()
        if not client:
            return {"status": "error", "message": "Firestore not connected"}
        
        news_collection = get_firestore_collection('financial_news')
        sentiment_collection = get_firestore_collection('sentiment_trends')
        
        if not news_collection or not sentiment_collection:
            return {"status": "error", "message": "Collections not accessible"}
        
        # Count documents in collections
        news_docs = list(news_collection.limit(1000).stream())
        sentiment_docs = list(sentiment_collection.limit(1000).stream())
        
        return {
            "status": "success",
            "collections": {
                "financial_news": {
                    "count": len(news_docs),
                    "sample_doc": news_docs[0].to_dict() if news_docs else None
                },
                "sentiment_trends": {
                    "count": len(sentiment_docs),
                    "sample_doc": sentiment_docs[0].to_dict() if sentiment_docs else None
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Firestore stats error: {e}")
        return {"status": "error", "message": f"Failed to get stats: {str(e)}"}
