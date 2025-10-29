# ADR-001: Cloud Database Selection

**Date:** 2024  
**Status:** Accepted  
**Deciders:** Development Team

## Context

The MarketPulse Analytics platform requires persistent data storage for:
1. Structured data: Stock prices, company information, technical indicators
2. Unstructured data: News articles, sentiment analysis results

We needed to choose between local databases (MySQL, MongoDB) and cloud-managed services.

## Decision

We selected **Google Cloud Platform** with:
- **Cloud SQL (MySQL)** for structured relational data
- **Cloud Firestore** for unstructured document data

## Rationale

### Cloud SQL (MySQL)

**Pros:**
- Managed service (no server maintenance)
- Automatic backups
- High availability
- Scalable (can upgrade instances)
- SQL compatibility (familiar to team)
- Supports complex queries and joins
- Good for time-series stock data

**Cons:**
- Cost (but manageable for project)
- Requires IP whitelisting for access
- Network latency (minimal impact)

### Firestore

**Pros:**
- NoSQL flexibility for varying article structures
- Automatic scaling
- Fast queries
- Google Cloud integration
- Real-time capabilities (if needed later)
- Serverless architecture

**Cons:**
- Cost per read/write operation
- Less flexible querying than SQL
- Learning curve for NoSQL

## Alternatives Considered

### Option 1: Local MySQL + MongoDB
- **Rejected:** Requires server maintenance, no automatic backups, deployment complexity

### Option 2: Cloud SQL Only
- **Rejected:** Not optimal for unstructured news/sentiment data

### Option 3: Firestore Only
- **Rejected:** MySQL better for structured stock data with relationships

### Option 4: AWS RDS + DynamoDB
- **Rejected:** Team more familiar with Google Cloud, better pricing for our use case

## Consequences

**Positive:**
- No database server management required
- Automatic backups and high availability
- Scalable architecture
- Separation of concerns (SQL for structured, NoSQL for unstructured)

**Negative:**
- Requires Google Cloud account setup
- Network dependencies (internet required)
- Cost considerations (manageable for project scale)
- IP whitelisting needed for MySQL access

## Implementation

- Cloud SQL instance created: `databaseproj`
- Firestore database: `databaseproj`
- Connection via Application Default Credentials (ADC)
- Environment variables for configuration

## Future Considerations

- May add Redis cache layer for performance
- Consider Cloud SQL read replicas if traffic increases
- Monitor Firestore costs as data grows

---

**Approved by:** Development Team  
**Last Updated:** 2024

