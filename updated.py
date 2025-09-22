import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import json
import logging
import os
import pickle
from pathlib import Path

# Force PyTorch backend and avoid TensorFlow
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

# Import transformers after setting environment variables
from transformers import pipeline
import torch

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinancialNewsAnalyzer:
    def __init__(self, alpha_vantage_key, finnhub_key, data_dir="financial_data"):
        self.alpha_vantage_key = alpha_vantage_key
        self.finnhub_key = finnhub_key
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.last_run_file = self.data_dir / "last_run.pkl"
        
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
    
    def get_last_run_date(self):
        """Get the last run date from file"""
        if self.last_run_file.exists():
            try:
                with open(self.last_run_file, 'rb') as f:
                    return pickle.load(f)
            except:
                return None
        return None
    
    def save_last_run_date(self, date):
        """Save the last run date to file"""
        with open(self.last_run_file, 'wb') as f:
            pickle.dump(date, f)
    
    def is_first_run(self):
        """Check if this is the first run"""
        return self.get_last_run_date() is None
    
    def get_alpha_vantage_news(self, tickers=None, limit=1000):
        """
        Fetch news from Alpha Vantage API with maximum data extraction
        """
        base_url = "https://www.alphavantage.co/query"
        all_news = []
        
        # For first run, get maximum data; for subsequent runs, get recent data
        if self.is_first_run():
            # First run - get as much as possible
            logger.info("First run detected - fetching maximum historical data...")
            time_from = (datetime.now() - timedelta(days=30)).strftime('%Y%m%dT%H%M')
        else:
            # Subsequent run - only get data since last run
            last_run = self.get_last_run_date()
            if last_run:
                time_from = last_run.strftime('%Y%m%dT%H%M')
                logger.info(f"Getting news since last run: {last_run}")
            else:
                time_from = (datetime.now() - timedelta(days=7)).strftime('%Y%m%dT%H%M')
        
        if tickers:
            # Get news for specific tickers
            for ticker in tickers:
                params = {
                    'function': 'NEWS_SENTIMENT',
                    'tickers': ticker,
                    'time_from': time_from,
                    'limit': limit // len(tickers) if len(tickers) > 1 else limit,
                    'sort': 'LATEST',
                    'apikey': self.alpha_vantage_key
                }
                
                try:
                    response = requests.get(base_url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'feed' in data:
                        for article in data['feed']:
                            news_item = {
                                'date': article.get('time_published', ''),
                                'ticker': ticker,
                                'title': article.get('title', ''),
                                'description': article.get('summary', ''),
                                'url': article.get('url', ''),
                                'source': 'Alpha Vantage',
                                'authors': ', '.join(article.get('authors', [])),
                                'category': article.get('category_within_source', 'general')
                            }
                            all_news.append(news_item)
                    
                    logger.info(f"Retrieved {len(data.get('feed', []))} articles for {ticker} from Alpha Vantage")
                    time.sleep(12)  # Rate limiting for free tier
                    
                except Exception as e:
                    logger.error(f"Error fetching Alpha Vantage news for {ticker}: {e}")
        else:
            # Get general market news
            params = {
                'function': 'NEWS_SENTIMENT',
                'time_from': time_from,
                'limit': limit,
                'sort': 'LATEST',
                'apikey': self.alpha_vantage_key
            }
            
            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if 'feed' in data:
                    for article in data['feed']:
                        # Extract relevant tickers or assign SPX for S&P 500 news
                        relevant_tickers = []
                        if 'ticker_sentiment' in article:
                            relevant_tickers = [item['ticker'] for item in article['ticker_sentiment']]
                        
                        # If no specific ticker, check for S&P 500 keywords
                        title_lower = article.get('title', '').lower()
                        summary_lower = article.get('summary', '').lower()
                        sp500_keywords = ['s&p 500', 'sp500', 'spx', 's&p500', 'market index', 'dow jones', 'nasdaq']
                        
                        if not relevant_tickers:
                            if any(keyword in title_lower or keyword in summary_lower for keyword in sp500_keywords):
                                relevant_tickers = ['SPX']  # Use SPX for S&P 500
                            else:
                                relevant_tickers = ['MARKET']  # General market news
                        
                        for ticker in relevant_tickers:
                            news_item = {
                                'date': article.get('time_published', ''),
                                'ticker': ticker,
                                'title': article.get('title', ''),
                                'description': article.get('summary', ''),
                                'url': article.get('url', ''),
                                'source': 'Alpha Vantage',
                                'authors': ', '.join(article.get('authors', [])),
                                'category': article.get('category_within_source', 'general')
                            }
                            all_news.append(news_item)
                
                logger.info(f"Retrieved {len(data.get('feed', []))} general market articles from Alpha Vantage")
                
            except Exception as e:
                logger.error(f"Error fetching Alpha Vantage general news: {e}")
        
        return all_news
    
    def get_finnhub_news(self, symbol, days_back=None):
        """
        Fetch news from Finnhub API with dynamic date range
        """
        base_url = "https://finnhub.io/api/v1/company-news"
        
        # Determine date range based on first run or subsequent run
        if self.is_first_run():
            days_back = 30  # First run - get 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
        else:
            last_run = self.get_last_run_date()
            if last_run:
                start_date = last_run
                end_date = datetime.now()
            else:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
        
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
                    'source': 'Finnhub',
                    'authors': '',
                    'category': article.get('category', 'general')
                }
                news_items.append(news_item)
            
            logger.info(f"Retrieved {len(news_items)} news items from Finnhub for {symbol}")
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching Finnhub news for {symbol}: {e}")
            return []
    
    def get_comprehensive_sp500_news(self, limit=200):
        """
        Get comprehensive S&P 500 related news from multiple sources
        """
        all_news = []
        
        # S&P 500 related tickers and ETFs
        sp500_related = ['SPY', 'VOO', 'IVV', 'SPXL', 'SPXS', 'SPX']
        
        logger.info("Fetching comprehensive S&P 500 news...")
        
        # Get news from Alpha Vantage for S&P 500 ETFs
        for ticker in sp500_related[:3]:  # Limit to avoid quota exhaustion
            news = self.get_alpha_vantage_news([ticker], limit//len(sp500_related))
            for item in news:
                item['ticker'] = 'SPX'  # Standardize to SPX
            all_news.extend(news)
            time.sleep(12)  # Rate limiting
        
        # Get general market news (will include S&P 500)
        market_news = self.get_alpha_vantage_news(None, limit//2)
        all_news.extend(market_news)
        
        # Get news from Finnhub for major S&P 500 ETF
        fh_news = self.get_finnhub_news('SPY')
        for item in fh_news:
            item['ticker'] = 'SPX'  # Standardize to SPX
        all_news.extend(fh_news)
        
        return all_news
    
    def analyze_sentiment_finbert(self, text):
        """
        Analyze sentiment using FinBERT or fallback model
        """
        try:
            # Truncate text if too long
            max_length = 512
            if len(text) > max_length:
                text = text[:max_length]
            
            result = self.sentiment_analyzer(text)[0]
            
            # Handle different model outputs
            label = result['label'].lower()
            confidence = result['score']
            
            # Map different label formats to our standard
            if 'positive' in label or label == 'label_2':
                sentiment = 'positive'
                score = confidence * 0.67 + 0.33  # Scale to 0.33 to 1
            elif 'negative' in label or label == 'label_0':
                sentiment = 'negative'
                score = -(confidence * 0.67 + 0.33)  # Scale to -1 to -0.33
            else:  # neutral or label_1
                sentiment = 'neutral'
                score = (confidence - 0.5) * 0.66  # Scale to -0.33 to 0.33
            
            return sentiment, round(score, 3)
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return 'neutral', 0.0
    
    def process_news_data(self, news_data):
        """
        Process news data and add sentiment analysis
        """
        processed_data = []
        
        logger.info(f"Starting sentiment analysis for {len(news_data)} articles...")
        
        for i, news in enumerate(news_data):
            if i % 10 == 0:
                logger.info(f"Processing article {i+1}/{len(news_data)}")
            
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
                'authors': news.get('authors', ''),
                'category': news.get('category', 'general'),
                'sentiment': sentiment,
                'sentiment_score': score
            }
            
            processed_data.append(processed_record)
            
            # Small delay to prevent overwhelming the system
            if i % 50 == 0 and i > 0:
                time.sleep(1)
        
        return processed_data
    
    def remove_duplicates(self, news_data):
        """
        Remove duplicate news articles based on title similarity
        """
        seen_titles = set()
        unique_news = []
        
        for news in news_data:
            title_key = news['title'].lower().strip()
            if title_key not in seen_titles and title_key:
                seen_titles.add(title_key)
                unique_news.append(news)
        
        logger.info(f"Removed {len(news_data) - len(unique_news)} duplicate articles")
        return unique_news
    
    def save_to_excel(self, data, filename=None):
        """
        Save processed data to Excel file with enhanced formatting
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = self.data_dir / f"financial_news_sentiment_{timestamp}.xlsx"
        
        df = pd.DataFrame(data)
        
        if df.empty:
            logger.warning("No data to save!")
            return df
        
        # Format date column
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%dT%H%M%S', errors='coerce')
        df = df.sort_values('date', ascending=False)
        
        # Reorder columns
        column_order = ['date', 'ticker', 'title', 'description', 'sentiment', 'sentiment_score', 
                       'url', 'source', 'authors', 'category']
        df = df.reindex(columns=column_order)
        
        # Save to Excel with multiple sheets
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Main sheet with all data
            df.to_excel(writer, sheet_name='All_News', index=False)
            
            # Separate sheets by ticker
            tickers = df['ticker'].unique()
            for ticker in tickers[:10]:  # Limit to prevent too many sheets
                ticker_df = df[df['ticker'] == ticker]
                if len(ticker_df) > 0:
                    sheet_name = ticker.replace('/', '_')[:31]  # Excel sheet name limit
                    ticker_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Summary sheet
            summary_data = {
                'Metric': ['Total Articles', 'Positive Sentiment', 'Negative Sentiment', 'Neutral Sentiment',
                          'Unique Tickers', 'Date Range From', 'Date Range To', 'Last Updated'],
                'Value': [
                    len(df),
                    len(df[df['sentiment'] == 'positive']),
                    len(df[df['sentiment'] == 'negative']),
                    len(df[df['sentiment'] == 'neutral']),
                    len(df['ticker'].unique()),
                    df['date'].min(),
                    df['date'].max(),
                    datetime.now()
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Format all worksheets
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 80)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        logger.info(f"Data saved to {filename}")
        return df

def main():
    # Configuration
    ALPHA_VANTAGE_KEY = "D8UW6Y3OJAB4FZIH"  # Replace with your key
    FINNHUB_KEY = "d34fdbpr01qqt8sos93gd34fdbpr01qqt8sos940"  # Replace with your key
    
    # Comprehensive list of stocks to track
    STOCKS_TO_TRACK = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META', 'NFLX', 'JPM', 'V']
    
    # Initialize analyzer
    analyzer = FinancialNewsAnalyzer(ALPHA_VANTAGE_KEY, FINNHUB_KEY)
    
    all_news = []
    
    try:
        current_time = datetime.now()
        is_first_run = analyzer.is_first_run()
        
        if is_first_run:
            logger.info("🚀 FIRST RUN - Collecting maximum historical data (30 days)")
            max_articles_per_stock = 50  # More articles for first run
        else:
            logger.info("🔄 WEEKLY UPDATE - Collecting news since last run")
            max_articles_per_stock = 20  # Fewer articles for updates
        
        # Get comprehensive S&P 500 news
        logger.info("📊 Fetching S&P 500 and market news...")
        sp500_news = analyzer.get_comprehensive_sp500_news(limit=100 if is_first_run else 30)
        all_news.extend(sp500_news)
        
        # Get individual stock news
        total_stocks = len(STOCKS_TO_TRACK)
        for i, stock in enumerate(STOCKS_TO_TRACK):
            logger.info(f"📈 Fetching news for {stock} ({i+1}/{total_stocks})")
            
            try:
                # Get from Alpha Vantage
                av_news = analyzer.get_alpha_vantage_news([stock], limit=max_articles_per_stock)
                all_news.extend(av_news)
                
                # Get from Finnhub
                time.sleep(1)  # Brief pause
                fh_news = analyzer.get_finnhub_news(stock)
                all_news.extend(fh_news)
                
                # Rate limiting for API quotas
                time.sleep(12 if i < total_stocks - 1 else 0)  # No delay after last stock
                
            except Exception as e:
                logger.error(f"Error fetching news for {stock}: {e}")
                continue
        
        logger.info(f"📰 Collected {len(all_news)} total articles")
        
        # Remove duplicates
        unique_news = analyzer.remove_duplicates(all_news)
        logger.info(f"📝 Processing {len(unique_news)} unique articles")
        
        if not unique_news:
            logger.warning("No news articles found!")
            return None
        
        # Process news and add sentiment analysis
        logger.info("🤖 Starting sentiment analysis...")
        processed_data = analyzer.process_news_data(unique_news)
        
        # Save to Excel
        df = analyzer.save_to_excel(processed_data)
        
        # Update last run date
        analyzer.save_last_run_date(current_time)
        
        # Print comprehensive summary
        print("\n" + "="*60)
        print("📊 FINANCIAL NEWS ANALYSIS COMPLETE")
        print("="*60)
        print(f"📅 Analysis Date: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 Run Type: {'First Run (Historical)' if is_first_run else 'Weekly Update'}")
        print(f"📰 Total Articles: {len(processed_data)}")
        print(f"📈 Positive Sentiment: {len(df[df['sentiment'] == 'positive'])} ({len(df[df['sentiment'] == 'positive'])/len(df)*100:.1f}%)")
        print(f"📉 Negative Sentiment: {len(df[df['sentiment'] == 'negative'])} ({len(df[df['sentiment'] == 'negative'])/len(df)*100:.1f}%)")
        print(f"⚖️  Neutral Sentiment: {len(df[df['sentiment'] == 'neutral'])} ({len(df[df['sentiment'] == 'neutral'])/len(df)*100:.1f}%)")
        print(f"🏢 Unique Tickers: {len(df['ticker'].unique())}")
        print(f"📊 S&P 500 Articles: {len(df[df['ticker'] == 'SPX'])}")
        print(f"📂 Data Range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
        
        # Top sentiment scores
        top_positive = df.nlargest(3, 'sentiment_score')[['ticker', 'title', 'sentiment_score']]
        top_negative = df.nsmallest(3, 'sentiment_score')[['ticker', 'title', 'sentiment_score']]
        
        print("\n🌟 Most Positive News:")
        for _, row in top_positive.iterrows():
            print(f"   {row['ticker']}: {row['title'][:60]}... (Score: {row['sentiment_score']})")
        
        print("\n⚠️  Most Negative News:")
        for _, row in top_negative.iterrows():
            print(f"   {row['ticker']}: {row['title'][:60]}... (Score: {row['sentiment_score']})")
        
        print("\n💾 Data saved to Excel with multiple sheets:")
        print("   • All_News: Complete dataset")
        print("   • Individual ticker sheets")
        print("   • Summary: Analysis overview")
        
        if not is_first_run:
            print(f"\n⏰ Next run recommended: {(current_time + timedelta(days=7)).strftime('%Y-%m-%d')}")
        
        print("="*60)
        
        return df
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        return None

if __name__ == "__main__":
    # Run the analysis
    result = main()