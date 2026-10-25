<?php
/*
 * Sisyfos – server för krypterad lagring (0.13.0; organisationer 0.16.1)
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

const API_VERSION   = 2;                   // 2 = organisationer (0.16.1)
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
const ORG_MAX       = 10;                  // medlemmar per organisation, admin inräknad
const ORG_QUOTA     = 50 * 1024 * 1024;    // per organisation: alla delar

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
      foreach (['acc', 'org'] as $sub) if (!is_dir("$dir/$sub")) mkdir("$dir/$sub", 0700);
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
          'size' => $acc['size'] ?? 0, 'used' => usage($acc), 'quota' => QUOTA, 'vault' => $acc['vault'], 'orgs' => acc_orgs($acc), 'moved' => $acc['moved'] ?? null];
}
/* Den egna boken har flyttat till en organisation (0.16.1) – en enhet som fortfarande synkar den får veta vart */
function not_moved(array $acc): void {
  if (!empty($acc['moved']) && !isset($_GET['org'])) fel(409, 'moved', 'Boken har flyttat till en organisation.', ['org' => org_brief($acc['moved'], array_values(array_filter($acc['orgs'] ?? [], fn($o) => $o['id'] === $acc['moved']))[0]['pid'] ?? '')]);
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
function code_norm(mixed $k): string { return strtoupper(preg_replace('/[^A-Za-z0-9]/', '', (string)$k)); }
function code_show(string $k): string { return substr($k, 0, 5) . '-' . substr($k, 5); }
function code_new(): string { $alfa = '23456789ABCDEFGHJKMNPQRSTVWXYZ'; $k = ''; for ($i = 0; $i < 10; $i++) $k .= $alfa[random_int(0, strlen($alfa) - 1)]; return $k; }
/* Förbruka en inbjudningskod av ett visst slag ('account' – nytt konto, 'org' – ny organisation, 'member' – medarbetare
   i en organisation). Returnerar koden eller null. Koder utan slag är kontokoder (0.13.0). */
function use_code(string $kod, array $kinds, string $who): ?array {
  return locked_json(invites_file(), function ($inv) use ($kod, $kinds, $who) {
    $inv = is_array($inv) ? $inv : [];
    $k = $inv[$kod] ?? null;
    if (!$k || !in_array($k['kind'] ?? 'account', $kinds, true) || ($k['used'] ?? 0) >= ($k['max'] ?? 1) || (isset($k['until']) && $k['until'] < time())) return [null, null];
    $inv[$kod]['used'] = ($k['used'] ?? 0) + 1;
    $inv[$kod]['by'][] = ['at' => time(), 'acc' => substr(hash('sha256', $who), 0, 8)];
    return [$inv, $inv[$kod] + ['code' => $kod]];
  });
}
function give_back(string $kod): void {
  locked_json(invites_file(), function ($inv) use ($kod) { if (!isset($inv[$kod])) return [null, null]; $inv[$kod]['used']--; array_pop($inv[$kod]['by']); return [$inv, null]; });
}

/* ---------- organisationer (0.16.1, etapp 4) ----------
   En organisation är en bok som flera personer delar. Boken ligger i delar (claude/etapp4.md): reg (registret),
   adm (fakturor), card.<person> och log.<person>. Varje del är krypterad på enheten till sina läsare och signerad av
   sin skribent – servern ser bara vem som skrev den och till vilka den är krypterad (nycklarna i 'to').
   Servern ser till att rätt person skriver varje del: reg, adm och korten skrivs av organisationens admin, en tidlogg
   av personen själv (eller av admin så länge personen inte har skrivit den själv – innan personen gått med).
     org/<id>/org.json      { v, id, book, name, created, rev, saved, size, members{pid: {acc, email, role, joined, keys?, wrote}}, parts{namn: {rev, by, size, saved}} }
     org/<id>/p-<namn>.json delen som den skickades
     org/<id>/env-<konto>.json  kontots omslag: valvet, nyckelringen (låst med kontots boknyckel) och stubben
   Kontot: orgs[] = [{id, pid, role}]. moved = organisationen som kontots egen bok flyttade till. */
function org_dir(string $oid): string { return dpath('org/' . $oid); }
function org_file(string $oid): string { return org_dir($oid) . '/org.json'; }
function part_ok(mixed $n): bool { return is_string($n) && (bool)preg_match('/^(reg|adm|(card|log)\.[A-Za-z0-9_-]{1,40})$/', $n); }
function pid_ok(mixed $p): bool { return is_string($p) && (bool)preg_match('/^[A-Za-z0-9_-]{1,40}$/', $p); }
function org_usage(array $org): int { return array_sum(array_column($org['parts'] ?? [], 'size')); }
/* Organisationen som begäran gäller (&org=<id>) – kontot måste vara medlem. Returnerar [id, pid, roll, org]. */
function org_ctx(array $acc, bool $need = true): ?array {
  $oid = (string)($_GET['org'] ?? '');
  if ($oid === '') { if ($need) fel(400, 'org', 'Organisationen saknas.'); return null; }
  if (!preg_match('/^[0-9a-f]{20}$/', $oid)) fel(400, 'org', 'Felaktig organisation.');
  $m = null; foreach ($acc['orgs'] ?? [] as $o) if ($o['id'] === $oid) $m = $o;
  $org = read_json(org_file($oid));
  if (!$m || !$org || ($org['members'][$m['pid']]['acc'] ?? '') !== acc_id($acc['email'])) fel(403, 'not_member', 'Du är inte med i organisationen längre.');
  return [$oid, $m['pid'], $org['members'][$m['pid']]['role'], $org];
}
function org_brief(string $oid, string $pid): ?array {
  $org = read_json(org_file($oid)); if (!$org || !isset($org['members'][$pid])) return null;
  return ['id' => $oid, 'name' => $org['name'], 'pid' => $pid, 'role' => $org['members'][$pid]['role'], 'members' => count($org['members'])];
}
function acc_orgs(array $acc): array { $ut = []; foreach ($acc['orgs'] ?? [] as $o) { $b = org_brief($o['id'], $o['pid']); if ($b) $ut[] = $b; } return $ut; }
/* Vad appen behöver veta om organisationen. Admin ser medlemmarnas e-post, nycklar och öppna inbjudningar. */
function org_public(string $oid, array $org, string $pid, string $role): array {
  $admin = $role === 'admin'; $mem = [];
  foreach ($org['members'] as $p => $m) $mem[] = ['pid' => (string)$p, 'role' => $m['role'], 'joined' => $m['joined'], 'wrote' => !empty($m['wrote'])]
    + ($admin ? ['email' => $m['email'], 'keys' => $m['keys'] ?? null] : []);
  $inv = [];
  if ($admin) foreach (read_json(invites_file()) ?? [] as $k => $v)
    if (($v['kind'] ?? '') === 'member' && ($v['org'] ?? '') === $oid && ($v['used'] ?? 0) < ($v['max'] ?? 1) && ($v['until'] ?? 0) > time())
      $inv[] = ['code' => code_show($k), 'pid' => $v['pid'], 'note' => $v['note'] ?? '', 'until' => $v['until']];
  return ['id' => $oid, 'name' => $org['name'], 'book' => $org['book'], 'pid' => $pid, 'role' => $role, 'max' => ORG_MAX, 'created' => $org['created'],
          'members' => $mem, 'invites' => $inv, 'wrote' => array_values(array_map('strval', array_keys(array_filter($org['members'], fn($m) => !empty($m['wrote'])))))];
}
/* Lägg till en medlem (under organisationens lås). Returnerar felkod eller null. */
function org_join(string $oid, string $pid, string $accId, string $email, string $role): ?string {
  if (!is_file(org_file($oid))) return 'none';
  $r = locked_json(org_file($oid), function ($org) use ($pid, $accId, $email, $role) {
    if (!is_array($org)) return [null, 'none'];
    foreach ($org['members'] as $m) if ($m['acc'] === $accId) return [null, 'already'];
    if (isset($org['members'][$pid])) return [null, 'taken'];
    if (count($org['members']) >= ORG_MAX) return [null, 'full'];
    $org['members'][$pid] = ['acc' => $accId, 'email' => $email, 'role' => $role, 'joined' => time(), 'wrote' => false];
    return [$org, null];
  });
  if ($r) return $r;
  locked_json(acc_file($accId), function ($acc) use ($oid, $pid, $role) { $acc['orgs'] = array_values(array_filter($acc['orgs'] ?? [], fn($o) => $o['id'] !== $oid)); $acc['orgs'][] = ['id' => $oid, 'pid' => $pid, 'role' => $role]; return [$acc, null]; });
  return null;
}
function org_join_fail(string $kod, string $why): never {
  give_back($kod);
  fel($why === 'full' ? 409 : 400, 'org_' . $why, ['none' => 'Organisationen finns inte längre.', 'already' => 'Kontot är redan med i organisationen.', 'taken' => 'Personen har redan ett konto i organisationen.', 'full' => 'Organisationen har redan ' . ORG_MAX . ' medlemmar.'][$why] ?? 'Det gick inte att gå med.');
}
/* Ta bort en medlem: ur organisationen, ur kontots lista och kontots omslag */
function org_drop(string $oid, string $pid): ?string {
  $acc = locked_json(org_file($oid), function ($org) use ($pid) {
    if (!is_array($org) || !isset($org['members'][$pid])) return [null, null];
    $a = $org['members'][$pid]['acc']; unset($org['members'][$pid]);
    return [$org, $a];
  });
  if (!$acc) return null;
  if (is_file(acc_file($acc))) locked_json(acc_file($acc), function ($x) use ($oid) { if (!is_array($x)) return [null, null]; $x['orgs'] = array_values(array_filter($x['orgs'] ?? [], fn($o) => $o['id'] !== $oid)); if (($x['moved'] ?? '') === $oid) unset($x['moved']); return [$x, null]; });
  @unlink(org_dir($oid) . "/env-$acc.json");
  return $acc;
}
function org_remove_all(string $oid): void {
  $org = read_json(org_file($oid)); if (!$org) return;
  foreach (array_keys($org['members']) as $p) org_drop($oid, (string)$p);
  locked_json(invites_file(), function ($inv) use ($oid) { $inv = is_array($inv) ? $inv : []; foreach ($inv as $k => $v) if (($v['org'] ?? '') === $oid) unset($inv[$k]); return [$inv, null]; });
  rmtree(org_dir($oid));
}
function check_env(mixed $e): array {
  if (!is_array($e) || !isset($e['data']['iv'], $e['data']['ct']) || !is_array($e['keys'] ?? null)) fel(400, 'format', 'Omslaget är ofullständigt.');
  if (strlen(json_encode($e)) > 32768) fel(400, 'format', 'Omslaget är för stort.');
  return ['vault' => $e['vault'] ?? null, 'zip' => $e['zip'] ?? null, 'keys' => $e['keys'], 'data' => $e['data']];
}
function check_pubkeys(mixed $k): array {
  if (!is_array($k) || !isset($k['enc']['x'], $k['enc']['y'], $k['sig']['x'], $k['sig']['y'], $k['fp'], $k['at'])) fel(400, 'keys', 'Nycklarna är ofullständiga.');
  if (strlen(json_encode($k)) > 4096) fel(400, 'keys', 'Nycklarna är för stora.');
  $j = fn($x) => ['kty' => (string)($x['kty'] ?? 'EC'), 'crv' => (string)($x['crv'] ?? 'P-256'), 'x' => (string)$x['x'], 'y' => (string)$x['y']];
  return ['enc' => $j($k['enc']), 'sig' => $j($k['sig']), 'at' => (string)$k['at'], 'fp' => (string)$k['fp']];
}
function write_atomic(string $f, string $raw): void { $tmp = $f . '.tmp'; file_put_contents($tmp, $raw); rename($tmp, $f); }

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
             'admin' => (config()['admin'] ?? '') !== '', 'register' => 'invite', 'orgs' => ORG_MAX]);
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
  $kod = code_norm($in['invite'] ?? '');
  if ($kod === '') fel(400, 'invite', 'Inbjudningskoden saknas.');
  $id = acc_id($email);
  if (is_file(acc_file($id))) fel(409, 'exists', 'Det finns redan ett konto med den e-postadressen. Logga in i stället.');
  // Förbruka koden först (under lås), lämna tillbaka den om kontot redan finns. En medarbetares kod (0.16.1)
  // skapar kontot och lägger in det i organisationen.
  $okKod = use_code($kod, ['account', 'member'], $email);
  if (!$okKod) { failed(); fel(403, 'invite', 'Inbjudningskoden gäller inte.'); }
  $dir = acc_dir($id);
  if (is_dir($dir) && is_file(acc_file($id))) {
    give_back($kod);
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
  $org = null;
  if (($okKod['kind'] ?? '') === 'member') {
    $why = org_join($okKod['org'], $okKod['pid'], $id, $email, 'member');
    if ($why) { rmtree($dir); org_join_fail($kod, $why); }
    $org = org_brief($okKod['org'], $okKod['pid']);
  }
  svar(201, ['token' => "$tok.$id", 'org' => $org] + public_acc(read_json(acc_file($id))));
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
  $dev = ['devices' => array_map(fn($t) => ['device' => $t['device'], 'created' => $t['created'], 'used' => $t['used'], 'this' => $t['h'] === $acc['_token']], $acc['tokens'])];
  $c = org_ctx($acc, false);
  if (!$c) { not_moved($acc); svar(200, public_acc($acc) + $dev); }
  [$oid, $pid, $role, $org] = $c;
  // Med en organisation gäller dess version och utrymme; kontot har kvar valvet och enheterna
  svar(200, ['rev' => $org['rev'], 'saved' => $org['saved'], 'size' => org_usage($org), 'used' => org_usage($org), 'quota' => ORG_QUOTA, 'org' => org_public($oid, $org, $pid, $role)] + public_acc($acc) + $dev);
}

/* Hämta boken (eller en tidigare version med &rev=N). Svarar med filen som den är.
   Med &org= (0.16.1): kontots omslag och de delar som är krypterade till personen, i samma form som en fil version 2. */
case 'get': {
  [$id, $acc] = auth();
  $c = org_ctx($acc, false);
  if ($c) {
    [$oid, $pid, $role, $org] = $c; $dir = org_dir($oid);
    $env = read_json("$dir/env-$id.json") ?? [];
    $parts = [];
    foreach ($org['parts'] as $n => $meta) {
      $p = read_json("$dir/p-$n.json");
      if ($p && isset($p['to'][$pid])) $parts[$n] = $p;
    }
    $ut = ['format' => 'sisyfos-krypterad', 'version' => 2, 'app' => 'server', 'saved' => $org['saved'] ? gmdate('c', $org['saved']) : null,
           'vault' => $env['vault'] ?? $acc['vault'], 'zip' => $env['zip'] ?? null, 'org' => $org['book'], 'me' => $pid,
           'keys' => (object)($env['keys'] ?? []), 'parts' => (object)$parts, 'data' => $env['data'] ?? null,
           'srv' => ['rev' => $org['rev'], 'role' => $role, 'wrote' => org_public($oid, $org, $pid, $role)['wrote']]];
    header('X-Sisyfos-Rev: ' . $org['rev']); header('X-Sisyfos-Head: ' . $org['rev']);
    http_response_code(200); echo json_encode($ut, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); exit;
  }
  not_moved($acc);
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
  if ($c = org_ctx($acc, false)) svar(200, ['rev' => $c[3]['rev'], 'saved' => $c[3]['saved'], 'size' => org_usage($c[3]), 'history' => [], 'org' => true]);
  svar(200, ['rev' => $acc['rev'], 'saved' => $acc['saved'], 'size' => $acc['size'], 'history' => array_reverse($acc['history'])]);
}

/* Spara boken. Kräver If-Match med den version enheten senast såg (0 = ingen bok än). Vid krock: 409 med serverns version.
   Med &org= (0.16.1): filen innehåller bara de delar enheten skriver. Varje del kontrolleras mot medlemmens roll och
   sparas för sig; krock bara om någon av just de delarna har ändrats sedan basversionen. behind = andra delar har ändrats. */
case 'put': {
  $need(); [$id, $acc] = auth();
  $match = trim((string)($_SERVER['HTTP_X_SISYFOS_BASE'] ?? $_SERVER['HTTP_IF_MATCH'] ?? ''), " \"");
  if ($match === '' || !ctype_digit($match)) fel(428, 'if_match', 'If-Match saknas.');
  $raw = body(MAX_BOOK);
  $fil = json_decode($raw, true);
  if (!is_array($fil) || ($fil['format'] ?? '') !== 'sisyfos-krypterad' || !isset($fil['data']['iv'], $fil['data']['ct'], $fil['vault']['id'])) fel(400, 'format', 'Servern tar bara emot krypterade böcker.');
  if ($c = org_ctx($acc, false)) {
    [$oid, $pid] = $c; $dir = org_dir($oid);
    if ($fil['vault']['id'] !== $acc['vault']['id']) fel(409, 'vault', 'Boken är krypterad med en annan nyckel än kontots. Logga in igen.');
    $parts = is_array($fil['parts'] ?? null) ? $fil['parts'] : [];
    foreach ($parts as $n => $p) {
      if (!part_ok($n) || !is_array($p) || !isset($p['iv'], $p['ct'], $p['sig'], $p['epk']) || !is_array($p['to'] ?? null) || !$p['to']) fel(400, 'format', "Delen $n är ofullständig.");
      if (($p['by'] ?? '') !== $pid) fel(403, 'writer', "Delen $n är inte skriven av dig.");
    }
    $env = check_env($fil);
    $res = locked_json(org_file($oid), function ($org) use ($parts, $pid, $match, $dir) {
      $role = $org['members'][$pid]['role'] ?? '';
      foreach ($parts as $n => $p) {
        $log = str_starts_with($n, 'log.') ? substr($n, 4) : null;
        $okW = $log !== null ? ($log === $pid || ($role === 'admin' && empty($org['members'][$log]['wrote']))) : $role === 'admin';
        if (!$okW) return [null, ['writer', $n]];
        if (($org['parts'][$n]['rev'] ?? 0) > (int)$match) return [null, ['conflict', $org]];
      }
      $sizes = []; foreach ($parts as $n => $p) $sizes[$n] = strlen(json_encode($p, JSON_UNESCAPED_SLASHES));
      $total = org_usage(['parts' => array_diff_key($org['parts'], $parts)]) + array_sum($sizes);
      if ($total > ORG_QUOTA) return [null, ['quota', $org]];
      $behind = false; foreach ($org['parts'] as $n => $m) if (!isset($parts[$n]) && $m['rev'] > (int)$match) $behind = true;
      if (!$parts) return [null, ['ok', $org, $behind]];
      $rev = $org['rev'] + 1; $nu = time();
      foreach ($parts as $n => $p) {
        write_atomic("$dir/p-$n.json", json_encode($p, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
        $org['parts'][$n] = ['rev' => $rev, 'by' => $pid, 'size' => $sizes[$n], 'saved' => $nu];
        if ($n === "log.$pid") $org['members'][$pid]['wrote'] = true;
      }
      $org['rev'] = $rev; $org['saved'] = $nu; $org['size'] = org_usage($org);
      return [$org, ['ok', $org, $behind]];
    });
    if ($res[0] === 'writer') fel(403, 'writer', "Du får inte skriva delen {$res[1]}.");
    if ($res[0] === 'conflict') fel(409, 'conflict', 'Boken har ändrats från en annan enhet.', ['rev' => $res[1]['rev'], 'saved' => $res[1]['saved']]);
    if ($res[0] === 'quota') fel(413, 'quota', 'Organisationens utrymme räcker inte.');
    $org = $res[1];
    write_atomic("$dir/env-$id.json", json_encode($env, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    svar(200, ['rev' => $org['rev'], 'saved' => $org['saved'], 'size' => org_usage($org), 'used' => org_usage($org), 'quota' => ORG_QUOTA, 'behind' => $res[2]]);
  }
  not_moved($acc);
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
  // Omslagen i organisationerna bär samma valv (0.16.1)
  foreach ($acc0['orgs'] ?? [] as $o) { $f = org_dir($o['id']) . "/env-$id.json"; if (is_file($f)) locked_json($f, fn($e) => [is_array($e) ? ['vault' => $vault] + $e : null, null]); }
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
  // Organisationer: en medarbetare går ur, en admin tar bort organisationen (med allt) – 0.16.1
  foreach ($acc['orgs'] ?? [] as $o) { if (($o['role'] ?? '') === 'admin') org_remove_all($o['id']); else org_drop($o['id'], $o['pid']); }
  rmtree(acc_dir($id));
  svar(200, ['deleted' => true]);
}

/* ---------- organisationer (0.16.1) ---------- */
/* Gör kontots bok till en organisation. Kräver en kod av slaget 'org' från serverns ägare. Kontot blir organisationens
   admin som personen pid i boken. Kontots egen bok på servern tas bort – boken finns nu i organisationen (moved). */
case 'orgCreate': {
  $need(); [$id, $acc] = auth(); $in = json_in(); guard();
  $book = (string)($in['book'] ?? ''); $name = mb_substr(trim((string)($in['name'] ?? '')), 0, 80); $pid = $in['pid'] ?? '';
  if (!preg_match('/^o[0-9A-Za-z_-]{1,40}$/', $book) || !pid_ok($pid) || $name === '') fel(400, 'format', 'Boken saknar organisation, namn eller person.');
  foreach ($acc['orgs'] ?? [] as $o) { $x = read_json(org_file($o['id'])); if ($x && $x['book'] === $book) fel(409, 'org_exists', 'Boken är redan en organisation.'); }
  $kod = code_norm($in['code'] ?? '');
  if (!use_code($kod, ['org'], $acc['email'])) { failed(); fel(403, 'invite', 'Koden för en organisation gäller inte.'); }
  $oid = bin2hex(random_bytes(10)); mkdir(org_dir($oid), 0700, true);
  file_put_contents(org_file($oid), json_encode(['v' => 1, 'id' => $oid, 'book' => $book, 'name' => $name, 'created' => time(), 'rev' => 0, 'saved' => null, 'size' => 0, 'members' => (object)[], 'parts' => (object)[]]), LOCK_EX);
  $why = org_join($oid, $pid, $id, $acc['email'], 'admin');
  if ($why) { rmtree(org_dir($oid)); org_join_fail($kod, $why); }
  $dir = acc_dir($id);
  locked_json(acc_file($id), function ($a) use ($oid, $dir) {
    @unlink("$dir/book.sisyfos"); foreach ($a['history'] ?? [] as $h) @unlink("$dir/hist-{$h['rev']}.sisyfos");
    $a['history'] = []; $a['size'] = 0; $a['moved'] = $oid;
    return [$a, null];
  });
  svar(201, ['org' => org_brief($oid, $pid)]);
}
/* Ett befintligt konto går med i en organisation med en medarbetarkod */
case 'orgJoin': {
  $need(); [$id, $acc] = auth(); $in = json_in(); guard();
  $kod = code_norm($in['code'] ?? '');
  $k = use_code($kod, ['member'], $acc['email']);
  if (!$k) { failed(); fel(403, 'invite', 'Inbjudningskoden gäller inte.'); }
  $why = org_join($k['org'], $k['pid'], $id, $acc['email'], 'member');
  if ($why) org_join_fail($kod, $why);
  svar(200, ['org' => org_brief($k['org'], $k['pid'])]);
}
/* Medarbetarens offentliga nycklar (som admin tar in i registret) och kontots omslag med nyckelringen */
case 'orgKeys': {
  $need(); [$id, $acc] = auth(); [$oid, $pid] = org_ctx($acc); $in = json_in();
  $keys = check_pubkeys($in['keys'] ?? null); $env = check_env($in['env'] ?? null);
  $ok = locked_json(org_file($oid), function ($org) use ($pid, $keys) {
    $m = $org['members'][$pid];
    if (!empty($m['keys']) && $m['keys']['fp'] !== $keys['fp'] && !empty($m['wrote'])) return [null, false];
    $org['members'][$pid]['keys'] = $keys; return [$org, true];
  });
  if (!$ok) fel(409, 'keys', 'Du har redan nycklar i organisationen.');
  write_atomic(org_dir($oid) . "/env-$id.json", json_encode($env, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
  svar(200);
}
/* Organisationens admin bjuder in en person i boken (pid) – koden gäller ett konto */
case 'orgInvite': {
  $need(); [, $acc] = auth(); [$oid, , $role, $org] = org_ctx($acc); $in = json_in();
  if ($role !== 'admin') fel(403, 'org_admin', 'Bara organisationens admin kan bjuda in.');
  $pid = $in['pid'] ?? ''; if (!pid_ok($pid)) fel(400, 'format', 'Personen saknas.');
  if (isset($org['members'][$pid])) fel(409, 'org_taken', 'Personen har redan ett konto i organisationen.');
  $dagar = max(1, min(90, (int)($in['days'] ?? 30))); $note = mb_substr(trim((string)($in['note'] ?? '')), 0, 80);
  $kod = code_new();
  $ok = locked_json(invites_file(), function ($inv) use ($oid, $pid, $kod, $dagar, $note, $org) {
    $inv = is_array($inv) ? $inv : []; $open = 0;
    foreach ($inv as $k => $v) if (($v['kind'] ?? '') === 'member' && ($v['org'] ?? '') === $oid) {
      if ($v['pid'] === $pid) { unset($inv[$k]); continue; }  // en ny kod ersätter den förra till samma person
      if (($v['used'] ?? 0) < 1 && ($v['until'] ?? 0) > time()) $open++;
    }
    if (count($org['members']) + $open >= ORG_MAX) return [null, false];
    $inv[$kod] = ['kind' => 'member', 'org' => $oid, 'pid' => $pid, 'note' => $note, 'created' => time(), 'until' => time() + $dagar * 86400, 'max' => 1, 'used' => 0, 'by' => []];
    return [$inv, true];
  });
  if (!$ok) fel(409, 'org_full', 'Organisationen har redan ' . ORG_MAX . ' medlemmar och inbjudningar.');
  svar(201, ['code' => code_show($kod), 'pid' => $pid, 'until' => time() + $dagar * 86400]);
}
case 'orgUninvite': {
  $need(); [, $acc] = auth(); [$oid, , $role] = org_ctx($acc); $in = json_in();
  if ($role !== 'admin') fel(403, 'org_admin', 'Bara organisationens admin kan ta bort inbjudningar.');
  $kod = code_norm($in['code'] ?? '');
  $ok = locked_json(invites_file(), function ($inv) use ($kod, $oid) { if (($inv[$kod]['org'] ?? '') !== $oid) return [null, false]; unset($inv[$kod]); return [$inv, true]; });
  $ok ? svar(200) : fel(404, 'none', 'Koden finns inte.');
}
/* Ta bort en medarbetare ur organisationen. Admins enhet krypterar sedan om delarna utan personen. */
case 'orgRemove': {
  $need(); [, $acc] = auth(); [$oid, $me, $role] = org_ctx($acc); $in = json_in();
  if ($role !== 'admin') fel(403, 'org_admin', 'Bara organisationens admin kan ta bort medarbetare.');
  $pid = $in['pid'] ?? ''; if (!pid_ok($pid) || $pid === $me) fel(400, 'format', 'Du kan inte ta bort dig själv.');
  if (!org_drop($oid, $pid)) fel(404, 'none', 'Personen är inte med i organisationen.');
  locked_json(invites_file(), function ($inv) use ($oid, $pid) { $inv = is_array($inv) ? $inv : []; foreach ($inv as $k => $v) if (($v['org'] ?? '') === $oid && ($v['pid'] ?? '') === $pid) unset($inv[$k]); return [$inv, null]; });
  svar(200);
}

/* ---------- administratör ---------- */
case 'invite': {
  $need(); require_admin(); $in = json_in();
  $max = max(1, min(100, (int)($in['max'] ?? 1)));
  $dagar = max(1, min(365, (int)($in['days'] ?? 30)));
  $note = mb_substr(trim((string)($in['note'] ?? '')), 0, 80);
  $kind = ($in['kind'] ?? '') === 'org' ? 'org' : 'account';  // org: en kod som gör en bok till en organisation (0.16.1)
  $kod = code_new();
  locked_json(invites_file(), function ($inv) use ($kod, $max, $dagar, $note, $kind) {
    $inv = is_array($inv) ? $inv : [];
    $inv[$kod] = ['kind' => $kind, 'created' => time(), 'until' => time() + $dagar * 86400, 'max' => $max, 'used' => 0, 'note' => $note, 'by' => []];
    return [$inv, null];
  });
  svar(201, ['code' => code_show($kod), 'kind' => $kind, 'max' => $max, 'until' => time() + $dagar * 86400]);
}
case 'invites': {
  require_admin(); $inv = array_filter(read_json(invites_file()) ?? [], fn($v) => ($v['kind'] ?? 'account') !== 'member');
  svar(200, ['invites' => array_values(array_map(fn($k, $v) => ['code' => code_show((string)$k), 'kind' => $v['kind'] ?? 'account', 'note' => $v['note'] ?? '', 'max' => $v['max'], 'used' => $v['used'] ?? 0, 'until' => $v['until'] ?? null], array_keys($inv), $inv))]);
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
    $ut[] = ['email' => $acc['email'], 'created' => $acc['created'], 'saved' => $acc['saved'], 'rev' => $acc['rev'], 'used' => usage($acc), 'devices' => count($acc['tokens'] ?? []), 'orgs' => count($acc['orgs'] ?? [])];
  }
  usort($ut, fn($a, $b) => strcmp($a['email'], $b['email']));
  $orgs = [];
  foreach (glob(dpath('org/*/org.json')) ?: [] as $f) {
    $o = read_json($f); if (!$o) continue;
    $adm = array_values(array_filter($o['members'], fn($m) => $m['role'] === 'admin'))[0]['email'] ?? '–';
    $orgs[] = ['name' => $o['name'], 'admin' => $adm, 'members' => count($o['members']), 'created' => $o['created'], 'saved' => $o['saved'], 'used' => org_usage($o)];
  }
  usort($orgs, fn($a, $b) => strcmp($a['name'], $b['name']));
  svar(200, ['accounts' => $ut, 'quota' => QUOTA, 'orgs' => $orgs, 'orgQuota' => ORG_QUOTA]);
}
case 'remove': {
  $need(); require_admin(); $in = json_in(); $id = acc_id(email_norm($in['email'] ?? ''));
  if (!is_file(acc_file($id))) fel(404, 'none', 'Kontot finns inte.');
  foreach (read_json(acc_file($id))['orgs'] ?? [] as $o) { if (($o['role'] ?? '') === 'admin') org_remove_all($o['id']); else org_drop($o['id'], $o['pid']); }
  rmtree(acc_dir($id)); svar(200, ['deleted' => true]);
}

default:
  fel(404, 'action', 'Okänd åtgärd.');
}
