<?php
/*
 * Sisyfos – server för krypterad lagring (0.13.0)
 * Copyright (C) 2026 Agrell Arkitektur. Fri programvara under GNU GPL v3 eller senare.
 *
 * Servern lagrar bara det som redan är krypterat på användarens enhet: valvet (boknyckeln låst
 * med lösenordet och med återställningsnyckeln) och den krypterade bokfilen (.sisyfos). Den ser
 * aldrig lösenordet, boknyckeln eller innehållet.
 *
 * Inloggning: ur lösenordet tar appen 512 bitar med PBKDF2 (valvets salt). De första 256 låser
 * upp boknyckeln och lämnar aldrig enheten; de sista 256 skickas hit som inloggningshemlighet,
 * och servern sparar bara password_hash() av dem.
 *
 * Lagring: inga databaser – JSON-filer med flock. Datamappen läggs utanför webbroten om PHP
 * får skriva där (../../sisyfos-data räknat från den här filen), annars i ./data/ som spärras
 * med .htaccess. Kontots mapp får ett namn som inte går att gissa (HMAC av e-postadressen).
 *
 * Administratör: om api-config.php finns och innehåller 'admin' (sha256 av en adminnyckel) kan
 * den som har nyckeln skapa inbjudningskoder, se konton och ta bort dem. Filen skrivs av
 * publiceringen på GitHub från hemligheten SISYFOS_ADMIN_KEY.
 *
 * Inga cookies, inga CORS-rubriker (bara samma ursprung), ingen loggning av innehåll.
 */

declare(strict_types=1);

const API_VERSION   = 1;
const QUOTA         = 20 * 1024 * 1024;    // per konto: bok + tidigare versioner
const MAX_BOOK      = 10 * 1024 * 1024;    // största enskilda bokfil
const KEEP_HISTORY  = 10;                  // tidigare versioner som sparas
const TOKEN_DAYS    = 90;                  // enhetens inloggning gäller så länge sedan senaste användning
const MAX_TOKENS    = 20;                  // inloggade enheter per konto
const FAIL_WINDOW   = 900;                 // sekunder
const FAIL_ACCOUNT  = 8;                   // misslyckade inloggningar per konto och fönster
const FAIL_IP       = 30;                  // misslyckade försök per IP och fönster
const KDF_NAME      = 'PBKDF2-SHA-256';
const KDF_ITER      = 600000;

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');
header('Referrer-Policy: no-referrer');
header('X-Frame-Options: DENY');

/* ---------- svar och indata ---------- */
function svar(int $status, array $data = []): never {
  http_response_code($status);
  echo json_encode(['ok' => $status < 400] + $data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
  exit;
}
function fel(int $status, string $kod, string $text, array $extra = []): never {
  svar($status, ['error' => $kod, 'message' => $text] + $extra);
}
function body(int $max = 65536): string {
  $raw = file_get_contents('php://input', false, null, 0, $max + 1);
  if ($raw === false) fel(400, 'body', 'Begäran kunde inte läsas.');
  if (strlen($raw) > $max) fel(413, 'too_large', 'Begäran är för stor.');
  return $raw;
}
function json_in(): array {
  $in = json_decode(body(), true);
  if (!is_array($in)) fel(400, 'format', 'Felaktigt format.');
  return $in;
}
function email_norm(mixed $e): string {
  $e = mb_strtolower(trim((string)$e), 'UTF-8');
  if ($e === '' || strlen($e) > 200 || !filter_var($e, FILTER_VALIDATE_EMAIL)) fel(400, 'email', 'E-postadressen ser inte rätt ut.');
  return $e;
}
function b64ok(mixed $s, int $bytes): string {
  $s = (string)$s; $d = base64_decode($s, true);
  if ($d === false || strlen($d) !== $bytes) fel(400, 'format', 'Felaktigt format.');
  return $s;
}
function check_vault(mixed $v): array {
  if (!is_array($v) || !isset($v['id'], $v['kdf']['salt'], $v['kdf']['iter'], $v['pw']['iv'], $v['pw']['ct'])) fel(400, 'vault', 'Valvet saknas eller är ofullständigt.');
  if (($v['kdf']['name'] ?? '') !== KDF_NAME || (int)$v['kdf']['iter'] < 100000) fel(400, 'vault', 'Valvet har okända inställningar.');
  b64ok($v['kdf']['salt'], 16);
  if (strlen(json_encode($v)) > 8192) fel(400, 'vault', 'Valvet är för stort.');
  return $v;
}

/* ---------- datamappen ---------- */
function data_dir(): array {
  static $res = null;
  if ($res) return $res;
  $ute = dirname(__DIR__, 2) . '/sisyfos-data';
  $inne = __DIR__ . '/data';
  foreach ([['outside', $ute], ['inside', $inne]] as [$mode, $dir]) {
    if (!is_dir($dir)) @mkdir($dir, 0700, true);
    if (is_dir($dir) && is_writable($dir)) {
      if ($mode === 'inside') {
        $ht = "# Sisyfos: datamappen ska aldrig visas på webben\nRequire all denied\n<IfModule !mod_authz_core.c>\n  Deny from all\n</IfModule>\nOptions -Indexes\n";
        if (@file_get_contents("$dir/.htaccess") !== $ht) file_put_contents("$dir/.htaccess", $ht, LOCK_EX);
        if (!is_file("$dir/index.html")) file_put_contents("$dir/index.html", '');
      }
      foreach (['acc'] as $sub) if (!is_dir("$dir/$sub")) mkdir("$dir/$sub", 0700);
      return $res = [$mode, $dir];
    }
  }
  fel(500, 'storage', 'Servern kan inte skriva någonstans. Kontrollera rättigheterna för mappen sisyfos/ på webbhotellet.');
}
function dpath(string $rel): string { return data_dir()[1] . '/' . $rel; }
function secret(): string {
  $f = dpath('secret.key');
  if (!is_file($f)) {
    $fp = fopen($f, 'c+'); flock($fp, LOCK_EX);
    if (filesize($f) === 0) { fwrite($fp, bin2hex(random_bytes(32))); fflush($fp); }
    flock($fp, LOCK_UN); fclose($fp); clearstatcache(true, $f);
  }
  $s = trim((string)file_get_contents($f));
  if (strlen($s) !== 64) fel(500, 'storage', 'Serverns nyckelfil är skadad.');
  return $s;
}
function acc_id(string $email): string { return substr(hash_hmac('sha256', 'acc|' . $email, secret()), 0, 40); }
function acc_dir(string $id): string { return dpath('acc/' . $id); }

/* Läs-ändra-skriv en JSON-fil under lås. $fn får datan (eller null) och returnerar ny data eller null för oförändrat. */
function locked_json(string $file, callable $fn): mixed {
  $fp = fopen($file, 'c+');
  if (!$fp || !flock($fp, LOCK_EX)) fel(500, 'storage', 'Servern kunde inte låsa en fil.');
  $raw = stream_get_contents($fp);
  $data = $raw ? json_decode($raw, true) : null;
  try { [$ny, $ret] = $fn($data); }
  finally {
    if (isset($ny) && $ny !== null) { ftruncate($fp, 0); rewind($fp); fwrite($fp, json_encode($ny, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)); fflush($fp); }
    flock($fp, LOCK_UN); fclose($fp);
  }
  return $ret;
}
function read_json(string $file): ?array {
  if (!is_file($file)) return null;
  $fp = fopen($file, 'r'); flock($fp, LOCK_SH); $raw = stream_get_contents($fp); flock($fp, LOCK_UN); fclose($fp);
  $d = json_decode((string)$raw, true);
  return is_array($d) ? $d : null;
}

/* ---------- begränsning av försök ---------- */
function client_key(): string { return 'ip|' . substr(hash_hmac('sha256', $_SERVER['REMOTE_ADDR'] ?? '', secret()), 0, 24); }
function fails(array $keys, bool $add = false): array {
  return locked_json(dpath('rate.json'), function ($d) use ($keys, $add) {
    $d = is_array($d) ? $d : []; $nu = time(); $ut = [];
    foreach ($d as $k => $tider) { $tider = array_values(array_filter($tider, fn($t) => $t > $nu - FAIL_WINDOW)); if ($tider) $d[$k] = $tider; else unset($d[$k]); }
    foreach ($keys as $k) { if ($add) $d[$k][] = $nu; $ut[$k] = count($d[$k] ?? []); }
    return [$d, $ut];
  });
}
function guard(?string $accKey = null): void {
  $keys = [client_key()]; if ($accKey) $keys[] = $accKey;
  $n = fails($keys);
  if ($n[client_key()] >= FAIL_IP || ($accKey && $n[$accKey] >= FAIL_ACCOUNT)) fel(429, 'slow_down', 'För många misslyckade försök. Vänta en kvart och försök igen.');
}
function failed(?string $accKey = null): void { $keys = [client_key()]; if ($accKey) $keys[] = $accKey; fails($keys, true); }

/* ---------- konton och inloggning ---------- */
function acc_file(string $id): string { return acc_dir($id) . '/account.json'; }
function token_hash(string $t): string { return hash('sha256', $t); }
function new_token(array &$acc, string $device): string {
  $t = rtrim(strtr(base64_encode(random_bytes(32)), '+/', '-_'), '=');
  $nu = time();
  $acc['tokens'] = array_values(array_filter($acc['tokens'] ?? [], fn($x) => $x['used'] > $nu - TOKEN_DAYS * 86400));
  usort($acc['tokens'], fn($a, $b) => $b['used'] <=> $a['used']);
  $acc['tokens'] = array_slice($acc['tokens'], 0, MAX_TOKENS - 1);
  $acc['tokens'][] = ['h' => token_hash($t), 'device' => mb_substr($device, 0, 60), 'created' => $nu, 'used' => $nu];
  return $t;
}
/* Kräver giltig token. Returnerar [kontots id, kontot]. Uppdaterar 'used' högst en gång i timmen. */
function auth(): array {
  // Egen rubrik i första hand: Apache med PHP som CGI/FPM tar ofta bort Authorization.
  $h = $_SERVER['HTTP_X_SISYFOS_TOKEN'] ?? $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
  if (!preg_match('/^(?:Bearer\s+)?([A-Za-z0-9_-]{20,100})\.([0-9a-f]{40})$/', trim($h), $m)) fel(401, 'auth', 'Inte inloggad.');
  [, $tok, $id] = $m;
  $f = acc_file($id);
  if (!is_file($f)) fel(401, 'auth', 'Inloggningen gäller inte längre.');
  $th = token_hash($tok);
  $acc = locked_json($f, function ($acc) use ($th) {
    if (!is_array($acc)) return [null, null];
    $nu = time();
    foreach ($acc['tokens'] ?? [] as $i => $t) {
      if (hash_equals($t['h'], $th) && $t['used'] > $nu - TOKEN_DAYS * 86400) {
        if ($t['used'] < $nu - 3600) { $acc['tokens'][$i]['used'] = $nu; return [$acc, $acc]; }
        return [null, $acc];
      }
    }
    return [null, null];
  });
  if (!$acc) fel(401, 'auth', 'Inloggningen gäller inte längre.');
  $acc['_token'] = $th;
  return [$id, $acc];
}
function public_acc(array $acc): array {
  return ['email' => $acc['email'], 'created' => $acc['created'], 'rev' => $acc['rev'] ?? 0, 'saved' => $acc['saved'] ?? null,
          'size' => $acc['size'] ?? 0, 'used' => usage($acc), 'quota' => QUOTA, 'vault' => $acc['vault']];
}
function usage(array $acc): int { return (int)($acc['size'] ?? 0) + array_sum(array_column($acc['history'] ?? [], 'size')); }
function fake_salt(string $email): string { return base64_encode(substr(hash_hmac('sha256', 'salt|' . $email, secret(), true), 0, 16)); }
function config(): array { static $c = null; if ($c === null) { $f = __DIR__ . '/api-config.php'; $c = is_file($f) ? (array)(include $f) : []; } return $c; }
function is_admin(): bool {
  // Klienten skickar nyckeln URL-kodad (från 0.13.1), så att å, ä, ö och andra tecken kommer fram som UTF-8.
  $k = trim(rawurldecode((string)($_SERVER['HTTP_X_SISYFOS_ADMIN'] ?? '')));
  $want = (string)(config()['admin'] ?? '');
  return $want !== '' && $k !== '' && hash_equals($want, hash('sha256', $k));
}
function require_admin(): void {
  if (is_admin()) return;
  guard(); failed();
  fel(403, 'admin', (config()['admin'] ?? '') === '' ? 'Ingen adminnyckel är satt på servern.' : 'Fel adminnyckel.');
}
function rmtree(string $dir): void {
  if (!is_dir($dir)) return;
  foreach (scandir($dir) as $f) { if ($f === '.' || $f === '..') continue; $p = "$dir/$f"; is_dir($p) ? rmtree($p) : unlink($p); }
  rmdir($dir);
}
function dummy_hash(): string {
  $f = dpath('dummy.hash');
  $h = @file_get_contents($f);
  if (!$h || !str_starts_with($h, '$')) { $h = password_hash(bin2hex(random_bytes(16)), PASSWORD_DEFAULT); file_put_contents($f, $h, LOCK_EX); }
  return $h;
}
function invites_file(): string { return dpath('invites.json'); }

/* ---------- åtgärder ---------- */
$metod = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$a = (string)($_GET['a'] ?? 'status');
if ($metod === 'OPTIONS') fel(405, 'method', 'Bara samma ursprung.');
$post = $metod === 'POST';
$need = fn() => $post || fel(405, 'method', 'Endast POST.');

switch ($a) {

case 'status': {
  [$mode] = data_dir(); secret();
  svar(200, ['api' => API_VERSION, 'php' => PHP_VERSION, 'storage' => $mode, 'quota' => QUOTA,
             'admin' => (config()['admin'] ?? '') !== '', 'register' => 'invite']);
}

/* Salt och varv för att räkna fram inloggningshemligheten. Okända adresser får ett falskt men stabilt salt. */
case 'kdf': {
  $need(); $in = json_in(); $email = email_norm($in['email'] ?? '');
  $acc = read_json(acc_file(acc_id($email)));
  svar(200, ['kdf' => $acc ? $acc['vault']['kdf'] : ['name' => KDF_NAME, 'iter' => KDF_ITER, 'salt' => fake_salt($email)]]);
}

case 'register': {
  $need(); guard(); $in = json_in();
  $email = email_norm($in['email'] ?? '');
  $login = b64ok($in['login'] ?? '', 32);
  $vault = check_vault($in['vault'] ?? null);
  $kod = strtoupper(preg_replace('/[^A-Za-z0-9]/', '', (string)($in['invite'] ?? '')));
  if ($kod === '') fel(400, 'invite', 'Inbjudningskoden saknas.');
  $id = acc_id($email);
  if (is_file(acc_file($id))) fel(409, 'exists', 'Det finns redan ett konto med den e-postadressen. Logga in i stället.');
  // Förbruka koden först (under lås), lämna tillbaka den om kontot redan finns.
  $okKod = locked_json(invites_file(), function ($inv) use ($kod, $email) {
    $inv = is_array($inv) ? $inv : [];
    $k = $inv[$kod] ?? null;
    if (!$k || ($k['used'] ?? 0) >= ($k['max'] ?? 1) || (isset($k['until']) && $k['until'] < time())) return [null, false];
    $inv[$kod]['used'] = ($k['used'] ?? 0) + 1;
    $inv[$kod]['by'][] = ['at' => time(), 'acc' => substr(hash('sha256', $email), 0, 8)];
    return [$inv, true];
  });
  if (!$okKod) { failed(); fel(403, 'invite', 'Inbjudningskoden gäller inte.'); }
  $dir = acc_dir($id);
  if (is_dir($dir) && is_file(acc_file($id))) {
    locked_json(invites_file(), function ($inv) use ($kod) { $inv[$kod]['used']--; array_pop($inv[$kod]['by']); return [$inv, null]; });
    fel(409, 'exists', 'Det finns redan ett konto med den e-postadressen. Logga in i stället.');
  }
  if (!is_dir($dir)) mkdir($dir, 0700);
  $device = (string)($in['device'] ?? '');
  $tok = locked_json(acc_file($id), function ($acc) use ($email, $login, $vault, $kod, $device) {
    if (is_array($acc)) return [null, null];
    $acc = ['v' => 1, 'email' => $email, 'created' => time(), 'invite' => $kod, 'login' => password_hash($login, PASSWORD_DEFAULT),
            'vault' => $vault, 'rev' => 0, 'saved' => null, 'size' => 0, 'history' => [], 'tokens' => [], 'orgs' => []];
    $t = new_token($acc, $device);
    return [$acc, $t];
  });
  if (!$tok) fel(409, 'exists', 'Det finns redan ett konto med den e-postadressen. Logga in i stället.');
  svar(201, ['token' => "$tok.$id"] + public_acc(read_json(acc_file($id))));
}

case 'login': {
  $need(); $in = json_in();
  $email = email_norm($in['email'] ?? '');
  $login = b64ok($in['login'] ?? '', 32);
  $id = acc_id($email); $ak = 'acc|' . $id;
  guard($ak);
  $f = acc_file($id);
  if (!is_file($f)) { password_verify($login, dummy_hash()); failed($ak); fel(401, 'login', 'Fel e-postadress eller lösenord.'); }
  $device = (string)($in['device'] ?? '');
  $res = locked_json($f, function ($acc) use ($login, $device) {
    if (!is_array($acc) || !password_verify($login, $acc['login'])) return [null, null];
    if (password_needs_rehash($acc['login'], PASSWORD_DEFAULT)) $acc['login'] = password_hash($login, PASSWORD_DEFAULT);
    $t = new_token($acc, $device);
    return [$acc, [$t, $acc]];
  });
  if (!$res) { failed($ak); fel(401, 'login', 'Fel e-postadress eller lösenord.'); }
  svar(200, ['token' => "{$res[0]}.$id"] + public_acc($res[1]));
}

case 'info': {
  [, $acc] = auth();
  svar(200, public_acc($acc) + ['devices' => array_map(fn($t) => ['device' => $t['device'], 'created' => $t['created'], 'used' => $t['used'], 'this' => $t['h'] === $acc['_token']], $acc['tokens'])]);
}

/* Hämta boken (eller en tidigare version med &rev=N). Svarar med filen som den är. */
case 'get': {
  [$id, $acc] = auth();
  $rev = isset($_GET['rev']) ? (int)$_GET['rev'] : (int)$acc['rev'];
  if ($rev === 0 || ($rev !== (int)$acc['rev'] && !in_array($rev, array_column($acc['history'], 'rev'), true))) fel(404, 'none', 'Det finns ingen sparad bok' . ($rev ? " med version $rev." : ' än.'));
  $f = acc_dir($id) . ($rev === (int)$acc['rev'] ? '/book.sisyfos' : "/hist-$rev.sisyfos");
  $raw = @file_get_contents($f);
  if ($raw === false) fel(404, 'none', 'Filen saknas på servern.');
  header('X-Sisyfos-Rev: ' . $rev);
  header('X-Sisyfos-Head: ' . (int)$acc['rev']);
  http_response_code(200); echo $raw; exit;
}

case 'history': {
  [, $acc] = auth();
  svar(200, ['rev' => $acc['rev'], 'saved' => $acc['saved'], 'size' => $acc['size'], 'history' => array_reverse($acc['history'])]);
}

/* Spara boken. Kräver If-Match med den version enheten senast såg (0 = ingen bok än). Vid krock: 409 med serverns version. */
case 'put': {
  $need(); [$id, ] = auth();
  $match = trim((string)($_SERVER['HTTP_X_SISYFOS_BASE'] ?? $_SERVER['HTTP_IF_MATCH'] ?? ''), " \"");
  if ($match === '' || !ctype_digit($match)) fel(428, 'if_match', 'If-Match saknas.');
  $raw = body(MAX_BOOK);
  $fil = json_decode($raw, true);
  if (!is_array($fil) || ($fil['format'] ?? '') !== 'sisyfos-krypterad' || !isset($fil['data']['iv'], $fil['data']['ct'], $fil['vault']['id'])) fel(400, 'format', 'Servern tar bara emot krypterade böcker.');
  $dir = acc_dir($id); $size = strlen($raw);
  $res = locked_json(acc_file($id), function ($acc) use ($match, $raw, $size, $dir, $fil) {
    if ((int)$match !== (int)$acc['rev']) return [null, ['conflict', $acc]];
    if ($fil['vault']['id'] !== $acc['vault']['id']) return [null, ['vault', $acc]];
    // Flytta nuvarande bok till historiken, rensa så att kvoten räcker.
    if ($acc['rev'] > 0 && is_file("$dir/book.sisyfos")) {
      rename("$dir/book.sisyfos", "$dir/hist-{$acc['rev']}.sisyfos");
      $acc['history'][] = ['rev' => $acc['rev'], 'saved' => $acc['saved'], 'size' => $acc['size']];
    }
    while ($acc['history'] && (count($acc['history']) > KEEP_HISTORY || $size + array_sum(array_column($acc['history'], 'size')) > QUOTA)) {
      $old = array_shift($acc['history']); @unlink("$dir/hist-{$old['rev']}.sisyfos");
    }
    $tmp = "$dir/book.tmp"; file_put_contents($tmp, $raw); rename($tmp, "$dir/book.sisyfos");
    $acc['rev']++; $acc['saved'] = time(); $acc['size'] = $size;
    return [$acc, ['ok', $acc]];
  });
  [$utfall, $acc] = $res;
  if ($utfall === 'conflict') fel(409, 'conflict', 'Boken har ändrats från en annan enhet.', ['rev' => $acc['rev'], 'saved' => $acc['saved']]);
  if ($utfall === 'vault') fel(409, 'vault', 'Boken är krypterad med en annan nyckel än kontots. Logga in igen.', ['rev' => $acc['rev']]);
  svar(200, ['rev' => $acc['rev'], 'saved' => $acc['saved'], 'size' => $acc['size'], 'used' => usage($acc), 'quota' => QUOTA]);
}

/* Nytt valv efter byte av lösenord eller återställningsnyckel. Med nytt lösenord skickas också ny inloggningshemlighet. */
case 'vault': {
  $need(); [$id, $acc0] = auth(); $me = $acc0['_token']; $in = json_in();
  $vault = check_vault($in['vault'] ?? null);
  $login = isset($in['login']) ? b64ok($in['login'], 32) : null;
  $others = !empty($in['logoutOthers']);
  $ok = locked_json(acc_file($id), function ($acc) use ($vault, $login, $others, $me) {
    if ($vault['id'] !== $acc['vault']['id']) return [null, false];
    if ($vault['kdf']['salt'] !== $acc['vault']['kdf']['salt'] && $login === null) return [null, false];
    $acc['vault'] = $vault;
    if ($login !== null) $acc['login'] = password_hash($login, PASSWORD_DEFAULT);
    if ($others) $acc['tokens'] = array_values(array_filter($acc['tokens'], fn($t) => hash_equals($t['h'], $me)));
    return [$acc, true];
  });
  if (!$ok) fel(400, 'vault', 'Valvet hör inte till kontot, eller så saknas den nya inloggningen.');
  svar(200);
}

case 'logout': {
  $need(); [$id, $acc] = auth(); $th = $acc['_token'];
  locked_json(acc_file($id), function ($acc) use ($th) { $acc['tokens'] = array_values(array_filter($acc['tokens'], fn($t) => !hash_equals($t['h'], $th))); return [$acc, null]; });
  svar(200);
}

/* Radera kontot och allt på servern. Kräver inloggningshemligheten igen. */
case 'delete': {
  $need(); [$id, ] = auth(); $in = json_in();
  $login = b64ok($in['login'] ?? '', 32); $ak = 'acc|' . $id;
  guard($ak);
  $acc = read_json(acc_file($id));
  if (!$acc || !password_verify($login, $acc['login'])) { failed($ak); fel(401, 'login', 'Fel lösenord.'); }
  rmtree(acc_dir($id));
  svar(200, ['deleted' => true]);
}

/* ---------- administratör ---------- */
case 'invite': {
  $need(); require_admin(); $in = json_in();
  $max = max(1, min(100, (int)($in['max'] ?? 1)));
  $dagar = max(1, min(365, (int)($in['days'] ?? 30)));
  $note = mb_substr(trim((string)($in['note'] ?? '')), 0, 80);
  $alfa = '23456789ABCDEFGHJKMNPQRSTVWXYZ'; $kod = '';
  for ($i = 0; $i < 10; $i++) $kod .= $alfa[random_int(0, strlen($alfa) - 1)];
  locked_json(invites_file(), function ($inv) use ($kod, $max, $dagar, $note) {
    $inv = is_array($inv) ? $inv : [];
    $inv[$kod] = ['created' => time(), 'until' => time() + $dagar * 86400, 'max' => $max, 'used' => 0, 'note' => $note, 'by' => []];
    return [$inv, null];
  });
  svar(201, ['code' => substr($kod, 0, 5) . '-' . substr($kod, 5), 'max' => $max, 'until' => time() + $dagar * 86400]);
}
case 'invites': {
  require_admin(); $inv = read_json(invites_file()) ?? [];
  svar(200, ['invites' => array_map(fn($k, $v) => ['code' => substr($k, 0, 5) . '-' . substr($k, 5), 'note' => $v['note'] ?? '', 'max' => $v['max'], 'used' => $v['used'] ?? 0, 'until' => $v['until'] ?? null], array_keys($inv), $inv)]);
}
case 'uninvite': {
  $need(); require_admin(); $in = json_in(); $kod = strtoupper(preg_replace('/[^A-Za-z0-9]/', '', (string)($in['code'] ?? '')));
  $ok = locked_json(invites_file(), function ($inv) use ($kod) { if (!isset($inv[$kod])) return [null, false]; unset($inv[$kod]); return [$inv, true]; });
  $ok ? svar(200) : fel(404, 'none', 'Koden finns inte.');
}
case 'accounts': {
  require_admin(); $ut = [];
  foreach (glob(dpath('acc/*/account.json')) ?: [] as $f) {
    $acc = read_json($f); if (!$acc) continue;
    $ut[] = ['email' => $acc['email'], 'created' => $acc['created'], 'saved' => $acc['saved'], 'rev' => $acc['rev'], 'used' => usage($acc), 'devices' => count($acc['tokens'] ?? [])];
  }
  usort($ut, fn($a, $b) => strcmp($a['email'], $b['email']));
  svar(200, ['accounts' => $ut, 'quota' => QUOTA]);
}
case 'remove': {
  $need(); require_admin(); $in = json_in(); $id = acc_id(email_norm($in['email'] ?? ''));
  if (!is_file(acc_file($id))) fel(404, 'none', 'Kontot finns inte.');
  rmtree(acc_dir($id)); svar(200, ['deleted' => true]);
}

default:
  fel(404, 'action', 'Okänd åtgärd.');
}
