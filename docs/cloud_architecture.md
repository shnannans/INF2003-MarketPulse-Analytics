# Cloud Architecture

**Team Member 4 Deliverable** - MarketPulse Analytics

This document describes the cloud architecture of the MarketPulse Analytics platform.

---

## Overview

The MarketPulse Analytics platform uses Google Cloud Platform (GCP) for hosting databases and can be deployed on various GCP compute services.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Client Browser                         │
│                  (index.html)                            │
└──────────────────────┬──────────────────────────────────┘
                        │ HTTPS
                        ↓
┌─────────────────────────────────────────────────────────┐
│              FastAPI Application                         │
│         (Local or Cloud Run / GCE)                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  API Endpoints:                                   │  │
│  │  - /api/stock_analysis                            │  │
│  │  - /api/news                                      │  │
│  │  - /api/sentiment                                 │  │
│  │  - /api/dashboard                                 │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────┬──────────────┬───────────────────────┘
                   │              │
         ┌─────────┴──┐    ┌──────┴─────────┐
         │            │    │                │
         ↓            ↓    ↓                ↓
┌─────────────────┐ ┌──────────────────────────┐
│  Cloud SQL      │ │  Cloud Firestore          │
│  (MySQL)        │ │  (NoSQL)                  │
│                 │ │                          │
│  - Stock prices │ │  - Financial news        │
│  - Companies    │ │  - Sentiment trends      │
│  - Indices      │ │  - Topic highlights      │
│  - Technical    │ │                          │
│    indicators   │ │                          │
└─────────────────┘ └──────────────────────────┘
         │                      │
         └──────────┬───────────┘
                    ↓
         ┌──────────────────────┐
         │  External APIs       │
         │  - yfinance          │
         │  - NewsAPI           │
         └──────────────────────┘
```

---

## Components

### 1. FastAPI Backend

**Location:** Can run locally or on Google Cloud

**Responsibilities:**
- REST API endpoints
- Business logic
- Data aggregation
- Cache management

**Deployment Options:**
- Local development
- Cloud Run (serverless)
- Compute Engine (VMs)
- App Engine

### 2. Cloud SQL (MySQL)

**Purpose:** Structured relational data storage

**Data Stored:**
- Stock prices with technical indicators
- Company information
- Market indices data
- Historical price data

**Configuration:**
- **Host:** 34.133.0.30
- **Database:** databaseproj
- **Connection:** Over internet (IP whitelisting required)

**Benefits:**
- Managed MySQL service
- Automatic backups
- High availability
- Scalable

### 3. Cloud Firestore

**Purpose:** NoSQL document storage for unstructured data

**Data Stored:**
- Financial news articles
- Sentiment analysis results
- Topic highlights
- Trend data

**Configuration:**
- **Project:** inf1005-452110
- **Database:** databaseproj

**Benefits:**
- Fast queries
- Automatic scaling
- Real-time updates (if needed)
- Flexible schema

### 4. External APIs

**yfinance:**
- Live stock data
- Historical prices
- Company information

**NewsAPI:**
- Financial news articles
- Company-specific news
- Market news

---

## Data Flow

### Stock Data Flow

1. **Request arrives** → FastAPI endpoint
2. **Check database** → Query MySQL for cached data
3. **If insufficient data:**
   - Fetch from yfinance API
   - Store in MySQL (write-through)
   - Return to client
4. **If sufficient data:**
   - Return from MySQL
   - Fast response

### News & Sentiment Flow

1. **Request arrives** → FastAPI endpoint
2. **Check Firestore** → Query for cached articles/trends
3. **If stale/empty:**
   - Fetch from NewsAPI
   - Analyze sentiment
   - Store in Firestore
   - Return to client
4. **If fresh data exists:**
   - Return from Firestore
   - Fast response

---

## Security Architecture

### Authentication & Authorization

**MySQL:**
- Username/password authentication
- IP whitelisting
- SSL/TLS encryption (recommended for production)

**Firestore:**
- Service account authentication
- IAM role-based access control
- Application Default Credentials (ADC)

### Network Security

- Private IP addresses (within GCP VPC)
- IP whitelisting for Cloud SQL
- Firewall rules on Compute Engine
- VPC peering for cross-service communication

### Data Security

- Encrypted at rest
- Encrypted in transit
- Credentials stored in environment variables
- Service accounts with least privilege

---

## Scalability

### Horizontal Scaling

**FastAPI:**
- Stateless design allows multiple instances
- Load balancer distributes requests
- Auto-scaling with Cloud Run

**Cloud SQL:**
- Read replicas for query scaling
- Connection pooling in application
- Query optimization

**Firestore:**
- Automatic scaling
- No manual scaling needed
- Global distribution (if configured)

### Performance Optimization

1. **Database-first strategy:** Reduces external API calls
2. **Caching:** In-memory cache for frequently accessed data
3. **Connection pooling:** Reuse database connections
4. **Async operations:** Non-blocking I/O operations

---

## Deployment Options

### Option 1: Cloud Run (Recommended)

**Pros:**
- Auto-scaling
- Pay per use
- No server management
- Easy deployment

**Cons:**
- Cold starts possible
- Limited customization

### Option 2: Compute Engine

**Pros:**
- Full control
- Custom configurations
- Better for long-running processes

**Cons:**
- Manual scaling
- Server management required

### Option 3: App Engine

**Pros:**
- Easy deployment
- Automatic scaling
- Managed service

**Cons:**
- Less flexible than Compute Engine

---

## Monitoring & Logging

### Cloud Monitoring

- API response times
- Error rates
- Database connection metrics
- Firestore read/write operations

### Logging

- Application logs in Cloud Logging
- Error tracking
- Performance metrics
- User activity (if implemented)

---

## Cost Optimization

1. **Use Firestore efficiently:** Minimize read/write operations
2. **Cache aggressively:** Reduce external API calls
3. **Database-first:** Use cached data when possible
4. **Right-size instances:** Choose appropriate machine types

---

## Disaster Recovery

### Backups

**Cloud SQL:**
- Automatic daily backups
- Point-in-time recovery
- Manual snapshot capability

**Firestore:**
- Automatic backups
- Export/import functionality

### Recovery Procedures

1. Restore from Cloud SQL backup
2. Export/import Firestore data
3. Redeploy application
4. Verify functionality

---

## Future Enhancements

1. **CDN:** For static assets
2. **Load Balancing:** For high traffic
3. **Redis Cache:** For even faster response times
4. **Message Queue:** For async processing
5. **Multi-region:** For global users

---

**Created by:** Team Member 4  
**Last Updated:** 2024

