<?php
// api/get_news.php
require_once __DIR__ . '/../vendor/autoload.php';  // Composer autoload for MongoDB
use MongoDB\Client;

header("Content-Type: application/json");
header("Access-Control-Allow-Origin: *");

try {
    $client = new Client("mongodb://localhost:27017");
    $collection = $client->financial_db->financial_news;  // Updated database name

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