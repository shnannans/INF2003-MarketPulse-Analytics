# pip install yfinance pandas openpyxl requests transformers torch

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import json
import logging
import os

# Force PyTorch backend and avoid TensorFlow
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# Import transformers after setting environment variables
from transformers import pipeline
import torch

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialNewsAnalyzer:
    def __init__(self, alpha_vantage_key, finnhub_key):
        self.alpha_vantage_key = alpha_vantage_key
        self.finnhub_key = finnhub_key
        
        # Initialize FinBERT for sentiment analysis (PyTorch only)
        logger.info("Loading FinBERT model...")
        try:
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
                framework="pt",  # Force PyTorch
                device=-1  # Use CPU (change to 0 for GPU if available)
            )
            logger.info("FinBERT model loaded successfully!")
        except Exception as e:
            logger.error(f"Error loading FinBERT: {e}")
            # Fallback to a simpler sentiment model if FinBERT fails
            logger.info("Falling back to cardiffnlp/twitter-roberta-base-sentiment-latest...")
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                framework="pt",
                device=-1
            )
        
    def get_alpha_vantage_news(self, tickers=None, limit=50):
        """
        Fetch news from Alpha Vantage API
        """
        base_url = "https://www.alphavantage.co/query"
        
        all_news = []
        
        if tickers:
            # Get news for specific tickers
            tickers_str = ",".join(tickers)
            params = {
                'function': 'NEWS_SENTIMENT',
                'tickers': tickers_str,
                'limit': limit,
                'apikey': self.alpha_vantage_key
            }
        else:
            # Get general market news
            params = {
                'function': 'NEWS_SENTIMENT',
                'limit': limit,
                'apikey': self.alpha_vantage_key
            }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'feed' in data:
                for article in data['feed']:
                    # Extract relevant tickers
                    relevant_tickers = []
                    if 'ticker_sentiment' in article:
                        relevant_tickers = [item['ticker'] for item in article['ticker_sentiment']]
                    
                    # Handle cases where no specific ticker is mentioned (market news)
                    if not relevant_tickers and not tickers:
                        relevant_tickers = ['MARKET']  # General market news
                    
                    for ticker in relevant_tickers or ['UNKNOWN']:
                        news_item = {
                            'date': article.get('time_published', ''),
                            'ticker': ticker,
                            'title': article.get('title', ''),
                            'description': article.get('summary', ''),
                            'url': article.get('url', ''),
                            'source': 'Alpha Vantage'
                        }
                        all_news.append(news_item)
            
            logger.info(f"Retrieved {len(all_news)} news items from Alpha Vantage")
            return all_news
            
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage news: {e}")
            return []
    
    def get_finnhub_news(self, symbol, days_back=7):
        """
        Fetch news from Finnhub API
        """
        base_url = "https://finnhub.io/api/v1/company-news"
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        params = {
            'symbol': symbol,
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'token': self.finnhub_key
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            articles = response.json()
            
            news_items = []
            for article in articles:
                news_item = {
                    'date': datetime.fromtimestamp(article.get('datetime', 0)).strftime('%Y%m%dT%H%M%S'),
                    'ticker': symbol,
                    'title': article.get('headline', ''),
                    'description': article.get('summary', ''),
                    'url': article.get('url', ''),
                    'source': 'Finnhub'
                }
                news_items.append(news_item)
            
            logger.info(f"Retrieved {len(news_items)} news items from Finnhub for {symbol}")
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching Finnhub news for {symbol}: {e}")
            return []
    
    def analyze_sentiment_finbert(self, text):
        """
        Analyze sentiment using FinBERT
        """
        try:
            # Truncate text if too long (FinBERT has token limits)
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            result = self.sentiment_analyzer(text)[0]
            
            # Map FinBERT labels to our format
            label_mapping = {
                'positive': 'positive',
                'negative': 'negative',
                'neutral': 'neutral'
            }
            
            sentiment = label_mapping.get(result['label'].lower(), 'neutral')
            confidence = result['score']
            
            # Convert to our scoring system (-1 to 1)
            if sentiment == 'positive':
                score = confidence * 0.67 + 0.33  # Scale to 0.33 to 1
            elif sentiment == 'negative':
                score = -(confidence * 0.67 + 0.33)  # Scale to -1 to -0.33
            else:
                score = (confidence - 0.5) * 0.66  # Scale to -0.33 to 0.33
            
            return sentiment, round(score, 3)
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return 'neutral', 0.0
    
    def get_sp500_news(self, limit=50):
        """
        Get S&P 500 related news
        """
        # Major S&P 500 ETFs and index-related tickers
        sp500_tickers = ['SPY', 'VOO', 'IVV']
        
        all_news = []
        
        # Get news from Alpha Vantage for S&P 500
        for ticker in sp500_tickers:
            news = self.get_alpha_vantage_news([ticker], limit//len(sp500_tickers))
            all_news.extend(news)
            time.sleep(12)  # Rate limiting for free tier
        
        # Also get general market news
        market_news = self.get_alpha_vantage_news(None, limit//2)
        all_news.extend(market_news)
        
        return all_news
    
    def process_news_data(self, news_data):
        """
        Process news data and add sentiment analysis
        """
        processed_data = []
        
        for i, news in enumerate(news_data):
            logger.info(f"Processing article {i+1}/{len(news_data)}: {news['title'][:50]}...")
            
            # Combine title and description for better sentiment analysis
            text_for_analysis = f"{news['title']} {news['description']}"
            
            # Analyze sentiment
            sentiment, score = self.analyze_sentiment_finbert(text_for_analysis)
            
            # Create processed record
            processed_record = {
                'date': news['date'],
                'ticker': news['ticker'],
                'title': news['title'],
                'description': news['description'],
                'url': news.get('url', ''),
                'source': news['source'],
                'sentiment': sentiment,
                'sentiment_score': score
            }
            
            processed_data.append(processed_record)
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.1)
        
        return processed_data

# -------------------------------
# 1 Stocks & Indices Setup
# -------------------------------
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
           "NVDA", "META", "NFLX", "JPM", "V"]  # 10 tickers
indices = {"^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "NASDAQ"}  # Yahoo Finance symbols

# API Keys - Replace with your actual keys
ALPHA_VANTAGE_KEY = "D8UW6Y3OJAB4FZIH"  # Replace with your key
FINNHUB_KEY = "d34fdbpr01qqt8sos93gd34fdbpr01qqt8sos940"  # Replace with your key

# -------------------------------
# 2 Fetch Stock Historical Prices
# -------------------------------
all_stock_data = []

for ticker in tickers:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="max")
        hist = hist.reset_index()
        hist['Ticker'] = ticker
        hist['Date'] = pd.to_datetime(hist['Date']).dt.tz_localize(None)  # remove timezone
        all_stock_data.append(hist)
    except Exception as e:
        print(f"Error fetching stock data for {ticker}: {e}")

stock_df = pd.concat(all_stock_data, ignore_index=True)
print("✅ Stock prices collected")

# -------------------------------
# 3 Fetch Company Fundamentals
# -------------------------------
all_fundamentals = []

for ticker in tickers:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        all_fundamentals.append({
            "Ticker": ticker,
            "Sector": info.get("sector", ""),
            "Industry": info.get("industry", ""),
            "MarketCap": info.get("marketCap", ""),
            "PE_Ratio": info.get("trailingPE", ""),
            "DividendYield": info.get("dividendYield", "")
        })
    except Exception as e:
        print(f"Error fetching fundamentals for {ticker}: {e}")

fundamentals_df = pd.DataFrame(all_fundamentals)
print("✅ Company fundamentals collected")

# -------------------------------
# 4 Fetch Market Indices
# -------------------------------
all_index_data = []

for symbol, name in indices.items():
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="max")
        hist = hist.reset_index()
        hist['Index'] = name
        hist['Date'] = pd.to_datetime(hist['Date']).dt.tz_localize(None)
        all_index_data.append(hist)
    except Exception as e:
        print(f"Error fetching index data for {symbol}: {e}")

indices_df = pd.concat(all_index_data, ignore_index=True)
print("✅ Market indices collected")

# -------------------------------
# 5 Advanced Financial News Collection & Sentiment Analysis
# -------------------------------
print("🔄 Starting advanced news collection and sentiment analysis...")

# Initialize the news analyzer
news_analyzer = FinancialNewsAnalyzer(ALPHA_VANTAGE_KEY, FINNHUB_KEY)

all_news = []

try:
    # Get S&P 500 news
    logger.info("Fetching S&P 500 news...")
    sp500_news = news_analyzer.get_sp500_news(limit=30)
    all_news.extend(sp500_news)
    
    # Get individual stock news
    for stock in tickers:
        logger.info(f"Fetching news for {stock}...")
        
        # Get from Alpha Vantage
        av_news = news_analyzer.get_alpha_vantage_news([stock], limit=10)
        all_news.extend(av_news)
        
        # Get from Finnhub (with rate limiting)
        time.sleep(1)
        fh_news = news_analyzer.get_finnhub_news(stock, days_back=7)
        all_news.extend(fh_news)
        
        # Rate limiting for free tiers
        time.sleep(12)  # Alpha Vantage rate limit
    
    # Remove duplicates based on title
    seen_titles = set()
    unique_news = []
    for news in all_news:
        if news['title'] not in seen_titles:
            seen_titles.add(news['title'])
            unique_news.append(news)
    
    logger.info(f"Total unique news articles: {len(unique_news)}")
    
    # Process news and add sentiment analysis
    logger.info("Starting sentiment analysis...")
    processed_news_data = news_analyzer.process_news_data(unique_news)
    
    # Convert to DataFrame
    news_sentiment_df = pd.DataFrame(processed_news_data)
    
    # Format date column
    if not news_sentiment_df.empty and 'date' in news_sentiment_df.columns:
        news_sentiment_df['date'] = pd.to_datetime(news_sentiment_df['date'], format='%Y%m%dT%H%M%S', errors='coerce')
        news_sentiment_df = news_sentiment_df.sort_values('date', ascending=False)
    
    print("✅ Advanced news sentiment analysis complete")
    
    # Print summary
    print(f"\n=== NEWS SENTIMENT SUMMARY ===")
    print(f"Total articles processed: {len(processed_news_data)}")
    if not news_sentiment_df.empty:
        print(f"Positive sentiment: {len(news_sentiment_df[news_sentiment_df['sentiment'] == 'positive'])}")
        print(f"Negative sentiment: {len(news_sentiment_df[news_sentiment_df['sentiment'] == 'negative'])}")
        print(f"Neutral sentiment: {len(news_sentiment_df[news_sentiment_df['sentiment'] == 'neutral'])}")
    
except Exception as e:
    logger.error(f"Error in news collection and analysis: {e}")
    # Create empty DataFrame as fallback
    news_sentiment_df = pd.DataFrame(columns=['date', 'ticker', 'title', 'description', 'sentiment', 'sentiment_score', 'url', 'source'])
    print("⚠️ Using empty news DataFrame due to errors")

# -------------------------------
# 6 Save All Data to Excel
# -------------------------------
filename = f"Enhanced_FinancialData_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

with pd.ExcelWriter(filename, engine="openpyxl") as writer:
    stock_df.to_excel(writer, sheet_name="Stock_Prices", index=False)
    fundamentals_df.to_excel(writer, sheet_name="Company_Fundamentals", index=False)
    indices_df.to_excel(writer, sheet_name="Market_Indices", index=False)
    news_sentiment_df.to_excel(writer, sheet_name="Financial_News_Advanced", index=False)
    
    # Format the news worksheet
    if 'Financial_News_Advanced' in writer.sheets:
        worksheet = writer.sheets['Financial_News_Advanced']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
            worksheet.column_dimensions[column_letter].width = adjusted_width

print(f"✅ All data collected and saved to {filename}")
print(f"📊 Enhanced financial data collection complete with advanced news sentiment analysis!")