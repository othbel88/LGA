<?php
// Garde commune : POST uniquement, piège anti-robot, même origine, limite d'envois par IP.
function guard($name, $max, $window) {
  if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !empty($_POST['website'])) { http_response_code(400); exit; }
  $o = $_SERVER['HTTP_ORIGIN'] ?? ($_SERVER['HTTP_REFERER'] ?? '');
  if ($o !== '') {
    $oh = parse_url($o, PHP_URL_HOST);
    $hh = preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? '');
    if ($oh !== $hh) { http_response_code(403); exit; }
  }
  $ip = $_SERVER['REMOTE_ADDR'] ?? '0';
  $f = sys_get_temp_dir() . '/lga_rl_' . $name . '_' . md5($ip);
  $now = time(); $hits = [];
  if (is_file($f)) { $hits = array_filter(array_map('intval', explode(',', (string)@file_get_contents($f))), function ($t) use ($now, $window) { return $t > $now - $window; }); }
  if (count($hits) >= $max) { http_response_code(429); exit; }
  $hits[] = $now;
  @file_put_contents($f, implode(',', $hits), LOCK_EX);
}
