# MarketPulse Analytics Platform

> **Real-time financial analytics platform with sentiment analysis and stock price tracking**

## 🚀 Quick Start

1. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with your credentials
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server:**
   ```bash
   cd api_python
   python -m uvicorn main:app --reload
   ```

4. **Access the application:**
   - Frontend: Open `index.html` in browser
   - API Docs: http://localhost:8000/docs
   - API: http://localhost:8000/api

## 📚 Documentation

**All documentation is now in the [`docs/`](docs/) directory:**

- **[📘 Setup Guide](docs/environment_setup_guide.md)** - Complete setup instructions
- **[🔗 Cloud Connection](docs/cloud_connection_guide.md)** - Connect to Google Cloud databases
- **[🏗️ Architecture](docs/cloud_architecture.md)** - System architecture overview
- **[🔍 Troubleshooting](docs/known_issues.md)** - Common problems and solutions
- **[📊 Monitoring](docs/monitoring_guide.md)** - Monitor system health
- **[👥 Team Tasks](docs/team_assignments_updated.txt)** - Task assignments for 6 team members
- **[🚀 Roadmap](docs/improvements.txt)** - Project roadmap and improvements

**New team members:** Start with [`docs/environment_setup_guide.md`](docs/environment_setup_guide.md)

## Prerequisites

- **Python 3.8+** with pip
- **Google Cloud Account** access (database already set up on cloud)
- **NewsAPI Account** (free tier available at https://newsapi.org/register)

### Python Dependencies
```bash
pip install -r requirements.txt
```

## Database Configuration

**✅ Databases are already set up on Google Cloud**

The project uses:
- **MySQL** on Google Cloud (host: 34.133.0.30)
- **Firestore** on Google Cloud (database: databaseproj)

**Configuration Steps:**
1. Copy `env.example` to `.env`
2. **Set up Google Cloud authentication** (see below)
3. Add your MySQL credentials and NewsAPI key to `.env`
4. See [`docs/environment_setup_guide.md`](docs/environment_setup_guide.md) for detailed setup

**🔑 Google Cloud Authentication:**

The easiest way is using **Application Default Credentials (ADC)**:

```bash
# Install Google Cloud SDK
# Windows: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login
gcloud config set project inf1005-452110

# That's it! No key file needed.
```

See [`setup_gcloud_auth.md`](setup_gcloud_auth.md) for detailed instructions.

**No local database setup needed!** Data collection script can be used to populate test data if needed.

## Project Structure

```
MarketPulse-Analytics/
├── api_python/              # FastAPI backend
│   ├── main.py             # FastAPI application
│   ├── routers/            # API endpoints
│   ├── config/             # Database connections
│   │   ├── database.py     # MySQL configuration
│   │   └── firestore.py    # Firestore configuration
│   ├── models/             # Data models
│   └── utils/              # Services (live data, news)
├── docs/                   # 📚 Documentation (NEW!)
│   ├── environment_setup_guide.md
│   ├── cloud_connection_guide.md
│   ├── cloud_architecture.md
│   ├── known_issues.md
│   ├── monitoring_guide.md
│   ├── improvements.txt
│   └── team_assignments_updated.txt
├── index.html              # Frontend dashboard
├── js/main.js             # Frontend JavaScript
├── env.example            # Environment variables template
├── local_data_collection.py  # Data population script
└── README.md              # This file
```

## Features

- ✅ **Real-time Stock Data** - Fetch live stock prices with technical indicators (MA_5, MA_20, MA_50, MA_200)
- ✅ **News Integration** - Financial news with sentiment analysis
- ✅ **Sentiment Analysis** - TextBlob + VADER combined sentiment scoring
- ✅ **Interactive Charts** - Chart.js visualizations for stock performance
- ✅ **Database-First Strategy** - Caches data for faster access and reduces API calls
- ✅ **Cloud Storage** - MySQL + Firestore on Google Cloud Platform

## API Endpoints

- `GET /api/companies` - List all companies
- `GET /api/company/{ticker}` - Get company details
- `GET /api/stock_analysis` - Get stock data with technical indicators
- `GET /api/news` - Get financial news articles
- `GET /api/sentiment` - Get sentiment analysis and trends
- `GET /api/dashboard` - Dashboard statistics

Full API documentation: http://localhost:8000/docs

## For More Information

**See the [`docs/`](docs/) directory for complete documentation:**

- Setup instructions
- Troubleshooting guide
- System architecture
- Team assignments
- Project roadmap
- And more!

## License

Project for academic purposes