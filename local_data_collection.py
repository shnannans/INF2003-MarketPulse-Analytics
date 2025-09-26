#!/usr/bin/env python3
"""
Frontend-Integrated Financial Data Collection Script
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
import mysql.connector
from pymongo import MongoClient
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('comprehensive_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FrontendIntegratedCollector:
    def __init__(self):
        self.mysql_config = {
            "host": "34.133.0.30",
            "user": "root",
            "password": "Password123@",
            "port": 3306
        }
        
        self.mongo_config = {
            "host": "localhost",
            "port": 27017,
            "database": "financial_db",
            "collection": "financial_news"
        }
        
        self.mysql_conn = None
        self.mongo_collection = None
        
        # Your existing comprehensive stock list
        self.major_stocks = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ',
            'WMT', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'BAC', 'ADBE', 'CRM',
            'NFLX', 'NKE', 'TMO', 'ABT', 'COST', 'PFE', 'AVGO', 'XOM', 'CVX', 'KO',
            'PEP', 'INTC', 'CSCO', 'VZ', 'MRK', 'T', 'DHR', 'TXN', 'LLY', 'ACN',
            'HON', 'MDT', 'UPS', 'QCOM', 'IBM', 'BMY', 'NEE', 'SBUX', 'AMT', 'LOW'
        ]
        
        self.market_indices = {
            '^GSPC': 'S&P 500',
            '^DJI': 'Dow Jones',
            '^IXIC': 'NASDAQ'
        }
        
        self.sectors = {
            'XLK': 'Technology',
            'XLF': 'Financials', 
            'XLE': 'Energy',
            'XLV': 'Healthcare',
            'XLI': 'Industrials',
            'XLP': 'Consumer Staples',
            'XLY': 'Consumer Discretionary',
            'XLU': 'Utilities',
            'XLB': 'Materials',
            'XLRE': 'Real Estate',
            'XLC': 'Communication Services'
        }

    def create_mysql_database(self):
        """Create MySQL database if it doesn't exist"""
        try:
            conn = mysql.connector.connect(
                host=self.mysql_config['host'],
                user=self.mysql_config['user'],
                password=self.mysql_config['password'],
                port=self.mysql_config['port'],
                auth_plugin='mysql_native_password'
            )
            cursor = conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS databaseproj")
            logger.info("MySQL database 'databaseproj' created/verified")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error creating MySQL database: {e}")
            return False

    def connect_databases(self):
        """Connect to both databases"""
        try:
            mysql_config = self.mysql_config.copy()
            mysql_config['database'] = 'databaseproj'
            # Ensure native password plugin is used
            self.mysql_conn = mysql.connector.connect(
                host=mysql_config['host'],
                user=mysql_config['user'],
                password=mysql_config['password'],
                port=mysql_config['port'],
                database=mysql_config['database'],
                auth_plugin='mysql_native_password'
            )
            logger.info("Connected to MySQL database: databaseproj")
            
            mongo_client = MongoClient(f"mongodb://{self.mongo_config['host']}:{self.mongo_config['port']}/")
            mongo_db = mongo_client[self.mongo_config['database']]
            self.mongo_collection = mongo_db[self.mongo_config['collection']]
            mongo_client.server_info()
            logger.info("Connected to MongoDB database: databaseproj")
            
            return True
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False

    def create_enhanced_mysql_tables(self):
        """Create all MySQL tables needed for the dashboard"""
        cursor = self.mysql_conn.cursor()
        
        try:
            # Companies table (your existing structure + missing columns)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                ticker VARCHAR(10) PRIMARY KEY,
                company_name VARCHAR(255),
                sector VARCHAR(100),
                industry VARCHAR(150),
                market_cap BIGINT,
                employees INTEGER,
                exchange VARCHAR(20),
                currency VARCHAR(10),
                country VARCHAR(50),
                website VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Enhanced stock prices (your existing structure + missing moving averages)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                date DATE NOT NULL,
                open_price DECIMAL(12,4),
                high_price DECIMAL(12,4),
                low_price DECIMAL(12,4),
                close_price DECIMAL(12,4),
                adj_close DECIMAL(12,4),
                volume BIGINT,
                ma_5 DECIMAL(12,4),
                ma_20 DECIMAL(12,4),
                ma_50 DECIMAL(12,4),
                ma_200 DECIMAL(12,4),
                price_change_pct DECIMAL(8,4),
                volume_change_pct DECIMAL(8,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_ticker_date (ticker, date),
                INDEX idx_ticker_date (ticker, date),
                INDEX idx_date (date)
            )
            """)
            
            # Financial metrics table (REQUIRED by your PHP get_companies.php)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_metrics (
                ticker VARCHAR(10) PRIMARY KEY,
                pe_ratio DECIMAL(8,2),
                dividend_yield DECIMAL(6,4),
                market_cap BIGINT,
                beta DECIMAL(6,4),
                forward_pe DECIMAL(8,2),
                price_to_book DECIMAL(8,4),
                debt_to_equity DECIMAL(8,4),
                return_on_equity DECIMAL(8,6),
                profit_margin DECIMAL(8,6),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """)
            
            # Market indices table (your existing structure)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_indices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL,
                index_name VARCHAR(100),
                date DATE NOT NULL,
                open_price DECIMAL(12,4),
                high_price DECIMAL(12,4),
                low_price DECIMAL(12,4),
                close_price DECIMAL(12,4),
                volume BIGINT,
                change_pct DECIMAL(8,4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_symbol_date (symbol, date),
                INDEX idx_symbol_date (symbol, date)
            )
            """)
            
            # Sector performance table (your existing structure)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sector_performance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sector_name VARCHAR(100),
                sector_etf VARCHAR(10),
                date DATE,
                close_price DECIMAL(12,4),
                change_pct DECIMAL(8,4),
                volume BIGINT,
                avg_sentiment DECIMAL(6,4),
                article_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_sector_date (sector_name, date),
                INDEX idx_sector_date (sector_name, date)
            )
            """)
            
            # Portfolio tracking table (your existing structure)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                shares DECIMAL(15,6),
                avg_cost DECIMAL(12,4),
                current_price DECIMAL(12,4),
                market_value DECIMAL(15,2),
                unrealized_pnl DECIMAL(15,2),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_ticker (ticker)
            )
            """)
            
            self.mysql_conn.commit()
            cursor.close()
            logger.info("Enhanced MySQL tables created successfully")
            
        except Exception as e:
            logger.error(f"Error creating enhanced tables: {e}")
            raise

    def calculate_simple_indicators(self, df):
        """Calculate simple technical indicators (UPDATED to include ma_200)"""
        try:
            # Moving averages (added ma_200 for PHP compatibility)
            df['ma_5'] = df['Close'].rolling(window=5).mean()
            df['ma_20'] = df['Close'].rolling(window=20).mean()  
            df['ma_50'] = df['Close'].rolling(window=50).mean()
            df['ma_200'] = df['Close'].rolling(window=200).mean()  # ADDED
            
            # Price and volume change percentages
            df['price_change_pct'] = df['Close'].pct_change() * 100
            df['volume_change_pct'] = df['Volume'].pct_change() * 100
            
            return df
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df
        
    def collect_market_indices(self):
        """Collect market indices data (your existing method)"""
        cursor = self.mysql_conn.cursor()
        
        for symbol, name in self.market_indices.items():
            try:
                logger.info(f"Collecting index data for {name}")
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="120d")
                
                prev_close = None
                for date, row in hist.iterrows():
                    change_pct = 0
                    if prev_close is not None:
                        change_pct = ((row['Close'] - prev_close) / prev_close * 100)
                    
                    cursor.execute("""
                    REPLACE INTO market_indices (symbol, index_name, date, open_price, high_price, 
                                               low_price, close_price, volume, change_pct)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        symbol, name, date.date(), float(row['Open']), float(row['High']),
                        float(row['Low']), float(row['Close']), int(row['Volume']), change_pct
                    ))
                    
                    prev_close = row['Close']
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error collecting index data for {symbol}: {e}")
        
        self.mysql_conn.commit()
        cursor.close()
        logger.info("Market indices collection completed")

    def collect_enhanced_stock_data(self, tickers):
        """Collect enhanced stock data with technical indicators (UPDATED)"""
        cursor = self.mysql_conn.cursor()
        
        for ticker in tickers:
            try:
                logger.info(f"Collecting enhanced data for {ticker}")
                stock = yf.Ticker(ticker)
                
                # Get company info
                info = stock.info
                cursor.execute("""
                REPLACE INTO companies (ticker, company_name, sector, industry, market_cap, 
                                     employees, exchange, currency, country, website)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    ticker, info.get('longName', ticker), info.get('sector', ''),
                    info.get('industry', ''), info.get('marketCap', 0),
                    info.get('fullTimeEmployees', 0), info.get('exchange', ''),
                    info.get('currency', 'USD'), info.get('country', ''),
                    info.get('website', '')
                ))
                
                # Insert financial metrics (REQUIRED for get_companies.php)
                cursor.execute("""
                REPLACE INTO financial_metrics (
                    ticker, pe_ratio, dividend_yield, market_cap, beta, 
                    forward_pe, price_to_book, debt_to_equity, return_on_equity, profit_margin
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    ticker,
                    info.get('trailingPE', None),
                    info.get('dividendYield', None),
                    info.get('marketCap', None),
                    info.get('beta', None),
                    info.get('forwardPE', None),
                    info.get('priceToBook', None),
                    info.get('debtToEquity', None),
                    info.get('returnOnEquity', None),
                    info.get('profitMargins', None)
                ))
                
                # Get historical data (your existing logic)
                hist = stock.history(period="1y")  
                if hist.empty:
                    logger.warning(f"No data for {ticker}")
                    continue
                
                # Calculate technical indicators (now includes ma_200)
                hist = self.calculate_simple_indicators(hist)
                
                # Insert price data with indicators (UPDATED to include ma_200)
                for date, row in hist.iterrows():
                    try:
                        cursor.execute("""
                        REPLACE INTO stock_prices (
                            ticker, date, open_price, high_price, low_price, close_price, 
                            adj_close, volume, ma_5, ma_20, ma_50, ma_200,
                            price_change_pct, volume_change_pct
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            ticker, date.date(), float(row['Open']), float(row['High']),
                            float(row['Low']), float(row['Close']), float(row['Close']),
                            int(row['Volume']), 
                            float(row['ma_5']) if pd.notna(row['ma_5']) else None,
                            float(row['ma_20']) if pd.notna(row['ma_20']) else None,
                            float(row['ma_50']) if pd.notna(row['ma_50']) else None,
                            float(row['ma_200']) if pd.notna(row['ma_200']) else None,  # ADDED
                            float(row['price_change_pct']) if pd.notna(row['price_change_pct']) else None,
                            float(row['volume_change_pct']) if pd.notna(row['volume_change_pct']) else None
                        ))
                    except Exception as e:
                        logger.error(f"Error inserting price data for {ticker} on {date}: {e}")
                        continue
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error collecting enhanced data for {ticker}: {e}")
        
        self.mysql_conn.commit()
        cursor.close()
        logger.info("Enhanced stock data collection completed")

    def collect_sector_performance(self):
        """Collect sector ETF performance data (your existing method)"""
        cursor = self.mysql_conn.cursor()
        
        for etf, sector in self.sectors.items():
            try:
                logger.info(f"Collecting sector data for {sector}")
                ticker = yf.Ticker(etf)
                hist = ticker.history(period="120d")
                
                prev_close = None
                for date, row in hist.iterrows():
                    change_pct = 0
                    if prev_close is not None:
                        change_pct = ((row['Close'] - prev_close) / prev_close * 100)
                    
                    # Mock sentiment data
                    avg_sentiment = (hash(f"{etf}{date}") % 100) / 500.0 - 0.1
                    article_count = hash(f"{sector}{date}") % 20 + 5
                    
                    cursor.execute("""
                    REPLACE INTO sector_performance (sector_name, sector_etf, date, close_price, 
                                                   change_pct, volume, avg_sentiment, article_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        sector, etf, date.date(), float(row['Close']), change_pct,
                        int(row['Volume']), avg_sentiment, article_count
                    ))
                    
                    prev_close = row['Close']
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error collecting sector data for {etf}: {e}")
        
        self.mysql_conn.commit()
        cursor.close()
        logger.info("Sector performance collection completed")

    def generate_comprehensive_news(self, tickers):
        """Generate comprehensive news data with variety (your existing method)"""
        news_articles = []
        
        sources = ['Reuters', 'Bloomberg', 'MarketWatch', 'CNBC', 'Wall Street Journal', 'Financial Times']
        categories = ['earnings_report', 'analyst_report', 'market_analysis', 'corporate_news', 'regulatory_news']
        
        for ticker in tickers:
            # Generate 20 articles per ticker (your existing logic)
            for i in range(20):
                sentiment_base = (hash(f"{ticker}{i}") % 200) / 100.0 - 1.0
                source = sources[hash(f"{ticker}{i}") % len(sources)]
                category = categories[hash(f"{ticker}{i}source") % len(categories)]
                
                if sentiment_base > 0.1:
                    sentiment_label = 'positive'
                    keywords = ['growth', 'strong', 'exceeds', 'bullish', 'upgrade']
                elif sentiment_base < -0.1:
                    sentiment_label = 'negative'
                    keywords = ['decline', 'weak', 'concern', 'bearish', 'downgrade']
                else:
                    sentiment_label = 'neutral'
                    keywords = ['stable', 'mixed', 'unchanged', 'sideways', 'neutral']
                
                article = {
                    'ticker': ticker,
                    'title': f'{ticker} {category.replace("_", " ").title()}: {sentiment_label.title()} Market Response',
                    'content': f'Analysis of {ticker} shows {sentiment_label} indicators in recent {category.replace("_", " ")} developments. Market factors suggest {", ".join(keywords[:3])} trends affecting overall performance and investor sentiment.',
                    'published_date': datetime.now() - timedelta(days=(i+1), hours=hash(f"{ticker}{i}hours") % 24),
                    'source': {
                        'name': source,
                        'credibility_score': 0.85 + (hash(source) % 15) / 100.0
                    },
                    'sentiment_analysis': {
                        'overall_score': sentiment_base,
                        'confidence': 0.7 + (hash(f"{ticker}conf{i}") % 25) / 100.0,
                        'positive_keywords': keywords if sentiment_label == 'positive' else [],
                        'negative_keywords': keywords if sentiment_label == 'negative' else [],
                        'neutral_keywords': keywords if sentiment_label == 'neutral' else []
                    },
                    'extracted_entities': {
                        'companies': [ticker],
                        'people': [f'CEO of {ticker}', f'Analyst {(i%3)+1}'],
                        'financial_terms': keywords,
                        'tickers': [ticker]
                    },
                    'metadata': {
                        'word_count': 250 + (hash(f"{ticker}{i}words") % 300),
                        'reading_time_minutes': 2.0 + (hash(f"{ticker}{i}time") % 20) / 10.0,
                        'article_category': category,
                        'market_hours': (hash(f"{ticker}{i}market") % 2) == 1,
                        'social_shares': hash(f"{ticker}{i}shares") % 500,
                        'engagement_score': (hash(f"{ticker}{i}engage") % 100) / 100.0
                    },
                    'processing_timestamps': {
                        'collected_at': datetime.utcnow(),
                        'sentiment_processed_at': datetime.utcnow(),
                        'indexed_at': datetime.utcnow()
                    },
                    'article_id': f'{ticker}_{category}_{i}_{int(time.time())}_{hash(f"{ticker}{i}id") % 10000}'
                }
                
                news_articles.append(article)
        
        return news_articles

    def collect_comprehensive_news(self, tickers):
        """Insert comprehensive news into MongoDB (your existing method)"""
        try:
            logger.info("Generating comprehensive news dataset...")
            news_articles = self.generate_comprehensive_news(tickers)
            
            inserted_count = 0
            for article in news_articles:
                try:
                    result = self.mongo_collection.update_one(
                        {'article_id': article['article_id']},
                        {'$set': article},
                        upsert=True
                    )
                    if result.upserted_id or result.modified_count > 0:
                        inserted_count += 1
                except Exception as e:
                    logger.error(f"Error inserting article: {e}")
            
            logger.info(f"Inserted {inserted_count} comprehensive news articles")
            
        except Exception as e:
            logger.error(f"Error in comprehensive news collection: {e}")

    def generate_sample_portfolio(self):
        """Generate sample portfolio holdings (your existing method)"""
        cursor = self.mysql_conn.cursor()
        
        portfolio_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        for ticker in portfolio_stocks:
            shares = 10 + (hash(f"{ticker}shares") % 100)
            avg_cost = 50 + (hash(f"{ticker}cost") % 250)
            current_price = avg_cost * (0.8 + (hash(f"{ticker}current") % 60) / 100.0)
            
            market_value = shares * current_price
            unrealized_pnl = (current_price - avg_cost) * shares
            
            cursor.execute("""
            REPLACE INTO portfolio_holdings (ticker, shares, avg_cost, current_price, 
                                           market_value, unrealized_pnl)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (ticker, shares, avg_cost, current_price, market_value, unrealized_pnl))
        
        self.mysql_conn.commit()
        cursor.close()
        logger.info("Sample portfolio data generated")

    def verify_frontend_compatibility(self):
        """Verify data is compatible with frontend requirements"""
        try:
            cursor = self.mysql_conn.cursor()
            
            # Check all required tables for frontend
            required_tables = {
                'companies': 'Company dropdown and info',
                'stock_prices': 'Price charts with technical indicators', 
                'financial_metrics': 'KPI cards and company details (REQUIRED by get_companies.php)',
                'market_indices': 'Market indices charts',
                'sector_performance': 'Sector heatmaps',
                'portfolio_holdings': 'Portfolio widgets'
            }
            
            all_good = True
            for table, purpose in required_tables.items():
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"Table {table}: {count} records ({purpose})")
                
                if count == 0:
                    logger.warning(f"WARNING: {table} is empty - {purpose} won't work")
                    all_good = False
            
            # Test the specific query used by get_companies.php
            cursor.execute("""
                SELECT 
                    c.*,
                    fm.pe_ratio,
                    fm.dividend_yield,
                    fm.market_cap as current_market_cap,
                    fm.beta,
                    (SELECT COUNT(*) FROM stock_prices sp WHERE sp.ticker = c.ticker) as price_records_count,
                    (SELECT MAX(date) FROM stock_prices sp WHERE sp.ticker = c.ticker) as latest_price_date
                FROM companies c
                LEFT JOIN financial_metrics fm ON c.ticker = fm.ticker
                ORDER BY c.market_cap DESC
                LIMIT 3
            """)
            test_data = cursor.fetchall()
            if test_data:
                logger.info("SUCCESS: get_companies.php query test passed")
                for row in test_data:
                    logger.info(f"   {row[0]}: PE={row[6]}, Beta={row[9]}, Records={row[10]}")
            else:
                logger.warning("WARNING: get_companies.php query test failed")
                all_good = False
            
            cursor.close()
            
            # Check MongoDB for news feed
            mongo_count = self.mongo_collection.count_documents({})
            logger.info(f"MongoDB news articles: {mongo_count} (for news feed)")
            
            if mongo_count == 0:
                logger.warning("WARNING: No news articles - news feed will be empty")
                all_good = False
            
            return all_good
            
        except Exception as e:
            logger.error(f"Error in frontend compatibility check: {e}")
            return False

    def run_comprehensive_collection(self):
        """Run the complete comprehensive data collection"""
        logger.info("Starting FRONTEND-INTEGRATED data collection...")
        
        try:
            if not self.create_mysql_database():
                return False
            
            if not self.connect_databases():
                return False
            
            # Create enhanced tables (includes financial_metrics now)
            logger.info("Creating frontend-compatible database tables...")
            self.create_enhanced_mysql_tables()
            
            # Your existing collection methods
            logger.info("Collecting market indices...")
            self.collect_market_indices()
            
            logger.info("Collecting enhanced stock data...")
            self.collect_enhanced_stock_data(self.major_stocks)
            
            logger.info("Collecting sector performance...")
            self.collect_sector_performance()
            
            logger.info("Generating comprehensive news...")
            self.collect_comprehensive_news(self.major_stocks)
            
            logger.info("Creating sample portfolio...")
            self.generate_sample_portfolio()
            
            # NEW: Frontend compatibility verification
            logger.info("Verifying frontend compatibility...")
            if self.verify_frontend_compatibility():
                logger.info("FRONTEND-INTEGRATED collection completed successfully!")
                logger.info("")
                logger.info("Your PHP frontend should now display:")
                logger.info("   Company dropdown with all major stocks")
                logger.info("   Stock price charts with moving averages")
                logger.info("   Market indices charts (S&P 500, NASDAQ, Dow)")
                logger.info("   Financial metrics in KPI cards")
                logger.info("   News feed with sentiment analysis")
                logger.info("   Sector performance data")
                logger.info("   Portfolio widgets with sample data")
                logger.info("")
                logger.info("Next steps:")
                logger.info("1. Start your web server (XAMPP/WAMP/MAMP)")
                logger.info("2. Open http://localhost/your-project-folder/index.html")
                logger.info("3. Enjoy your data-driven dashboard!")
                return True
            else:
                logger.error("❌ Frontend compatibility verification failed")
                return False
                
        except Exception as e:
            logger.error(f"Error in comprehensive collection: {e}")
            return False
        
        finally:
            if self.mysql_conn:
                self.mysql_conn.close()

def main():
    """Main execution function"""
    print("=" * 70)
    print("FRONTEND-INTEGRATED FINANCIAL DATA COLLECTION")
    print("Based on your comprehensive data collection script")
    print("=" * 70)
    
    collector = FrontendIntegratedCollector()
    success = collector.run_comprehensive_collection()
    
    print("=" * 70)
    if success:
        print("✅ SUCCESS: Your data is ready for the frontend!")
        print("\nData collected:")
        print(f"- {len(collector.major_stocks)} companies with full metrics")
        print(f"- 1 year of stock data with technical indicators")
        print(f"- {len(collector.market_indices)} market indices")
        print(f"- {len(collector.sectors)} sector ETFs")
        print(f"- {len(collector.major_stocks) * 20} news articles")
        print("- Sample portfolio data")
    else:
        print("❌ FAILED: Check logs for details")
    print("=" * 70)

if __name__ == "__main__":
    main()