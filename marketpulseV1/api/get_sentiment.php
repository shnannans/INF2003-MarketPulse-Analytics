<?php
// api/get_sentiment.php
require_once __DIR__ . '/../vendor/autoload.php';
use MongoDB\Client;

header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

$ticker = strtoupper($_GET['ticker'] ?? '');
$days = intval($_GET['days'] ?? 7);

try {
    $client = new Client("mongodb://localhost:27017");
    $collection = $client->financial_db->financial_news;  // Updated database name

    $cutoff = new MongoDB\BSON\UTCDateTime((time() - $days * 86400) * 1000);
    $match = ['published_date' => ['$gte' => $cutoff]];
    
    if (!empty($ticker)) {
        $match['ticker'] = $ticker;
    }

    // Aggregate statistics
    $pipeline = [
        ['$match' => $match],
        [
            '$group' => [
                '_id' => null,
                'total_articles' => ['$sum' => 1],
                'avg_sentiment' => ['$avg' => '$sentiment_analysis.overall_score'],
                'positive_count' => [
                    '$sum' => [
                        '$cond' => [
                            ['$gt' => ['$sentiment_analysis.overall_score', 0.1]], 
                            1, 
                            0
                        ]
                    ]
                ],
                'negative_count' => [
                    '$sum' => [
                        '$cond' => [
                            ['$lt' => ['$sentiment_analysis.overall_score', -0.1]], 
                            1, 
                            0
                        ]
                    ]
                ],
                'neutral_count' => [
                    '$sum' => [
                        '$cond' => [
                            [
                                '$and' => [
                                    ['$gte' => ['$sentiment_analysis.overall_score', -0.1]], 
                                    ['$lte' => ['$sentiment_analysis.overall_score', 0.1]]
                                ]
                            ], 
                            1, 
                            0
                        ]
                    ]
                ]
            ]
        ]
    ];

    $statsResult = iterator_to_array($collection->aggregate($pipeline));
    $stats = $statsResult[0] ?? [
        'total_articles' => 0,
        'avg_sentiment' => 0,
        'positive_count' => 0,
        'negative_count' => 0,
        'neutral_count' => 0
    ];
    
    // Remove MongoDB _id
    unset($stats['_id']);

    // Daily trend analysis
    $trendPipeline = [
        ['$match' => $match],
        [
            '$group' => [
                '_id' => [
                    'date' => [
                        '$dateToString' => [
                            'format' => "%Y-%m-%d", 
                            'date' => '$published_date'
                        ]
                    ]
                ],
                'avg_sentiment' => ['$avg' => '$sentiment_analysis.overall_score'],
                'article_count' => ['$sum' => 1]
            ]
        ],
        ['$sort' => ['_id.date' => 1]]
    ];

    $trendsResult = iterator_to_array($collection->aggregate($trendPipeline));

    echo json_encode([
        'statistics' => $stats,
        'trends' => $trendsResult,
        'filters' => [
            'ticker' => $ticker,
            'days' => $days
        ],
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