<?php
// Bibliothèque commune de l'espace membre (sessions, base SQLite, CSRF).
$cfgf = __DIR__ . '/config.php';
$CFG = file_exists($cfgf) ? require $cfgf : require __DIR__ . '/config.sample.php';
session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'secure' => !empty($_SERVER['HTTPS']), 'httponly' => true, 'samesite' => 'Lax']);
session_start();
function db() {
  static $p = null;
  if ($p) return $p;
  $p = new PDO('sqlite:' . __DIR__ . '/../private/members.sqlite');
  $p->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
  $p->exec('CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT, pass TEXT, provider TEXT, created TEXT)');
  return $p;
}
function user() {
  if (empty($_SESSION['uid'])) return null;
  $s = db()->prepare('SELECT id,email,name FROM members WHERE id=?'); $s->execute([$_SESSION['uid']]);
  return $s->fetch(PDO::FETCH_ASSOC) ?: null;
}
function csrf() { if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(16)); return $_SESSION['csrf']; }
function login_as($id) { session_regenerate_id(true); $_SESSION['uid'] = (int)$id; }
function upsert_social($email, $name, $prov) {
  $s = db()->prepare('SELECT id FROM members WHERE email=?'); $s->execute([$email]); $id = $s->fetchColumn();
  if (!$id) { db()->prepare('INSERT INTO members(email,name,pass,provider,created) VALUES(?,?,?,?,?)')->execute([$email, $name, null, $prov, date('c')]); $id = db()->lastInsertId(); }
  return $id;
}
function http($url, $post = null) {
  $c = curl_init($url);
  curl_setopt_array($c, [CURLOPT_RETURNTRANSFER => 1, CURLOPT_TIMEOUT => 15]);
  if ($post) { curl_setopt($c, CURLOPT_POST, 1); curl_setopt($c, CURLOPT_POSTFIELDS, http_build_query($post)); }
  $r = curl_exec($c); curl_close($c);
  return json_decode($r, true);
}
