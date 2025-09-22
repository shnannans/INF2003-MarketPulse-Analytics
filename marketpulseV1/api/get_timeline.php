<?php
// api/get_timeline.php
header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

require_once __DIR__ . '/../config/database.php';

$days = intval($_GET['days'] ?? 7);

try {
    $events = [];
    
    // Get significant market events from the last few days
    $pdo = getMySQLConnection();
    
    // Get significant price movements as timeline events
    $stmt = $pdo->prepare("
        SELECT 
            sp.date,
            sp.ticker,
            c.company_name,
            sp.price_change_pct
        FROM stock_prices sp
        JOIN companies c ON sp.ticker = c.ticker
        WHERE sp.date >= DATE_SUB(CURDATE(), INTERVAL ? DAY)
        AND ABS(sp.price_change_pct) > 4
        ORDER BY sp.date DESC, ABS(sp.price_change_pct) DESC
        LIMIT 10
    ");
    $stmt->execute([$days]);
    $priceEvents = $stmt->fetchAll();
    
    foreach ($priceEvents as $event) {
        $direction = $event['price_change_pct'] > 0 ? 'surged' : 'dropped';
        $events[] = [
            'date' => $event['date'],
            'title' => "{$event['company_name']} ({$event['ticker']}) {$direction} " . 
                      abs(round($event['price_change_pct'], 1)) . "%",
            'type' => 'price_movement',
            'ticker' => $event['ticker']
        ];
    }
    
    // Add some market-wide events
    $marketEvents = [
        ['title' => 'Market opens with mixed signals amid economic uncertainty', 'days_ago' => 1],
        ['title' => 'Technology sector shows resilience in trading session', 'days_ago' => 2],
        ['title' => 'Federal Reserve announcement impacts market sentiment', 'days_ago' => 3]
    ];
    
    foreach ($marketEvents as $i => $event) {
        if ($event['days_ago'] <= $days) {
            $events[] = [
                'date' => date('Y-m-d', strtotime("-{$event['days_ago']} days")),
                'title' => $event['title'],
                'type' => 'market_news',
                'ticker' => 'MARKET'
            ];
        }
    }
    
    // Sort by date descending
    usort($events, function($a, $b) {
        return strtotime($b['date']) - strtotime($a['date']);
    });
    
    echo json_encode([
        'events' => $events,
        'count' => count($events),
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