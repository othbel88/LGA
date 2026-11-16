<?php
// Garde commune : POST uniquement, piège anti-robot, même origine obligatoire, limite d'envois par IP et par site.
function guard($name, $max, $window) {
  if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !empty($_POST['website'])) { http_response_code(400); exit; }
  $o = $_SERVER['HTTP_ORIGIN'] ?? ($_SERVER['HTTP_REFERER'] ?? '');
  $oh = $o !== '' ? parse_url($o, PHP_URL_HOST) : null;
  $hh = preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? '');
  if ($oh === null || $oh !== $hh) { http_response_code(403); exit; } // absence d'Origin/Referer = refusé, pas ignoré
  $ip = $_SERVER['REMOTE_ADDR'] ?? '0';
  $dir = __DIR__ . '/.rl';
  if (!is_dir($dir)) { @mkdir($dir, 0700); @file_put_contents($dir . '/.htaccess', "Require all denied\n"); } // doublon si l'hébergeur a effacé le dossier vide du dépôt
  $f = $dir . '/' . preg_replace('/[^a-z0-9]/', '', $name) . '_' . md5($hh . '|' . $ip); // propre à ce site (pas sys_get_temp_dir, partageable en mutualisé)
  $now = time(); $hits = [];
  if (is_file($f)) { $hits = array_filter(array_map('intval', explode(',', (string)@file_get_contents($f))), function ($t) use ($now, $window) { return $t > $now - $window; }); }
  if (count($hits) >= $max) { http_response_code(429); exit; }
  $hits[] = $now;
  @file_put_contents($f, implode(',', $hits), LOCK_EX);
}
