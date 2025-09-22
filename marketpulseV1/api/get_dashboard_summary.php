<?php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

// Debug: Check if config file exists
$configPath = __DIR__ . '/../config/database.php';
if (!file_exists($configPath)) {
    echo json_encode([
        "error" => "Config file not found at: " . $configPath,
        "status" => "error"
    ]);
    exit;
}

require_once $configPath;

try {
    // Test MySQL connection first
    $pdo = getMySQLConnection();
    
    // Get MySQL statistics
    $companyCount = 0;
    $priceRecords = 0;
    $latestDate = 'N/A';
    
    try {
        $stmt = $pdo->query("SELECT COUNT(*) as company_count FROM companies");
        $result = $stmt->fetch();
        $companyCount = $result ? $result['company_count'] : 0;
    } catch (Exception $e) {
        error_log("Companies query failed: " . $e->getMessage());
    }
    
    try {
        $stmt = $pdo->query("SELECT COUNT(*) as price_records FROM stock_prices");
        $result = $stmt->fetch();
        $priceRecords = $result ? $result['price_records'] : 0;
    } catch (Exception $e) {
        error_log("Stock prices query failed: " . $e->getMessage());
    }
    
    try {
        $stmt = $pdo->query("SELECT MAX(date) as latest_date FROM stock_prices");
        $result = $stmt->fetch();
        $latestDate = $result ? $result['latest_date'] : 'N/A';
    } catch (Exception $e) {
        error_log("Latest date query failed: " . $e->getMessage());
    }
    
    // Try MongoDB (but don't fail if it doesn't work)
    $totalArticles = 0;
    $recentArticles = 0;
    $avgSentiment = 0;
    
    try {
        if (function_exists('getMongoCollection')) {
            $newsCollection = getMongoCollection();
            if ($newsCollection) {
                $totalArticles = $newsCollection->countDocuments();
                
                $recentCutoff = new MongoDB\BSON\UTCDateTime((time() - 24 * 3600) * 1000);
                $recentArticles = $newsCollection->countDocuments([
                    'published_date' => ['$gte' => $recentCutoff]
                ]);
                
                $avgSentimentPipeline = [
                    ['$group' => ['_id' => null, 'avg_sentiment' => ['$avg' => '$sentiment_analysis.overall_score']]]
                ];
                
                $avgResult = iterator_to_array($newsCollection->aggregate($avgSentimentPipeline));
                $avgSentiment = $avgResult[0]['avg_sentiment'] ?? 0;
            }
        }
    } catch (Exception $e) {
        error_log("MongoDB failed: " . $e->getMessage());
        // Continue with zeros
    }
    
    echo json_encode([
        "total_companies" => $companyCount,
        "total_articles" => $totalArticles,
        "recent_articles" => $recentArticles,
        "total_price_records" => $priceRecords,
        "latest_price_date" => $latestDate,
        "avg_sentiment" => round($avgSentiment, 3),
        "portfolio_value" => "$1,234,567",
        "status" => "success"
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "error" => $e->getMessage(),
        "status" => "error",
        "debug_info" => [
            "config_path" => $configPath,
            "file_exists" => file_exists($configPath)
        ]
    ]);
}
?>