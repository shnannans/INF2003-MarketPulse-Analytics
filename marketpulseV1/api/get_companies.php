<?php
// api/get_companies.php - Updated to use config
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once __DIR__ . '/../config/database.php';

try {
    $pdo = getMySQLConnection();
    
    $stmt = $pdo->query("
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
    ");
    
    $companies = $stmt->fetchAll();
    
    echo json_encode([
        "companies" => $companies,
        "count" => count($companies),
        "status" => "success"
    ]);
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "error" => $e->getMessage(),
        "status" => "error"
    ]);
}
?>

<?php
// api/get_stock_analysis.php - Updated with enhanced data
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once __DIR__ . '/../config/database.php';

$ticker = strtoupper($_GET['ticker'] ?? 'AAPL');
$days = intval($_GET['days'] ?? 90);

try {
    $pdo = getMySQLConnection();

    // Get enhanced stock price data with technical indicators
    $stmt = $pdo->prepare("
        SELECT 
            date,
            open_price,
            high_price,
            low_price,
            close_price,
            adj_close,
            volume,
            ma_5,
            ma_20,
            ma_50,
            ma_200,
            price_change_pct,
            volume_change_pct
        FROM stock_prices
        WHERE ticker = :ticker 
            AND date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        ORDER BY date DESC
        LIMIT 500
    ");
    
    $stmt->execute(['ticker' => $ticker, 'days' => $days]);
    $analysis = $stmt->fetchAll();
    
    // Calculate additional metrics
    if (!empty($analysis)) {
        $prices = array_column($analysis, 'close_price');
        $current_price = $prices[0];
        $volatility = calculateVolatility($prices);
        
        // Get company information
        $companyStmt = $pdo->prepare("SELECT * FROM companies WHERE ticker = :ticker");
        $companyStmt->execute(['ticker' => $ticker]);
        $company = $companyStmt->fetch();
        
        echo json_encode([
            'ticker' => $ticker,
            'company' => $company,
            'current_price' => $current_price,
            'volatility' => round($volatility, 4),
            'analysis' => $analysis,
            'count' => count($analysis),
            'status' => 'success'
        ]);
    } else {
        echo json_encode([
            'ticker' => $ticker,
            'error' => 'No data found for ticker',
            'status' => 'error'
        ]);
    }

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'error' => $e->getMessage(),
        'status' => 'error'
    ]);
}

function calculateVolatility($prices) {
    if (count($prices) < 2) return 0;
    
    $returns = [];
    for ($i = 1; $i < count($prices); $i++) {
        if ($prices[$i] != 0) {
            $returns[] = ($prices[$i-1] - $prices[$i]) / $prices[$i];
        }
    }
    
    if (empty($returns)) return 0;
    
    $mean = array_sum($returns) / count($returns);
    $variance = 0;
    foreach ($returns as $return) {
        $variance += pow($return - $mean, 2);
    }
    $variance = $variance / count($returns);
    
    return sqrt($variance) * sqrt(252) * 100; // Annualized volatility
}
?>

<?php
// api/get_indices.php - Updated to use real data
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once __DIR__ . '/../config/database.php';

$days = intval($_GET['days'] ?? 30);

try {
    $pdo = getMySQLConnection();
    
    // Get real market indices data
    $stmt = $pdo->prepare("
        SELECT 
            symbol,
            index_name,
            date,
            close_price,
            change_pct
        FROM market_indices
        WHERE date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
        ORDER BY symbol, date ASC
    ");
    $stmt->execute(['days' => $days]);
    $indicesData = $stmt->fetchAll();
    
    if (empty($indicesData)) {
        // Fallback to mock data if no real data available
        $dates = [];
        for ($i = $days - 1; $i >= 0; $i--) {
            $dates[] = date('Y-m-d', strtotime("-{$i} days"));
        }
        
        echo json_encode([
            "trend" => array_map(function($date) { return ["date" => $date]; }, $dates),
            "indices" => [
                ["name" => "S&P 500", "values" => array_map(function($i) { return 4300 + rand(-20,20); }, $dates)],
                ["name" => "NASDAQ", "values" => array_map(function($i) { return 15000 + rand(-50,50); }, $dates)]
            ],
            "summary" => [
                ["name" => "S&P 500", "change_percent" => rand(-200, 200) / 100],
                ["name" => "NASDAQ", "change_percent" => rand(-200, 200) / 100]
            ],
            "status" => "success",
            "note" => "Using mock data - run data collection to get real indices"
        ]);
    } else {
        // Process real indices data
        $groupedData = [];
        foreach ($indicesData as $row) {
            $groupedData[$row['index_name']][] = $row;
        }
        
        $trend = [];
        $indices = [];
        $summary = [];
        
        $allDates = array_unique(array_column($indicesData, 'date'));
        sort($allDates);
        $trend = array_map(function($date) { return ["date" => $date]; }, $allDates);
        
        foreach ($groupedData as $indexName => $data) {
            $values = array_column($data, 'close_price');
            $indices[] = ["name" => $indexName, "values" => array_map('floatval', $values)];
            
            if (count($values) > 1) {
                $latestChange = end($data)['change_pct'];
                $summary[] = ["name" => $indexName, "change_percent" => round($latestChange, 2)];
            }
        }
        
        echo json_encode([
            "trend" => $trend,
            "indices" => $indices,
            "summary" => $summary,
            "status" => "success"
        ]);
    }
    
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "error" => $e->getMessage(),
        "status" => "error"
    ]);
}
?>

<?php
// api/get_news.php - Updated to use config
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once __DIR__ . '/../config/database.php';

try {
    $collection = getMongoCollection();

    $ticker = strtoupper($_GET['ticker'] ?? '');
    $days = intval($_GET['days'] ?? 7);
    $sentiment = $_GET['sentiment'] ?? '';
    $limit = intval($_GET['limit'] ?? 20);

    // Build query filter
    $cutoff = new MongoDB\BSON\UTCDateTime((time() - $days * 86400) * 1000);
    $filter = ['published_date' => ['$gte' => $cutoff]];
    
    if (!empty($ticker)) {
        $filter['ticker'] = $ticker;
    }
    
    // Sentiment filter
    if (!empty($sentiment)) {
        switch ($sentiment) {
            case 'positive':
                $filter['sentiment_analysis.overall_score'] = ['$gt' => 0.1];
                break;
            case 'negative':
                $filter['sentiment_analysis.overall_score'] = ['$lt' => -0.1];
                break;
            case 'neutral':
                $filter['sentiment_analysis.overall_score'] = [
                    '$gte' => -0.1,
                    '$lte' => 0.1
                ];
                break;
        }
    }

    $options = [
        'limit' => $limit,
        'sort' => ['published_date' => -1],
        'projection' => [
            'article_id' => 1,
            'ticker' => 1,
            'title' => 1,
            'content' => 1,
            'published_date' => 1,
            'source' => 1,
            'sentiment_analysis' => 1,
            'extracted_entities' => 1,
            'metadata' => 1
        ]
    ];

    $cursor = $collection->find($filter, $options);
    $articles = iterator_to_array($cursor);

    // Convert MongoDB ObjectId to string and format dates
    foreach ($articles as &$article) {
        $article['_id'] = (string) $article['_id'];
        if (isset($article['published_date']) && $article['published_date'] instanceof MongoDB\BSON\UTCDateTime) {
            $article['published_date'] = $article['published_date']->toDateTime()->format('c');
        }
    }

    echo json_encode([
        'articles' => array_values($articles),
        'count' => count($articles),
        'filters' => [
            'ticker' => $ticker,
            'days' => $days,
            'sentiment' => $sentiment
        ],
        'status' => 'success'
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "error" => $e->getMessage(),
        "status" => "error"
    ]);
}
?>