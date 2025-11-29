"""
Documentation Endpoints (Task 70: Documentation Requirements)
Provides documentation content and help resources
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import logging

from config.database import get_mysql_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/docs/user-guide", response_model=dict)
async def get_user_guide(
    section: Optional[str] = Query(None, description="Section: search, dashboard, profile, faq"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get user guide documentation (Task 70: Documentation Requirements).
    Returns user guide content for different sections.
    """
    try:
        user_guide = {
            "search": {
                "title": "How to Search for Companies",
                "content": [
                    "Use the search box at the top of the page to search for companies",
                    "You can search by company name or ticker symbol",
                    "Use filters to narrow down results by sector, market cap, or price range",
                    "Click on a company name to view detailed information",
                    "Use autocomplete suggestions for faster searching"
                ],
                "tips": [
                    "Use partial company names for better results",
                    "Filter by sector to find companies in specific industries",
                    "Save your favorite searches for quick access"
                ]
            },
            "dashboard": {
                "title": "How to View Dashboards",
                "content": [
                    "The dashboard shows an overview of market data and analytics",
                    "Select a ticker symbol to view detailed stock information",
                    "Use the date range selector to view historical data",
                    "Charts show price trends, moving averages, and sentiment analysis",
                    "Use filters to customize the dashboard view"
                ],
                "tips": [
                    "Try different date ranges to see short-term and long-term trends",
                    "Compare multiple stocks using the comparison feature",
                    "Export dashboard data for further analysis"
                ]
            },
            "profile": {
                "title": "How to Manage Profile",
                "content": [
                    "Click on your profile icon to access profile settings",
                    "Update your email address and password",
                    "Set your preferences for notifications and display",
                    "View your account activity and history",
                    "Manage your saved searches and favorites"
                ],
                "tips": [
                    "Keep your email address up to date for important notifications",
                    "Use a strong password for account security",
                    "Review your account activity regularly"
                ]
            },
            "faq": {
                "title": "Frequently Asked Questions",
                "questions": [
                    {
                        "question": "How often is the data updated?",
                        "answer": "Stock prices are updated daily. News articles and sentiment analysis are updated in real-time."
                    },
                    {
                        "question": "Can I export data?",
                        "answer": "Yes, you can export data in JSON, CSV, or Excel formats from the export menu."
                    },
                    {
                        "question": "How do I filter companies?",
                        "answer": "Use the search and filter options to filter by sector, market cap, price range, or date range."
                    },
                    {
                        "question": "What is sentiment analysis?",
                        "answer": "Sentiment analysis analyzes news articles to determine positive, negative, or neutral sentiment about companies."
                    },
                    {
                        "question": "How do I contact support?",
                        "answer": "You can contact support through the help section or email support@marketpulse.com"
                    }
                ]
            }
        }
        
        if section and section.lower() in user_guide:
            selected = {section.lower(): user_guide[section.lower()]}
        else:
            selected = user_guide
        
        return {
            "status": "success",
            "section": section,
            "user_guide": selected,
            "message": "User guide retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting user guide: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user guide: {str(e)}"
        )


@router.get("/docs/admin-guide", response_model=dict)
async def get_admin_guide(
    section: Optional[str] = Query(None, description="Section: users, companies, news, system"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get admin guide documentation (Task 70: Documentation Requirements).
    Returns admin guide content for different sections.
    """
    try:
        admin_guide = {
            "users": {
                "title": "How to Manage Users",
                "content": [
                    "Access the user management page from the admin panel",
                    "View all users, including active and deleted users",
                    "Create new users with email and password",
                    "Edit user information, including role and status",
                    "Delete users (soft delete) or restore deleted users",
                    "Change user passwords and roles",
                    "Promote users to admin or demote admins to regular users"
                ],
                "tips": [
                    "Always verify user identity before making changes",
                    "Use soft delete to preserve user data",
                    "Monitor user activity for security"
                ]
            },
            "companies": {
                "title": "How to Add/Edit Companies",
                "content": [
                    "Access the company management page from the admin panel",
                    "Add new companies with ticker, name, sector, and market cap",
                    "Edit existing company information",
                    "Update financial metrics (PE ratio, dividend yield, beta)",
                    "Delete companies (soft delete) or restore deleted companies",
                    "Bulk import companies from CSV or Excel files"
                ],
                "tips": [
                    "Verify ticker symbols before adding companies",
                    "Keep company information up to date",
                    "Use bulk operations for efficiency"
                ]
            },
            "news": {
                "title": "How to Manage News",
                "content": [
                    "Access the news management page from the admin panel",
                    "Ingest news articles from external sources",
                    "Edit news article content and metadata",
                    "Delete news articles (soft delete) or restore deleted articles",
                    "Bulk ingest news articles from multiple sources",
                    "View sentiment analysis results for articles"
                ],
                "tips": [
                    "Verify news article sources for accuracy",
                    "Review sentiment analysis results",
                    "Keep news articles organized by date and source"
                ]
            },
            "system": {
                "title": "System Administration",
                "content": [
                    "Monitor system health from the health dashboard",
                    "View system status and sync history",
                    "Trigger manual data synchronization",
                    "Monitor database connection pool status",
                    "View cache statistics and clear caches",
                    "Monitor error logs and system metrics",
                    "Configure system settings and preferences"
                ],
                "tips": [
                    "Regularly check system health and metrics",
                    "Monitor error logs for issues",
                    "Keep system documentation up to date"
                ]
            }
        }
        
        if section and section.lower() in admin_guide:
            selected = {section.lower(): admin_guide[section.lower()]}
        else:
            selected = admin_guide
        
        return {
            "status": "success",
            "section": section,
            "admin_guide": selected,
            "message": "Admin guide retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting admin guide: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting admin guide: {str(e)}"
        )


@router.get("/docs/help-tooltips", response_model=dict)
async def get_help_tooltips(
    component: Optional[str] = Query(None, description="Component name"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get help tooltips for UI components (Task 70: Documentation Requirements).
    Returns tooltip content for different UI components.
    """
    try:
        tooltips = {
            "search_box": {
                "text": "Search for companies by name or ticker symbol. Use filters to narrow down results.",
                "position": "bottom"
            },
            "dashboard": {
                "text": "View market overview, stock prices, and analytics. Select a ticker to see detailed information.",
                "position": "bottom"
            },
            "filters": {
                "text": "Use filters to narrow down results by sector, market cap, price range, or date range.",
                "position": "right"
            },
            "export_button": {
                "text": "Export current data view to JSON, CSV, or Excel format.",
                "position": "top"
            },
            "refresh_button": {
                "text": "Refresh data to get the latest information.",
                "position": "left"
            },
            "user_profile": {
                "text": "Access your profile settings, preferences, and account information.",
                "position": "bottom"
            },
            "admin_panel": {
                "text": "Admin-only: Manage users, companies, news, and system settings.",
                "position": "bottom"
            }
        }
        
        if component and component.lower() in tooltips:
            selected = {component.lower(): tooltips[component.lower()]}
        else:
            selected = tooltips
        
        return {
            "status": "success",
            "component": component,
            "tooltips": selected,
            "message": "Help tooltips retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting help tooltips: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting help tooltips: {str(e)}"
        )


@router.get("/docs/onboarding", response_model=dict)
async def get_onboarding_tour(
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get onboarding tour steps (Task 70: Documentation Requirements).
    Returns steps for first-time user onboarding.
    """
    try:
        onboarding_tour = {
            "steps": [
                {
                    "step": 1,
                    "title": "Welcome to MarketPulse Analytics",
                    "content": "Welcome! This tour will help you get started with the platform.",
                    "target": "dashboard",
                    "position": "center"
                },
                {
                    "step": 2,
                    "title": "Search for Companies",
                    "content": "Use the search box to find companies by name or ticker symbol.",
                    "target": "search_box",
                    "position": "bottom"
                },
                {
                    "step": 3,
                    "title": "View Dashboard",
                    "content": "The dashboard shows market overview, stock prices, and analytics.",
                    "target": "dashboard",
                    "position": "top"
                },
                {
                    "step": 4,
                    "title": "Use Filters",
                    "content": "Use filters to narrow down results by sector, market cap, or price range.",
                    "target": "filters",
                    "position": "right"
                },
                {
                    "step": 5,
                    "title": "Explore Features",
                    "content": "Explore advanced features like charts, sentiment analysis, and exports.",
                    "target": "features",
                    "position": "center"
                }
            ],
            "settings": {
                "show_on_first_visit": True,
                "allow_skip": True,
                "show_progress": True,
                "auto_advance": False
            }
        }
        
        return {
            "status": "success",
            "onboarding_tour": onboarding_tour,
            "message": "Onboarding tour retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting onboarding tour: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting onboarding tour: {str(e)}"
        )


@router.get("/docs/contextual-help", response_model=dict)
async def get_contextual_help(
    context: Optional[str] = Query(None, description="Context: search, dashboard, profile, admin"),
    db: AsyncSession = Depends(get_mysql_session)
):
    """
    Get contextual help content (Task 70: Documentation Requirements).
    Returns context-specific help content.
    """
    try:
        contextual_help = {
            "search": {
                "title": "Search Help",
                "content": "Use the search box to find companies. You can search by company name or ticker symbol. Use filters to narrow down results.",
                "links": [
                    {"text": "User Guide - Search", "url": "/docs/user-guide?section=search"},
                    {"text": "FAQ", "url": "/docs/user-guide?section=faq"}
                ]
            },
            "dashboard": {
                "title": "Dashboard Help",
                "content": "The dashboard shows market overview, stock prices, and analytics. Select a ticker to view detailed information.",
                "links": [
                    {"text": "User Guide - Dashboard", "url": "/docs/user-guide?section=dashboard"},
                    {"text": "Chart Guide", "url": "/docs/charts"}
                ]
            },
            "profile": {
                "title": "Profile Help",
                "content": "Manage your profile settings, preferences, and account information. Update your email, password, and preferences.",
                "links": [
                    {"text": "User Guide - Profile", "url": "/docs/user-guide?section=profile"},
                    {"text": "Security Settings", "url": "/docs/security"}
                ]
            },
            "admin": {
                "title": "Admin Help",
                "content": "Admin panel for managing users, companies, news, and system settings. Requires admin privileges.",
                "links": [
                    {"text": "Admin Guide", "url": "/docs/admin-guide"},
                    {"text": "System Administration", "url": "/docs/admin-guide?section=system"}
                ]
            }
        }
        
        if context and context.lower() in contextual_help:
            selected = contextual_help[context.lower()]
        else:
            selected = contextual_help
        
        return {
            "status": "success",
            "context": context,
            "contextual_help": selected,
            "message": "Contextual help retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Error getting contextual help: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting contextual help: {str(e)}"
        )

