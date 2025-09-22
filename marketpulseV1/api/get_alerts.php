<?php
// api/get_alerts.php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once __DIR__ . '/../config/database.php';

try {
    $pdo = getMySQLConnection();
    
    // Generate alerts based on price movements and sentiment
    $alerts = [];
    
    // Check for significant price movements in last 24 hours
    $stmt = $pdo->prepare("
        SELECT 
            sp1.ticker,
            sp1.close_price as current_price,
            sp2.close_price as prev_price,
            ((sp1.close_price - sp2.close_price) / sp2.close_price * 100) as price_change_pct,
            c.company_name
        FROM stock_prices sp1
        JOIN stock_prices sp2 ON sp1.ticker = sp2.ticker 
        JOIN companies c ON sp1.ticker = c.ticker
        WHERE sp1.date = CURDATE() - INTERVAL 1 DAY
        AND sp2.date = CURDATE() - INTERVAL 2 DAY
        AND ABS((sp1.close_price - sp2.close_price) / sp2.close_price * 100) > 3
        ORDER BY ABS((sp1.close_price - sp2.close_price) / sp2.close_price * 100) DESC
        LIMIT 5
    ");
    $stmt->execute();
    $priceAlerts = $stmt->fetchAll();
    
    foreach ($priceAlerts as $alert) {
        $direction = $alert['price_change_pct'] > 0 ? 'increased' : 'decreased';
        $alerts[] = [
            'ticker' => $alert['ticker'],
            'type' => 'price_movement',
            'message' => "{$alert['company_name']} ({$alert['ticker']}) {$direction} by " . 
                        abs(round($alert['price_change_pct'], 2)) . "% in last 24 hours",
            'severity' => abs($alert['price_change_pct']) > 5 ? 'high' : 'medium'
        ];
    }
    
    // Add some sentiment-based alerts (mock for now since we need correlation)
    $alerts[] = [
        'ticker' => 'AAPL',
        'type' => 'sentiment',
        'message' => 'High positive sentiment spike detected with recent news coverage',
        'severity' => 'medium'
    ];
    
    echo json_encode([
        'alerts' => $alerts,
        'count' => count($alerts),
        'status' => 'success'
    ]);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'error' => $e->getMessage(),
        'status' => 'error'
    ]);
}
?>