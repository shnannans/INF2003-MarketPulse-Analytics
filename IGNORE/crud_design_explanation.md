# CRUD API Design Explanation

## Overview
This document explains **what data** you would be creating, updating, patching, and deleting for each CRUD operation - not the technical implementation, but the **logical design** and **use cases**.

---

## TASK 1: Startup Data Synchronization (Automatic on API Start)

### **Automatic Data Refresh on API Startup**

When you start the API server, the system automatically performs a **data synchronization** operation to ensure all existing data in the MySQL database is up-to-date with the current day.

**What Happens on Startup:**

1. **Query All Existing Companies:**
   - Fetch all tickers from the `companies` table
   - For each company that exists in the database, perform data updates

2. **For Each Company - Update Stock Prices (POST - Add New Records):**
   - Query the `stock_prices` table to find the **latest date** for each ticker
   - Use **yfinance** to fetch stock price data from the last stored date **up to today**
   - **POST (Insert)** new stock price records for all missing dates
   - Only add new records - do not modify existing historical data
   - Calculate and store moving averages (MA_5, MA_20, MA_50, MA_200) for new dates
   - Store price change percentages and volume changes
   - **Result:** All companies now have stock prices updated to the current day

3. **For Each Company - Update Financial Metrics (PUT - Replace Existing Record):**
   - Use **yfinance** to fetch current financial metrics (PE ratio, dividend yield, beta, market cap)
   - **PUT (Update)** the existing record in the `financial_metrics` table
   - Since there is only **one record per company** in financial_metrics, this replaces the entire record
   - **Result:** All companies now have current financial metrics

4. **Update Market Indices (POST - Add New Records):**
   - Query the `market_indices` table to find the **latest date** for each index symbol
   - Use **yfinance** to fetch index data from the last stored date **up to today**
   - **POST (Insert)** new index records for all missing dates
   - Only add new records - do not modify existing historical data
   - **Result:** All market indices now have data updated to the current day

5. **Update Sector Performance (POST - Add New Records):**
   - Query the `sector_performance` table to find the **latest date** for each sector
   - Use **yfinance** or sector ETF data to fetch sector performance from the last stored date **up to today**
   - **POST (Insert)** new sector performance records for all missing dates
   - Only add new records - do not modify existing historical data
   - **Result:** All sector performance data now updated to the current day

**Summary of Operations:**
- **Stock Prices:** POST (add new records from last date to today)
- **Financial Metrics:** PUT (update the one record per company)
- **Market Indices:** POST (add new records from last date to today)
- **Sector Performance:** POST (add new records from last date to today)

**Use Cases:**
- **Automatic Data Freshness:** Ensures database is always current when API starts
- **No Manual Updates Required:** System automatically catches up on any missed days
- **Historical Preservation:** Only adds new data, never modifies existing historical records
- **Complete Coverage:** Updates all companies, indices, and sectors in one startup operation

**Benefits:**
- **Always Current:** Database is automatically synchronized to current day on startup
- **Gap Filling:** Automatically fills in any missing days (e.g., if API was down for a few days)
- **Data Integrity:** Uses POST for time-series data (adds new records) and PUT for single records (financial metrics)
- **Efficient:** Only fetches and inserts data that's missing (from last stored date to today)

**Error Handling:**
- If yfinance fails for a specific ticker: Log error, continue with other companies
- If database operation fails: Log error, continue with other companies
- Startup should not fail completely if one company's update fails
- Log summary at end: "Updated X companies, Y stock price records, Z indices"

**Performance Considerations:**
- This operation may take time if there are many companies
- Consider running in background thread/async task
- Consider batching operations to avoid overwhelming yfinance API
- Consider rate limiting to respect yfinance API limits

---

## TASK 2: Companies Management API - POST

### **POST `/api/companies`** - Create a New Company (Automated Data Fetching)
**What you're posting:**
```json
{
  "ticker": "AAPL"
}
```

**Note:** Only the ticker is required. The system automatically fetches all other data from yfinance.

**System Workflow:**

1. **Check Database First:**
   - Query the SQL database to check if the ticker already exists in the `companies` table
   - If the company already exists, return an error (409 Conflict) or existing company data

2. **If Ticker Doesn't Exist - Automated Data Fetching:**
   - Use **yfinance** to fetch comprehensive data for the ticker:
     - **Company Information**: Company name, sector, market cap, exchange, etc.
     - **Financial Metrics**: PE ratio, dividend yield, beta, current market cap
     - **Complete Historical Stock Prices**: Full historical dataset from IPO/earliest available date to current date
       - Open, High, Low, Close prices
       - Adjusted close prices
       - Volume data
       - All available historical records (not just recent data)

3. **Database Population:**
   - Insert company information into `companies` table
   - Insert financial metrics into `financial_metrics` table
   - Insert **all historical stock price records** into `stock_prices` table
     - Calculate and store moving averages (MA_5, MA_20, MA_50, MA_200) for each date
     - Store price change percentages and volume changes
     - Ensure complete historical dataset is stored (every trading day available)

4. **Response:**
   - Returns the created company with all fetched data
   - Includes summary of records inserted (e.g., "Inserted 5000 stock price records")

**Use Cases:**
- Adding a new company to track that doesn't exist in the database yet
- Automatically populating complete company data from yfinance
- Setting up a new ticker with full historical data
- One-step company onboarding with complete data population

**Benefits:**
- **No manual data entry required** - just provide ticker symbol
- **Complete historical data** - automatically fetches and stores all available stock price history
- **Fully populated database** - company, metrics, and prices all inserted in one operation
- **Data consistency** - ensures all related tables are populated together

**Error Handling:**
- If ticker already exists: Return 409 Conflict or existing company data
- If ticker not found in yfinance: Return 404 Not Found
- If yfinance API fails: Return 503 Service Unavailable
- If database insertion fails: Rollback all inserts, return 500 error

---

## TASK 3: Companies Management API - PUT

### **PUT `/api/companies/{ticker}`** - Full Update (Replace Entire Company)
**What you're putting:**
```json
{
  "ticker": "AAPL",  // Must match URL parameter
  "company_name": "Apple Inc. (Updated)",
  "sector": "Consumer Technology",  // Changed sector
  "market_cap": 3500000000000  // Updated market cap
}
```

**Use Cases:**
- Completely replacing company information
- Correcting all fields at once
- Bulk updates from external data sources

**What happens:**
- Replaces ALL fields of the company (even if you send null/empty values)
- If company doesn't exist, you might create it (upsert behavior) or return 404
- Updates all provided fields, sets others to null if not provided

---

## TASK 4: Companies Management API - PATCH

### **PATCH `/api/companies/{ticker}`** - Partial Update (Update Only Some Fields)
**What you're patching:**
```json
{
  "sector": "Consumer Technology"  // Only updating sector, everything else stays the same
}
```

**Use Cases:**
- Updating just the sector when a company changes business focus
- Correcting a typo in company name
- Updating market cap when new data arrives
- Making small corrections without touching other fields

**What happens:**
- Only updates the fields you send
- Leaves all other fields unchanged
- More flexible than PUT - you don't need to send everything

**Example Scenarios:**
- Company changes sector: `{"sector": "New Sector"}`
- Fix typo: `{"company_name": "Corrected Name"}`
- Update market cap: `{"market_cap": 4000000000000}`

---

## TASK 5: Companies Management API - DELETE

### **DELETE `/api/companies/{ticker}`** - Soft Delete a Company
**What you're deleting:**
- Marks the company record as deleted (soft delete) - record remains in database

**Use Cases:**
- Removing a company that's no longer publicly traded
- Cleaning up test/demo data
- Removing companies that were added by mistake
- Companies that merged or were acquired
- Temporarily hiding a company from search results

**What happens:**
- Sets `deleted_at` timestamp (or `is_deleted` flag) on the company record
- Company record remains in database but is marked as deleted
- Related data (stock_prices, financial_metrics) remains intact
- GET endpoints will exclude soft-deleted companies from results
- Can be restored later if needed

**Soft Delete Behavior:**
- Record is not permanently removed from database
- `deleted_at` field stores the deletion timestamp
- All queries filter out records where `deleted_at IS NOT NULL`
- Admin can restore deleted companies if needed
- Historical data integrity is preserved

---

## TASK 6: News Management API - POST

### **POST `/api/news/ingest`** - Create/Ingest News Articles
**What you're posting:**
```json
{
  "title": "Apple Announces New iPhone",
  "content": "Full article text here...",
  "published_date": "2024-01-15T10:30:00Z",
  "source": "TechCrunch",
  "ticker": "AAPL",  // Optional - which company this relates to
  "url": "https://techcrunch.com/article",
  "sentiment_analysis": {  // Optional - pre-computed sentiment
    "polarity": 0.5,
    "subjectivity": 0.3
  }
}
```

**Use Cases:**
- Manually adding news articles not captured by NewsAPI
- Bulk importing historical news articles
- Adding articles from sources not covered by NewsAPI
- Controlled ingestion (as opposed to automatic scraping)
- Adding curated/verified news articles

**What happens:**
- Creates a new document in Firestore `financial_news` collection
- Generates a unique ID for the article
- Optionally runs sentiment analysis if not provided
- Stores in Firestore (NoSQL database)

**Bulk Operation:**
```json
{
  "articles": [
    {"title": "Article 1", ...},
    {"title": "Article 2", ...},
    {"title": "Article 3", ...}
  ]
}
```
- Allows ingesting multiple articles in one request
- Useful for batch imports

---

## TASK 7: News Management API - PUT

### **PUT `/api/news/{id}`** - Full Update of News Article
**What you're putting:**
```json
{
  "title": "Updated Title",
  "content": "Updated full content...",
  "published_date": "2024-01-15T10:30:00Z",
  "source": "Updated Source",
  "ticker": "AAPL",
  "sentiment_analysis": {...}  // Must provide everything
}
```

**Use Cases:**
- Correcting article content
- Updating sentiment analysis results
- Fixing metadata (date, source, ticker association)

**What happens:**
- Replaces entire article document in Firestore
- All fields must be provided (or set to null)

---

## TASK 8: News Management API - PATCH

### **PATCH `/api/news/{id}`** - Partial Update of News Article
**What you're patching:**
```json
{
  "ticker": "MSFT"  // Only updating which company this relates to
}
```

**Use Cases:**
- Correcting ticker association (article was mis-tagged)
- Updating sentiment score after re-analysis
- Fixing a typo in title
- Adding missing metadata

**What happens:**
- Only updates specified fields
- Leaves other fields unchanged

**Example Scenarios:**
- Fix ticker: `{"ticker": "AAPL"}` - article was incorrectly tagged
- Update sentiment: `{"sentiment_analysis": {"polarity": 0.8}}`
- Fix date: `{"published_date": "2024-01-16T10:30:00Z"}`

---

## TASK 9: News Management API - DELETE

### **DELETE `/api/news/{id}`** - Soft Delete News Article
**What you're deleting:**
- Marks the news article as deleted (soft delete) - document remains in Firestore

**Use Cases:**
- Removing duplicate articles
- Deleting articles that are no longer relevant
- Cleaning up test/demo data
- Removing articles with incorrect information
- Compliance: removing articles that violate terms
- Temporarily hiding articles from search results

**What happens:**
- Sets `deleted_at` timestamp (or `is_deleted` flag) in the Firestore document
- Article document remains in Firestore but is marked as deleted
- GET endpoints will exclude soft-deleted articles from results
- Can be restored later if needed

**Soft Delete Behavior:**
- Document is not permanently removed from Firestore
- `deleted_at` field stores the deletion timestamp
- All queries filter out documents where `deleted_at IS NOT NULL`
- Admin can restore deleted articles if needed

---

## 3. What About Stock Prices?

### **Stock Prices and Company POST Relationship**

**Important:** When you **POST a new company** (see Section 1), the system automatically:
- Fetches **complete historical stock prices** from yfinance
- Inserts **all historical records** into the `stock_prices` table
- This means stock prices are **automatically populated** when a company is created

**Should Stock Prices Have Separate CRUD?**

**Current Situation:**
- Stock prices are **automatically collected** when creating a company via POST
- They represent **historical facts** - you don't usually "create" or "delete" historical stock prices
- They're time-series data that should be immutable
- **Note:** Stock prices are populated as part of company creation, not separately

**Possible Separate CRUD Operations (if needed for edge cases):**

#### **POST `/api/stock_prices`** - Manual Price Entry
**Use Cases:**
- Adding historical data that's missing
- Correcting gaps in data collection
- Adding data from alternative sources
- Backfilling historical data

**What you'd post:**
```json
{
  "ticker": "AAPL",
  "date": "2024-01-15",
  "open_price": 150.25,
  "high_price": 152.30,
  "low_price": 149.80,
  "close_price": 151.50,
  "volume": 50000000,
  "ma_5": 150.00,
  "ma_20": 148.50,
  "ma_50": 145.00,
  "ma_200": 140.00
}
```

#### **PATCH `/api/stock_prices/{ticker}/{date}`** - Correct Price Data
**Use Cases:**
- Fixing incorrect price data
- Correcting data entry errors
- Updating moving averages if calculation was wrong

**What you'd patch:**
```json
{
  "close_price": 151.75  // Correcting a wrong close price
}
```

#### **DELETE `/api/stock_prices/{ticker}/{date}`** - Soft Delete Price Record
**Use Cases:**
- Marking duplicate entries as deleted
- Marking incorrect data that can't be corrected
- Cleaning up test data
- Temporarily excluding specific price records from calculations

**What happens:**
- Sets `deleted_at` timestamp on the stock price record
- Record remains in database but is marked as deleted
- GET endpoints and calculations will exclude soft-deleted price records
- Can be restored later if needed

**Soft Delete Behavior:**
- Record is not permanently removed from database
- `deleted_at` field stores the deletion timestamp
- All queries filter out records where `deleted_at IS NOT NULL`
- Historical data integrity is preserved

**Recommendation:** Stock prices CRUD is **lower priority** - focus on Companies and News first, as those are more likely to need manual management.

---

## 4. Financial Metrics CRUD (Optional)

### **PATCH `/api/companies/{ticker}/metrics`** - Update Financial Metrics
**What you're patching:**
```json
{
  "pe_ratio": 28.5,
  "dividend_yield": 0.015,
  "beta": 1.2,
  "market_cap": 3000000000000
}
```

**Use Cases:**
- Updating financial metrics when new data arrives
- Correcting calculated metrics
- Manual override of automatically calculated values

**Note:** Financial metrics are often calculated automatically, so CRUD might be less needed here.

---

## TASK 10: User Management API - POST

### **POST `/api/users`** - Create a New User
**What you're posting:**
```json
{
  "username": "john_doe",
  "email": "john.doe@example.com",
  "password": "secure_password_123",
  "role": "user"  // "user" or "admin"
}
```

**Use Cases:**
- Registering new users
- Admin creating user accounts
- Setting up initial admin accounts
- Bulk user creation

**What happens:**
- Creates a new user record in the `users` table
- Password is hashed before storage (never store plain text)
- Sets `created_at` timestamp
- Sets `is_active` to true by default
- Returns created user (without password)

**Validation:**
- Username must be unique
- Email must be unique and valid format
- Password must meet security requirements (min length, complexity)
- Role must be either "user" or "admin"

---

## TASK 11: User Management API - GET (List)

### **GET `/api/users`** - List All Users
**Query Parameters:**
- `role`: Filter by role (user/admin)
- `is_active`: Filter by active status (true/false)
- `limit`: Maximum number of results
- `offset`: Pagination offset

**Use Cases:**
- Admin viewing all users
- User management dashboard
- Generating user reports

**What happens:**
- Returns list of users (excluding soft-deleted users)
- Excludes password from response
- Supports filtering and pagination

---

### **GET `/api/users/{user_id}`** - Get User Details
**Use Cases:**
- Viewing specific user information
- User profile page
- Admin reviewing user account

**What happens:**
- Returns user details (excluding password)
- Returns 404 if user doesn't exist or is soft-deleted

---

## TASK 12: User Management API - PUT

### **PUT `/api/users/{user_id}`** - Full Update of User
**What you're putting:**
```json
{
  "username": "john_doe_updated",
  "email": "john.updated@example.com",
  "role": "admin",
  "is_active": true
}
```

**Use Cases:**
- Admin updating all user fields
- Changing user role (promote to admin, demote to user)
- Activating/deactivating user accounts
- Bulk user updates

**What happens:**
- Replaces ALL fields of the user (except password - use separate endpoint for password changes)
- Updates `updated_at` timestamp
- Only admins can change roles

**Permissions:**
- Admins can update any user
- Users can only update their own account (limited fields)

---

## TASK 13: User Management API - PATCH

### **PATCH `/api/users/{user_id}`** - Partial Update of User
**What you're patching:**
```json
{
  "email": "newemail@example.com"  // Only updating email
}
```

**Use Cases:**
- User updating their own email
- Admin changing user role
- Activating/deactivating specific users
- Updating user preferences

**What happens:**
- Only updates the fields you send
- Leaves all other fields unchanged
- Updates `updated_at` timestamp

**Example Scenarios:**
- Change email: `{"email": "newemail@example.com"}`
- Change role: `{"role": "admin"}` (admin only)
- Deactivate user: `{"is_active": false}` (admin only)

---

## TASK 14: User Management API - DELETE

### **DELETE `/api/users/{user_id}`** - Soft Delete User
**What you're deleting:**
- Marks the user account as deleted (soft delete) - record remains in database

**Use Cases:**
- Removing user accounts
- Cleaning up test/demo accounts
- Removing accounts that violate terms of service
- Temporarily disabling user access

**What happens:**
- Sets `deleted_at` timestamp on the user record
- User record remains in database but is marked as deleted
- User cannot log in after soft delete
- All user-related data remains intact
- GET endpoints will exclude soft-deleted users from results
- Can be restored later if needed

**Soft Delete Behavior:**
- Record is not permanently removed from database
- `deleted_at` field stores the deletion timestamp
- All queries filter out records where `deleted_at IS NOT NULL`
- Admin can restore deleted users if needed
- User authentication will fail for soft-deleted users

**Permissions:**
- Only admins can delete users
- Users cannot delete their own accounts (use account deactivation instead)

---

## TASK 15: User Management API - Restore

### **PATCH `/api/users/{user_id}/restore`** - Restore Soft-Deleted User
**What you're patching:**
- Restores a soft-deleted user account

**Use Cases:**
- Restoring accidentally deleted accounts
- Re-enabling user access after investigation
- Recovering test accounts

**What happens:**
- Sets `deleted_at` to NULL
- User account becomes active again
- User can log in again

**Permissions:**
- Only admins can restore users

---

## TASK 16: User Management API - Password Change

### **PATCH `/api/users/{user_id}/password`** - Change User Password
**What you're patching:**
```json
{
  "current_password": "old_password",
  "new_password": "new_secure_password"
}
```

**Use Cases:**
- User changing their own password
- Admin resetting user passwords
- Password recovery flow

**What happens:**
- Validates current password (for users changing their own)
- Hashes new password before storage
- Updates password in database
- Invalidates existing sessions (optional, for security)

**Permissions:**
- Users can change their own password (must provide current password)
- Admins can change any user's password (may not need current password)

---

## TASK 17: User Management API - Role Change

### **PATCH `/api/users/{user_id}/role`** - Change User Role
**What you're patching:**
```json
{
  "role": "admin"  // "user" or "admin"
}
```

**Use Cases:**
- Promoting user to admin
- Demoting admin to regular user
- Role management

**What happens:**
- Updates user role
- Changes permissions immediately
- Updates `updated_at` timestamp

**Permissions:**
- Only admins can change user roles
- Cannot change your own role (prevents lockout)

---

## TASK 18: Admin Management API - GET

### **GET `/api/admins`** - List All Admins
**Query Parameters:**
- `is_active`: Filter by active status
- `limit`: Maximum number of results
- `offset`: Pagination offset

**Use Cases:**
- Viewing all admin accounts
- Admin management dashboard
- Security audit

**What happens:**
- Returns list of users with role="admin" (excluding soft-deleted)
- Excludes password from response
- Supports filtering and pagination

**Permissions:**
- Only admins can access this endpoint

---

## TASK 19: Admin Management API - POST

### **POST `/api/admins`** - Create a New Admin
**What you're posting:**
```json
{
  "username": "admin_user",
  "email": "admin@example.com",
  "password": "secure_admin_password",
  "role": "admin"
}
```

**Use Cases:**
- Creating new admin accounts
- Setting up additional administrators
- Initial admin account creation

**What happens:**
- Creates a new user with role="admin"
- Password is hashed before storage
- Sets `created_at` timestamp
- Sets `is_active` to true by default
- Returns created admin (without password)

**Permissions:**
- Only existing admins can create new admin accounts

---

## TASK 20: Admin Management API - Demote

### **PATCH `/api/admins/{user_id}/demote`** - Demote Admin to User
**What you're patching:**
- Changes admin role to regular user

**Use Cases:**
- Removing admin privileges
- Demoting admin who no longer needs access
- Security: removing compromised admin access

**What happens:**
- Changes role from "admin" to "user"
- User loses admin permissions immediately
- Updates `updated_at` timestamp

**Permissions:**
- Only admins can demote other admins
- Cannot demote yourself (prevents lockout)
- At least one admin must remain in system

---

## TASK 21: Admin Management API - Promote

### **PATCH `/api/admins/{user_id}/promote`** - Promote User to Admin
**What you're patching:**
- Changes user role to admin

**Use Cases:**
- Granting admin privileges to trusted users
- Promoting users to administrators
- Adding new administrators

**What happens:**
- Changes role from "user" to "admin"
- User gains admin permissions immediately
- Updates `updated_at` timestamp

**Permissions:**
- Only admins can promote users to admin

---

## Summary: What Gets Created/Updated/Deleted

### **Startup Synchronization (Automatic on API Start):**
- ✅ **Stock Prices:** POST - Add new records from last stored date to today for all companies
- ✅ **Financial Metrics:** PUT - Update the one record per company with current metrics
- ✅ **Market Indices:** POST - Add new records from last stored date to today
- ✅ **Sector Performance:** POST - Add new records from last stored date to today

### **Companies:**
- ✅ **POST**: Create new company (automated - fetches from yfinance: company info, financial metrics, and **complete historical stock prices**)
- ✅ **PUT**: Replace entire company record
- ✅ **PATCH**: Update specific fields (sector, name, market cap)
- ✅ **DELETE**: Soft delete company (marks as deleted, preserves data)

### **News Articles:**
- ✅ **POST**: Ingest new articles (title, content, date, source, ticker, sentiment)
- ✅ **PUT**: Replace entire article document
- ✅ **PATCH**: Update specific fields (ticker, sentiment, title)
- ✅ **DELETE**: Soft delete article (marks as deleted, preserves document)

### **Stock Prices:**
- ✅ **Automatic on Startup:** POST - Add new records from last date to today (for all companies)
- ⚠️ **Manual POST**: Manual price entry (if needed for data gaps)
- ⚠️ **PATCH**: Correct price data (if errors found)
- ⚠️ **DELETE**: Soft delete price records (marks as deleted, preserves data)

### **Financial Metrics:**
- ✅ **Automatic on Startup:** PUT - Update the one record per company with current metrics
- ⚠️ **Manual PATCH**: Update metrics (PE ratio, dividend yield, beta)

### **Market Indices:**
- ✅ **Automatic on Startup:** POST - Add new records from last date to today

### **Sector Performance:**
- ✅ **Automatic on Startup:** POST - Add new records from last date to today

### **Users:**
- ✅ **POST**: Create new user account
- ✅ **GET**: List all users / Get user details
- ✅ **PUT**: Replace entire user record
- ✅ **PATCH**: Update specific user fields (email, role, is_active)
- ✅ **DELETE**: Soft delete user (marks as deleted, preserves account)
- ✅ **PATCH /restore**: Restore soft-deleted user
- ✅ **PATCH /password**: Change user password
- ✅ **PATCH /role**: Change user role

### **Admins:**
- ✅ **GET**: List all admin accounts
- ✅ **POST**: Create new admin account
- ✅ **PATCH /promote**: Promote user to admin
- ✅ **PATCH /demote**: Demote admin to user

---

## Key Design Decisions Needed

1. **Cascade Deletes:** When deleting a company, should related stock prices be deleted too?
   - Recommendation: **No** - prevent deletion if stock prices exist, or require explicit flag

2. **Upsert Behavior:** Should PUT create if company doesn't exist, or return 404?
   - Recommendation: **Return 404** - use POST to create, PUT to update

3. **Validation:** What validations are needed?
   - Ticker format (uppercase, alphanumeric, max length)
   - Market cap (positive numbers)
   - Dates (not in future for stock prices)
   - Required vs optional fields

4. **Permissions:** Who can create/update/delete?
   -  only? Or all users?
   - This relates to the OAuth/JWT task (Level 3)

5. **Soft Deletes:** Should deletes be permanent or soft (mark as deleted)?
   - **Decision: Soft Deletes Only** - All DELETE operations use soft delete
   - Records are marked with `deleted_at` timestamp (or `is_deleted` flag)
   - Records remain in database but are excluded from queries
   - Can be restored later if needed
   - Preserves data integrity and allows recovery

---

## Use Case Examples

### Scenario 1: Adding a New Company to Track (Automated)
```
POST /api/companies
{
  "ticker": "NVDA"
}
```

**What happens automatically:**
1. System checks if NVDA exists in database → Not found
2. Fetches from yfinance:
   - Company info (name: "NVIDIA Corporation", sector: "Technology", etc.)
   - Financial metrics (PE ratio, dividend yield, beta, market cap)
   - **Complete historical stock prices** (all trading days from IPO to today)
3. Inserts into database:
   - `companies` table: 1 record
   - `financial_metrics` table: 1 record
   - `stock_prices` table: ~5000+ historical records (all available dates)
4. Returns: Created company with summary (e.g., "Inserted 5,234 stock price records")

### Scenario 2: Company Changes Sector
```
PATCH /api/companies/AAPL
{
  "sector": "Consumer Technology"
}
```

### Scenario 3: Manually Adding News Article
```
POST /api/news/ingest
{
  "title": "Apple Q4 Earnings Beat Expectations",
  "content": "Apple reported strong earnings...",
  "published_date": "2024-01-15T16:00:00Z",
  "source": "Financial Times",
  "ticker": "AAPL"
}
```

### Scenario 4: Correcting Mis-tagged News Article
```
PATCH /api/news/abc123
{
  "ticker": "MSFT"  // Was incorrectly tagged as AAPL
}
```

### Scenario 5: Soft Deleting Test Data
```
DELETE /api/companies/TEST  // Soft deletes, can be restored
DELETE /api/news/test-article-id  // Soft deletes, can be restored
```

### Scenario 6: Creating a New User
```
POST /api/users
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password",
  "role": "user"
}
```

### Scenario 7: Promoting User to Admin
```
PATCH /api/users/123/role
{
  "role": "admin"
}
```

### Scenario 8: Soft Deleting a User
```
DELETE /api/users/123  // Soft deletes, preserves account data
```

### Scenario 9: Restoring a Soft-Deleted User
```
PATCH /api/users/123/restore  // Restores the user account
```

---

This design gives you full control over the data in your system, allowing manual management when automatic collection isn't sufficient or when corrections are needed.

## Important Notes on Soft Deletes

**All DELETE operations in this system use soft delete:**
- Records are never permanently removed from the database
- `deleted_at` timestamp (or `is_deleted` flag) marks records as deleted
- All GET queries automatically filter out soft-deleted records
- Soft-deleted records can be restored if needed
- This preserves data integrity and allows recovery from mistakes

**Database Schema Requirements:**
- All tables should include `deleted_at` column (DATETIME, nullable)
- Or use `is_deleted` boolean flag (default false)
- Index on `deleted_at` for query performance
- Firestore documents should include `deleted_at` field (timestamp, nullable)

**Query Behavior:**
- All SELECT queries should include `WHERE deleted_at IS NULL` (or `WHERE is_deleted = false`)
- Admin endpoints may optionally include soft-deleted records with a query parameter
- Restore endpoints set `deleted_at` back to NULL

