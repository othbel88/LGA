<?php
// Inscription newsletter : enregistre l'adresse (api/subscribers.csv, protégé par .htaccess) et prévient le Riad.
require __DIR__ . '/guard.php';
guard('subscribe', 5, 3600);
$e = filter_var($_POST['email'] ?? '', FILTER_VALIDATE_EMAIL);
if (!$e || strlen($e) > 254) { http_response_code(422); exit; }
$safe = preg_match('/^[=+\-@\t\r]/', $e) ? "'" . $e : $e; // neutralise les formules Excel
$line = date('c') . ',"' . str_replace('"', '""', $safe) . "\"\n";
$ok = file_put_contents(__DIR__ . '/subscribers.csv', $line, FILE_APPEND | LOCK_EX); // à l'intérieur du site : .csv déjà bloqué par .htaccess, pas de pari sur la structure des dossiers OVH
if ($ok === false) { error_log('LGA subscribe.php: échec d\'écriture dans ' . __DIR__ . '/subscribers.csv'); }
@mail('legrandalcazar@gmail.com', 'Nouvelle inscription newsletter', $e, "From: no-reply@legrandalcazar.com");
http_response_code(200);
