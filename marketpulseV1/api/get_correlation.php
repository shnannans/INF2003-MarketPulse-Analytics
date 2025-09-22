<?php
header("Content-Type: application/json");
// Replace with real correlation algorithm that analyzes price & sentiment windows around a date
$ticker = $_GET['ticker'] ?? 'AAPL';
$date = $_GET['date'] ?? null;
$mockCorr = rand(-100,100)/100;
echo json_encode(["ticker"=>$ticker, "date"=>$date, "correlation"=>$mockCorr]);
