<?php
header("Content-Type: application/json");
// Mock sectors
echo json_encode([
  "sectors" => [
    ["sector"=>"Technology","change_percent"=>1.2,"sentiment"=>0.2],
    ["sector"=>"Financials","change_percent"=>-0.3,"sentiment"=>-0.05],
    ["sector"=>"Energy","change_percent"=>2.5,"sentiment"=>0.5]
  ]
]);