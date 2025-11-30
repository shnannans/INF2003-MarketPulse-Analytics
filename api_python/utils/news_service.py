"""
Live NewsAPI integration with real-time sentiment analysis
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from cachetools import TTLCache
import asyncio
import re
from concurrent.futures import ThreadPoolExecutor

from newsapi import NewsApiClient
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config.database import get_mysql_session
from models.database_models import Company
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Initialize services
newsapi_client = None
vader_analyzer = SentimentIntensityAnalyzer()

# Cache for news articles (TTL cache)
news_cache = TTLCache(maxsize=1000, ttl=int(os.getenv('NEWS_CACHE_TTL', 300)))

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)

def init_news_service():
    """Initialize NewsAPI client"""
    global newsapi_client
    # Try environment variable first, then fallback to demo mode
    api_key = os.getenv('NEWSAPI_KEY')

    # For demo purposes, we'll use realistic mock data without API key
    if not api_key:
        logger.info("No NEWSAPI_KEY found in environment. Using demo mode with realistic mock data.")
        newsapi_client = None
        return False

    try:
        newsapi_client = NewsApiClient(api_key=api_key)
        # Test the API key with a simple request
        test_response = newsapi_client.get_top_headlines(page_size=1, country='us')
        if test_response and test_response.get('status') == 'ok':
            logger.info("NewsAPI client initialized and verified successfully")
            return True
        else:
            logger.warning(f"NewsAPI test failed: {test_response}")
            newsapi_client = None
            return False
    except Exception as e:
        logger.error(f"Failed to initialize NewsAPI client: {e}")
        newsapi_client = None
        return False

def analyze_sentiment_textblob(text: str) -> Dict:
    """Analyze sentiment using TextBlob"""
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1
        subjectivity = blob.sentiment.subjectivity  # 0 to 1

        return {
            "overall_score": round(polarity, 4),
            "subjectivity": round(subjectivity, 4),
            "method": "textblob"
        }
    except Exception as e:
        logger.error(f"TextBlob sentiment analysis error: {e}")
        return {"overall_score": 0.0, "subjectivity": 0.0, "method": "textblob"}

def analyze_sentiment_vader(text: str) -> Dict:
    """Analyze sentiment using VADER"""
    try:
        scores = vader_analyzer.polarity_scores(text)
        # Convert compound score (-1 to 1) to our format
        return {
            "overall_score": round(scores['compound'], 4),
            "positive": round(scores['pos'], 4),
            "negative": round(scores['neg'], 4),
            "neutral": round(scores['neu'], 4),
            "method": "vader"
        }
    except Exception as e:
        logger.error(f"VADER sentiment analysis error: {e}")
        return {"overall_score": 0.0, "positive": 0.0, "negative": 0.0, "neutral": 0.0, "method": "vader"}

def clean_article_content(content: str) -> str:
    """Clean article content by removing promotional text and artifacts"""
    if not content:
        return content

    # Common promotional patterns to remove
    promotional_patterns = [
        # Stock ticker references with "Free Report"
        r'\([A-Z]+:[A-Z]+ – Free Report\)',
        r'\([A-Z]+:[A-Z]+ - Free Report\)',

        # Other common artifacts
        r'\(NYSE:[A-Z]+\)',
        r'\(NASDAQ:[A-Z]+\)',
        r'\(AMEX:[A-Z]+\)',

        # Newsletter/subscription promotions
        r'Subscribe to.*?newsletter',
        r'Get.*?free report',
        r'Click here.*?more',
        r'Read more.*?(?:\.|$)',

        # Advertisement indicators
        r'Advertisement\s*\n',
        r'Sponsored Content\s*\n',
        r'Promoted by.*?\n',

        # Social media artifacts
        r'Follow.*?on Twitter',
        r'Like us on Facebook',
        r'@[A-Za-z0-9_]+',  # Twitter handles

        # Newsletter signup calls
        r'Sign up.*?newsletter',
        r'Subscribe.*?updates',

        # Photo/video credits that clutter content
        r'Photo.*?Getty Images',
        r'Image.*?Reuters',
        r'Video.*?Bloomberg',

        # Common footer text
        r'This story originally appeared.*',
        r'Originally published.*',

        # Weird spacing artifacts
        r'\s+\n\s*\n',  # Multiple blank lines
    ]

    cleaned_content = content
    for pattern in promotional_patterns:
        cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE)

    # Clean up extra whitespace
    cleaned_content = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_content)  # Max 2 newlines
    cleaned_content = re.sub(r'[ \t]+', ' ', cleaned_content)  # Normalize spaces
    cleaned_content = cleaned_content.strip()

    # Remove trailing promotional calls to action
    trailing_patterns = [
        r'\.\s*Click here.*$',
        r'\.\s*Read more.*$',
        r'\.\s*Subscribe.*$',
        r'\.\s*Get.*report.*$',
    ]

    for pattern in trailing_patterns:
        cleaned_content = re.sub(pattern, '.', cleaned_content, flags=re.IGNORECASE)

    return cleaned_content

def combine_sentiment_analysis(text: str) -> Dict:
    """Combine TextBlob and VADER for more accurate sentiment"""
    textblob_result = analyze_sentiment_textblob(text)
    vader_result = analyze_sentiment_vader(text)

    # Weighted average (VADER is generally better for social media/news)
    combined_score = (textblob_result["overall_score"] * 0.3) + (vader_result["overall_score"] * 0.7)

    # Determine overall_sentiment category based on score thresholds
    if combined_score > 0.1:
        overall_sentiment = "positive"
    elif combined_score < -0.1:
        overall_sentiment = "negative"
    else:
        overall_sentiment = "neutral"

    return {
        "overall_score": round(combined_score, 4),
        "overall_sentiment": overall_sentiment,  # Add this field for proper categorization
        "textblob_score": textblob_result["overall_score"],
        "vader_score": vader_result["overall_score"],
        "vader_breakdown": {
            "positive": vader_result["positive"],
            "negative": vader_result["negative"],
            "neutral": vader_result["neutral"]
        },
        "method": "combined",
        "analysis_timestamp": datetime.now().isoformat()
    }

async def fetch_news_async(query: str, days: int = 7, language: str = 'en') -> List[Dict]:
    """Fetch news articles asynchronously"""
    if not newsapi_client:
        logger.warning("NewsAPI client not available, no news data will be returned")
        return []

    # Check cache first
    cache_key = f"{query}_{days}_{language}"
    if cache_key in news_cache:
        logger.info(f"Returning cached news for query: {query}")
        return news_cache[cache_key]

    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Run NewsAPI call in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        def fetch_news_sync():
            try:
                # Search for articles
                articles_response = newsapi_client.get_everything(
                    q=query,
                    from_param=start_date.strftime('%Y-%m-%d'),
                    to=end_date.strftime('%Y-%m-%d'),
                    language=language,
                    sort_by='publishedAt',
                    page_size=int(os.getenv('MAX_ARTICLES_PER_REQUEST', 50))
                )
                return articles_response.get('articles', [])
            except Exception as e:
                logger.error(f"NewsAPI fetch error: {e}")
                return []

        raw_articles = await loop.run_in_executor(executor, fetch_news_sync)

        # Process articles with sentiment analysis
        processed_articles = []
        for article in raw_articles:
            try:
                # Prepare content for display and sentiment analysis
                title = article.get('title', '').strip()
                description = article.get('description', '').strip()
                raw_content = article.get('content', '').strip()

                # Clean and combine content for sentiment analysis
                sentiment_text = ""
                if title:
                    sentiment_text += title + ". "
                if description:
                    sentiment_text += description + ". "

                # Clean raw content (NewsAPI often has truncated content with [...] or [+xxx chars])
                cleaned_content = raw_content
                if raw_content:
                    # Remove NewsAPI truncation indicators
                    if '[+' in raw_content:
                        cleaned_content = raw_content.split('[+')[0].strip()
                    elif '…' in raw_content:
                        # Keep content up to ellipsis but don't truncate further
                        pass

                    # Apply content cleaning to remove promotional artifacts
                    cleaned_content = clean_article_content(cleaned_content)

                    sentiment_text += cleaned_content

                # Clean description as well
                cleaned_description = clean_article_content(description) if description else ""

                # Create full display content (title + description + content)
                full_content = ""
                if title:
                    full_content += title
                if cleaned_description and cleaned_description not in title:
                    full_content += ("\n\n" if full_content else "") + cleaned_description
                if cleaned_content and cleaned_content not in (title + cleaned_description):
                    full_content += ("\n\n" if full_content else "") + cleaned_content

                # Perform sentiment analysis on the complete text
                sentiment_analysis = combine_sentiment_analysis(sentiment_text)

                # Format article for our API - keep full content without truncation
                # Generate article_id from URL hash (ensure positive number)
                url = article.get('url', '')
                url_hash = abs(hash(url)) if url else int(datetime.now().timestamp() * 1000000)
                processed_article = {
                    "article_id": f"newsapi_{url_hash}",
                    "ticker": query.upper() if len(query) <= 5 else "",  # Assume ticker if short
                    "title": title,
                    "content": full_content,  # Remove arbitrary length limit
                    "published_date": article.get('publishedAt', ''),
                    "source": {
                        "name": article.get('source', {}).get('name', 'Unknown'),
                        "url": article.get('url', '')
                    },
                    "url": article.get('url', ''),
                    "sentiment_analysis": sentiment_analysis,
                    "extracted_entities": [],  # TODO: Could add NER here
                    "metadata": {
                        "fetched_at": datetime.now().isoformat(),
                        "api_source": "newsapi_live"
                    }
                }
                processed_articles.append(processed_article)

            except Exception as e:
                logger.error(f"Error processing article: {e}")
                continue

        # Cache the results (only if we have articles)
        if processed_articles:
            news_cache[cache_key] = processed_articles
            logger.info(f"Fetched and cached {len(processed_articles)} articles for query: {query}")
        else:
            logger.warning(f"No articles fetched for query '{query}'")

        return processed_articles

    except Exception as e:
        logger.error(f"Error fetching news for query '{query}': {e}")
        return []


async def get_company_info_from_db(ticker: str) -> Dict:
    """Get company search terms from MySQL database"""
    try:
        async for db in get_mysql_session():
            stmt = select(Company).where(Company.ticker == ticker.upper())
            result = await db.execute(stmt)
            company = result.first()

            if company:
                company_obj = company[0]
                return {
                    'names': [company_obj.company_name, ticker],
                    'industry': f"{company_obj.sector} {company_obj.industry}",
                    'exclude': ''  # Could add exclusion rules later
                }
            else:
                return {
                    'names': [ticker],
                    'industry': 'stock earnings financial',
                    'exclude': ''
                }
    except Exception as e:
        logger.error(f"Database query failed for {ticker}: {e}")
        return {'names': [ticker], 'industry': 'financial', 'exclude': ''}


async def get_financial_news(ticker: str = "", days: int = 7, sentiment_filter: str = "") -> List[Dict]:
    """Get financial news for a specific ticker or general financial news"""

    # Build search query with improved ticker-specific terms
    if ticker:
        ticker = ticker.upper()

        # Get company information from database
        search_info = await get_company_info_from_db(ticker)

        # Build comprehensive search query
        primary_terms = ' OR '.join([f'"{name}"' for name in search_info['names']])
        industry_terms = search_info['industry']

        # Create focused search query that prioritizes company names with industry context
        search_query = f'({primary_terms}) AND ({industry_terms})'

        # Add ticker as secondary search term
        if ticker not in search_info['names'][0]:
            search_query += f' OR ({ticker} AND (earnings OR stock OR financial OR quarterly))'
    else:
        # General financial news with more specific terms
        search_query = "stock market OR financial markets OR earnings OR economic news OR Wall Street"

    # Fetch articles
    articles = await fetch_news_async(search_query, days)

    # Post-process articles for ticker-specific searches
    if ticker and articles:
        # Filter for relevance to the specific company
        search_info = await get_company_info_from_db(ticker)
        filtered_articles = []

        for article in articles:
            # Ensure ticker is set for ticker-specific searches
            if not article.get('ticker') or article['ticker'] == '':
                article['ticker'] = ticker

            # Check relevance - article should mention company names or ticker
            title_content = (article.get('title', '') + ' ' + article.get('content', '')).lower()

            # Check if any company name is mentioned
            company_mentioned = any(name.lower() in title_content for name in search_info['names'])
            ticker_mentioned = ticker.lower() in title_content

            # Check for exclusion terms (e.g., "apple fruit" when searching for AAPL)
            exclude_terms = search_info.get('exclude', '').split()
            excluded = any(term in title_content for term in exclude_terms if term)

            # Include article if relevant and not excluded
            if (company_mentioned or ticker_mentioned) and not excluded:
                filtered_articles.append(article)
            else:
                logger.debug(f"Filtered out irrelevant article: {article.get('title', '')[:50]}...")

        articles = filtered_articles
        logger.info(f"Filtered {len(articles)} relevant articles for {ticker}")

    # Set ticker for remaining articles
    if ticker and articles:
        for article in articles:
            if not article.get('ticker') or article['ticker'] == '':
                article['ticker'] = ticker

    # Apply sentiment filter if specified
    if sentiment_filter and articles:
        filtered_articles = []
        for article in articles:
            score = article.get('sentiment_analysis', {}).get('overall_score', 0)

            if sentiment_filter == 'positive' and score > 0.1:
                filtered_articles.append(article)
            elif sentiment_filter == 'negative' and score < -0.1:
                filtered_articles.append(article)
            elif sentiment_filter == 'neutral' and -0.1 <= score <= 0.1:
                filtered_articles.append(article)

        articles = filtered_articles

    return articles

# Initialize the service
try:
    init_news_service()
except Exception as e:
    logger.error(f"Failed to initialize news service: {e}")