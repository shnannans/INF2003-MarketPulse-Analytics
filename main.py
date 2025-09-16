import requests
import pandas as pd
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
    
    def save_to_excel(self, data, filename):
        """
        Save processed data to Excel file
        """
        df = pd.DataFrame(data)
        
        # Format date column
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%dT%H%M%S', errors='coerce')
            df = df.sort_values('date', ascending=False)
        
        # Reorder columns
        column_order = ['date', 'ticker', 'title', 'description', 'sentiment', 'sentiment_score', 'url', 'source']
        df = df.reindex(columns=column_order)
        
        # Save to Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Financial_News', index=False)
            
            # Format the worksheet
            worksheet = writer.sheets['Financial_News']
            
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
        
        logger.info(f"Data saved to {filename}")
        return df

def main():
    # Configuration
    ALPHA_VANTAGE_KEY = "D8UW6Y3OJAB4FZIH"  # Replace with your key
    FINNHUB_KEY = "d34fdbpr01qqt8sos93gd34fdbpr01qqt8sos940"  # Replace with your key
    
    # Stocks to track (you can modify this list)
    STOCKS_TO_TRACK = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META', 'NFLX', 'JPM', 'V']
    # Initialize analyzer
    analyzer = FinancialNewsAnalyzer(ALPHA_VANTAGE_KEY, FINNHUB_KEY)
    
    all_news = []
    
    try:
        # Get S&P 500 news
        logger.info("Fetching S&P 500 news...")
        sp500_news = analyzer.get_sp500_news(limit=30)
        all_news.extend(sp500_news)
        
        # Get individual stock news
        for stock in STOCKS_TO_TRACK:
            logger.info(f"Fetching news for {stock}...")
            
            # Get from Alpha Vantage
            av_news = analyzer.get_alpha_vantage_news([stock], limit=10)
            all_news.extend(av_news)
            
            # Get from Finnhub (with rate limiting)
            time.sleep(1)
            fh_news = analyzer.get_finnhub_news(stock, days_back=7)
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
        processed_data = analyzer.process_news_data(unique_news)
        
        # Save to Excel
        filename = f"financial_news_sentiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df = analyzer.save_to_excel(processed_data, filename)
        
        # Print summary
        print(f"\n=== SUMMARY ===")
        print(f"Total articles processed: {len(processed_data)}")
        print(f"Positive sentiment: {len(df[df['sentiment'] == 'positive'])}")
        print(f"Negative sentiment: {len(df[df['sentiment'] == 'negative'])}")
        print(f"Neutral sentiment: {len(df[df['sentiment'] == 'neutral'])}")
        print(f"Data saved to: {filename}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return None

if __name__ == "__main__":
    # Run the analysis
    result = main()