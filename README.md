# Sisyfos

Tidrapport och projektdagbok för en- och fåmansföretag. Körs helt lokalt i webbläsaren – ingen server, inget konto, inget moln, ingen AI.

## Om Sisyfos

<!--
  OM SISYFOS – skriv själv utifrån stödorden och ta sedan bort kommentaren:
  · tidrapport + projektdagbok, en- och fåmansföretag
  · kunder, projekt, tid per dag med anteckning
  · helt lokal: ingen server, inget konto, inget moln, ingen AI, ingen spårning
  · inte bokföring/fakturering – PDF-underlag till egna system
  · löpande mot budget, påminnelser 50/75/90 %, öppet vs hanterat
  · smartshell: tid, kommandon och frågor på en rad, överst på alla sidor (nytt i 0.9)
  · dag-, vecka- och månadsvy, mobil
  · fungerar utan nät, kan installeras som app (nytt i 0.7)
  · boken skyddas: ögonblicksbilder, påminnelse om kopia, autospar till mapp (nytt i 0.7)
  · alfa, synpunkter välkomna
  · namnet: Sisyfos och stenen
-->

## Prova

Öppna **https://agrellarkitektur.se/sisyfos/**. Sisyfos startar med en exempelbok; skapa din egen bok under menyn *Sisyfos → Ny tom bok*.

Sisyfos är en **alfaversion**. Den fungerar, men ändras fortfarande. Spara en kopia av boken som fil regelbundet (menyn *Sisyfos → Säkerhetskopior*).

## Smartshell

Fältet överst på alla sidor. Raden under fältet säger vad Enter gör innan något händer, och nästan allt kan ångras direkt efteråt. Klicka i fältet (eller skriv `?`) för hela förteckningen.

| Skriv | Gör |
|---|---|
| `3,5 strand ritade fasad` · `tor 8 strand` · `v43 fl` | tid – timmarna först, sedan projekt och anteckning |
| `v43` · `okt` · `idag` | går dit i tidboken |
| `ch` · `ch v43` · `öppna v43` · `sign v43` | checkar av, öppnar, signerar |
| `db okt strand` · `db ner okt strand` · `db ner öppet strand` | visar eller laddar ner projektdagboken |
| `pers fv` · `översikt 2025` | personsammanställning, månadsöversikt |
| `hant fm strand` · `häv okt strand` | markerar som hanterad och låser, eller häver |
| `proj strand` · `proj Kv. Lärkan 2 100000 Diamanten` | öppnar eller skapar projekt (budget och kund valfritt) |
| `kund Diamanten Bygg` · `uppg strand Bygglov` · `ant strand …` · `budget strand 180k` · `avsluta strand` | kunder, uppgifter, anteckningar, budget, status |
| `? strand` · `? öppet` · `? saldo` · `? v43` | frågor – svaret visas i panelen |

Perioder: `idag`, `tor`, `mån-fre`, `15/10-22/10`, `v40-43`, `fv` (förra veckan), `okt`, `sept-okt`, `fm` (förra månaden), `sept-`, `2026`, `öppet`. Ett projekt anges med ett ord ur namnet, numret eller en egen förkortning; namn med siffror kan skrivas inom citattecken.

## Var boken sparas

- Boken sparas **bara på din enhet**, i webbläsarens databas (IndexedDB) med en spegel i localStorage. Ingenting skickas någonstans.
- Sisyfos ber webbläsaren om **beständig lagring**, så att boken inte rensas när utrymmet tryter.
- **Ögonblicksbilder** tas automatiskt före dagens första ändring (14 dagar bakåt) och före stora ändringar som import, ny bok och uppgradering. De kan återställas under *Inställningar → Säkerhetskopior*.
- **Kopia som fil**: *Spara kopia som fil* laddar ner hela boken som JSON. Sisyfos påminner om det efter en vecka (kan ändras).
- **Autospar till mapp** (Chrome och Edge på dator): välj en mapp – gärna en som säkerhetskopieras eller ligger i en molnmapp – så skriver Sisyfos boken dit vid varje ändring, plus en kopia per dag i undermappen *Säkerhetskopior*.
- Rensar du webbplatsdata för sidan försvinner boken ur webbläsaren. Då behövs en kopia.

## Installera som app

Sisyfos är en PWA och fungerar utan nät.

- **Chrome/Edge på dator:** installera-ikonen i adressfältet, eller *Installera som app* i Sisyfos-menyn. Appen och webbläsaren delar samma bok.
- **iPhone/iPad:** *Dela → Lägg till på hemskärmen*. Obs! Hemskärmsappen får en **egen lagring**, skild från Safari/Chrome. Spara boken som fil i webbläsaren och importera den i appen.

## Filformat och bakåtkompatibilitet

Boken är en JSON-fil med versionsnummer (`format`). Varje ändring av formatet får en migrering, och **gamla böcker går alltid att öppna** i nyare versioner. En bok från en nyare version öppnas inte av en äldre – och skrivs aldrig över.

`test/bocker/` innehåller en exempelbok per filformat. Arbetsflödet *Test – gamla böcker öppnas* kontrollerar vid varje push att alla fortfarande öppnas:

```sh
pip install playwright && python3 -m playwright install chromium
python3 -m http.server 8765 &
python3 test/oppna_gamla_bocker.py
```

## Filer

| Fil | Vad |
|---|---|
| `index.html` | Hela appen i en fil (typsnitten inbyggda, inga anrop till andra servrar) |
| `sw.js` | Service worker – gör att appen startar utan nät |
| `manifest.webmanifest`, `icon.svg`, `*.png` | Appikon och installation |
| `feedback.php` | Tar emot synpunktsformuläret och skickar det som e-post. Sparar ingenting |
| `test/` | Gamla böcker och kontrollen att de öppnas |

## Publicera på ett webbhotell

Lägg alla filer i roten (utom `test/`, README och LICENSE) i samma mapp, till exempel `/sisyfos/`. Appen behöver https för att fungera offline. `feedback.php` kräver att PHP:s `mail()` fungerar; peka `FEEDBACK_URL` i `index.html` dit.

### Arbetsflöden

- **Publicera på webbhotellet** – laddar upp appen via FTPS vid varje push till `main`. Aktiveras när hemligheterna `FTP_SERVER`, `FTP_USERNAME` och `FTP_PASSWORD` finns (frivilligt `FTP_DIR`, standard `/sisyfos/`, och `FTP_PROTOCOL`, standard `ftps`).
- **Release-zip** – när en release publiceras på GitHub (tagg `vX.Y.Z`) läggs `sisyfos-vX.Y.Z.zip` till, färdig att lägga på webbhotellet. Taggen måste stämma med `APP_VERSION` i `index.html`.
- **Test – gamla böcker öppnas** – se ovan.

## Licens

Fri programvara under [GNU GPL v3](LICENSE) eller senare. Typsnitten Archivo och IBM Plex Mono är inbyggda under SIL Open Font License 1.1.
