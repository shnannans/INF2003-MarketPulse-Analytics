<?php
// config/database.php - Local database configuration

// MySQL Configuration (match your data_collection.py)
define('DB_HOST', 'localhost');
define('DB_NAME', 'financial_db');
define('DB_USER', 'root');
define('DB_PASS', '');  // XAMPP default is empty
define('DB_PORT', 3307);

// MongoDB Configuration
define('MONGO_HOST', 'localhost');
define('MONGO_PORT', 27017);
define('MONGO_DB', 'financial_db');
define('MONGO_COLLECTION', 'financial_news');

// Database connection functions
function getMySQLConnection() {
    try {
        $pdo = new PDO(
            "mysql:host=" . DB_HOST . ";dbname=" . DB_NAME . ";port=" . DB_PORT . ";charset=utf8mb4",
            DB_USER,
            DB_PASS,
            [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
            ]
        );
        return $pdo;
    } catch (PDOException $e) {
        error_log("MySQL connection failed: " . $e->getMessage());
        throw new Exception("Database connection failed: " . $e->getMessage());
    }
}

function getMongoCollection($collectionName = MONGO_COLLECTION) {
    try {
        // Check if vendor autoload exists before requiring it
        $autoloadPath = __DIR__ . '/../vendor/autoload.php';
        if (!file_exists($autoloadPath)) {
            throw new Exception("MongoDB dependencies not installed. Run: composer require mongodb/mongodb");
        }
        
        require_once $autoloadPath;
        $client = new MongoDB\Client("mongodb://" . MONGO_HOST . ":" . MONGO_PORT);
        return $client->selectDatabase(MONGO_DB)->selectCollection($collectionName);
    } catch (Exception $e) {
        error_log("MongoDB connection failed: " . $e->getMessage());
        return null; // Return null instead of throwing exception
    }
}

// Test database connectivity
function testConnections() {
    $results = ['mysql' => false, 'mongodb' => false];
    
    try {
        $pdo = getMySQLConnection();
        $stmt = $pdo->query("SHOW TABLES");
        $results['mysql'] = $stmt->rowCount() > 0;
    } catch (Exception $e) {
        error_log("MySQL test failed: " . $e->getMessage());
    }
    
    try {
        $collection = getMongoCollection();
        $results['mongodb'] = ($collection !== null);
    } catch (Exception $e) {
        error_log("MongoDB test failed: " . $e->getMessage());
    }
    
    return $results;
}
?>