<?php
// api/get_stock_analysis.php - Fixed to use config and handle missing columns
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once __DIR__ . '/../config/database.php';

$ticker = strtoupper($_GET['ticker'] ?? 'AAPL');
$days = intval($_GET['days'] ?? 90);

try {
    $pdo = getMySQLConnection();

    // First check what columns exist
    $stmt = $pdo->query("SHOW COLUMNS FROM stock_prices");
    $columns = $stmt->fetchAll(PDO::FETCH_COLUMN);
    
    // Build dynamic query based on available columns
    $selectColumns = [
        'date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume'
    ];
    
    $movingAvgColumns = [];
    if (in_array('ma_5', $columns)) $movingAvgColumns[] = 'ma_5';
    if (in_array('ma_20', $columns)) $movingAvgColumns[] = 'ma_20';
    if (in_array('ma_50', $columns)) $movingAvgColumns[] = 'ma_50';
    if (in_array('ma_200', $columns)) $movingAvgColumns[] = 'ma_200';
    if (in_array('price_change_pct', $columns)) $movingAvgColumns[] = 'price_change_pct';
    if (in_array('volume_change_pct', $columns)) $movingAvgColumns[] = 'volume_change_pct';
    
    $allColumns = array_merge($selectColumns, $movingAvgColumns);
    
    // If moving averages don't exist, calculate them on the fly
    if (empty($movingAvgColumns)) {
        $query = "
            SELECT 
                date,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                AVG(close_price) OVER (
                    ORDER BY date 
                    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                ) as ma_5,
                AVG(close_price) OVER (
                    ORDER BY date 
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) as ma_20,
                LAG(close_price, 1) OVER (ORDER BY date) as prev_close
            FROM stock_prices
            WHERE ticker = :ticker 
                AND date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
            ORDER BY date DESC
            LIMIT 500
        ";
    } else {
        $query = "
            SELECT " . implode(', ', $allColumns) . "
            FROM stock_prices
            WHERE ticker = :ticker 
                AND date >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
            ORDER BY date DESC
            LIMIT 500
        ";
    }
    
    $stmt = $pdo->prepare($query);
    $stmt->execute(['ticker' => $ticker, 'days' => $days]);
    $analysis = $stmt->fetchAll();
    
    // Calculate additional metrics if data exists
    $currentPrice = null;
    $volatility = 0;
    $company = null;
    
    if (!empty($analysis)) {
        $prices = array_column($analysis, 'close_price');
        $currentPrice = $prices[0];
        $volatility = calculateVolatility($prices);
        
        // Get company information
        try {
            $companyStmt = $pdo->prepare("SELECT * FROM companies WHERE ticker = :ticker");
            $companyStmt->execute(['ticker' => $ticker]);
            $company = $companyStmt->fetch();
        } catch (Exception $e) {
            // Company table might not exist or have different structure
            $company = ['ticker' => $ticker, 'name' => $ticker];
        }
    }
    
    echo json_encode([
        'ticker' => $ticker,
        'company' => $company,
        'current_price' => $currentPrice,
        'volatility' => round($volatility, 4),
        'analysis' => $analysis,
        'count' => count($analysis),
        'status' => 'success',
        'available_columns' => $allColumns
    ]);

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