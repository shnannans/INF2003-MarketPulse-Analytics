<?php
header("Content-Type: application/json");
// Mock indices data, replace with real queries
$dates = [];
for ($i=6; $i>=0; $i--) $dates[] = date('Y-m-d', strtotime("-{$i} days"));
$sp500 = array_map(fn($i) => 4300 + rand(-20,20) + $i, $dates);
$nasdaq = array_map(fn($i) => 15000 + rand(-50,50) + $i, $dates);

echo json_encode([
  "trend" => array_map(fn($d)=>["date"=>$d], $dates),
  "indices" => [
    ["name"=>"S&P 500", "values" => $sp500],
    ["name"=>"NASDAQ", "values" => $nasdaq]
  ],
  "summary" => [
    ["name"=>"S&P 500", "change_percent" => round((end($sp500)-$sp500[0])/$sp500[0]*100,2)],
    ["name"=>"NASDAQ", "change_percent" => round((end($nasdaq)-$nasdaq[0])/$nasdaq[0]*100,2)]
  ]
]);