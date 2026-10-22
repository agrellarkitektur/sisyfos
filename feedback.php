<?php
/*
 * Sisyfos – mottagare för synpunkter
 * Copyright (C) 2026 Agrell Arkitektur. Fri programvara under GNU GPL v3 eller senare.
 *
 * Tar emot ett formulär från Sisyfos och skickar det vidare som e-post. Sparar ingenting:
 * inga meddelanden, inga IP-adresser, inga loggar. Det enda som skrivs till disk är en
 * gemensam räknare med tidsstämplar (utan något om avsändaren) som stoppar massutskick.
 *
 * Installation: lägg filen på servern (t.ex. /sisyfos/feedback.php) och peka FEEDBACK_URL
 * i Sisyfos dit. Kräver att PHP:s mail() fungerar hos webbhotellet.
 */

const TO        = 'ca@agrellarkitektur.se';
const FROM      = 'Sisyfos synpunkter <noreply@agrellarkitektur.se>';
const MAX_HOUR  = 30;          // högst så många mejl per timme totalt
const MAX_BYTES = 20000;       // största tillåtna begäran
const KINDS     = ['Fel', 'Förslag', 'Fråga', 'Övrigt'];

// Tillåtna ursprung. '*' går bra eftersom skriptet bara tar emot – det lämnar inte ut något.
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Access-Control-Max-Age: 86400');
header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');
header('Referrer-Policy: no-referrer');

function svar(int $status, array $data): void {
  http_response_code($status);
  echo json_encode($data, JSON_UNESCAPED_UNICODE);
  exit;
}
function ren(string $s, int $max, bool $rader = false): string {
  $s = str_replace("\0", '', $s);
  $s = $rader ? preg_replace("/\r\n?/", "\n", $s) : preg_replace('/[\r\n\t]+/', ' ', $s);
  $s = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $s) ?? '';
  return mb_substr(trim($s), 0, $max, 'UTF-8');
}

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') svar(405, ['ok' => false, 'error' => 'Endast POST.']);

$raw = file_get_contents('php://input', false, null, 0, MAX_BYTES + 1);
if ($raw === false || strlen($raw) > MAX_BYTES) svar(413, ['ok' => false, 'error' => 'Meddelandet är för stort.']);
$in = json_decode($raw, true);
if (!is_array($in)) svar(400, ['ok' => false, 'error' => 'Felaktigt format.']);

// Robotfällor: dolt fält som ska vara tomt, och ett formulär som skickas på under tre sekunder.
// Svara "ok" så att roboten inte lär sig något – men skicka inget.
if (!empty($in['hp']) || (isset($in['ms']) && (int)$in['ms'] < 3000)) svar(200, ['ok' => true]);

$kind    = in_array($in['kind'] ?? '', KINDS, true) ? $in['kind'] : 'Övrigt';
$subject = ren((string)($in['subject'] ?? ''), 120);
$message = ren((string)($in['message'] ?? ''), 5000, true);
$reply   = ren((string)($in['reply'] ?? ''), 200);
if ($message === '') svar(400, ['ok' => false, 'error' => 'Synpunkten är tom.']);
if ($reply !== '' && !filter_var($reply, FILTER_VALIDATE_EMAIL)) svar(400, ['ok' => false, 'error' => 'E-postadressen ser inte rätt ut.']);

$info = '';
if (is_array($in['info'] ?? null)) {
  $v = ren((string)($in['info']['version'] ?? ''), 20);
  $f = ren((string)($in['info']['format'] ?? ''), 10);
  $sc = ren((string)($in['info']['screen'] ?? ''), 20);
  $info = "Sisyfos $v (format $f), skärm $sc";
}

// Gemensam räknare utan något om avsändaren
$fil = sys_get_temp_dir() . '/sisyfos-feedback-rate.json';
$fp = @fopen($fil, 'c+');
if ($fp && flock($fp, LOCK_EX)) {
  $tider = json_decode(stream_get_contents($fp) ?: '[]', true) ?: [];
  $tider = array_values(array_filter($tider, fn($t) => $t > time() - 3600));
  if (count($tider) >= MAX_HOUR) { flock($fp, LOCK_UN); fclose($fp); svar(429, ['ok' => false, 'error' => 'Många synpunkter just nu – försök igen om en stund.']); }
  $tider[] = time();
  ftruncate($fp, 0); rewind($fp); fwrite($fp, json_encode($tider));
  flock($fp, LOCK_UN); fclose($fp);
}

$amne = 'Sisyfos – ' . $kind . ($subject !== '' ? ': ' . $subject : '');
$text = $message . "\n\n—\n"
      . ($reply !== '' ? "Svar till: $reply\n" : "Anonym (ingen e-postadress angiven)\n")
      . ($info !== '' ? "$info\n" : '')
      . "Skickat " . date('Y-m-d H:i') . " via Sisyfos synpunktsformulär.\n";

$huvud = [
  'From: ' . FROM,
  'MIME-Version: 1.0',
  'Content-Type: text/plain; charset=UTF-8',
  'Content-Transfer-Encoding: 8bit',
  'X-Mailer: Sisyfos',
];
if ($reply !== '') $huvud[] = 'Reply-To: ' . $reply;

mb_internal_encoding('UTF-8');
$ok = mail(TO, mb_encode_mimeheader($amne, 'UTF-8', 'B'), $text, implode("\r\n", $huvud));
if (!$ok) svar(500, ['ok' => false, 'error' => 'Servern kunde inte skicka e-post.']);
svar(200, ['ok' => true]);
