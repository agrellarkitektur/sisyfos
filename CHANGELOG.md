# Ändringar i Sisyfos

## 0.11.2

Rättning efter test. Filformatet är oförändrat (7).

- **Rapportförslagen ligger under val och knappar** i Projektdagbok och Fakturaunderlag (och Öppen tid i enkelt läge), med rubriken *Rapportförslag* ovanför knapparna. Förut låg de över projekt- och datumväljaren och syntes dåligt.

## 0.11.1

Småjusteringar. Filformatet är oförändrat (7) – standarduppgiften sparas som ett nytt, valfritt fält (`book.defaultTasks`).

- **Nya projekt får en uppgift, Utredning**, i stället för Skiss och Bygglov. Vilka uppgifter nya projekt ska få anges i guiden för ny bok och under *Inställningar → Nya projekt*.
- **Lägesknapp** bredvid temaknappen: *Enkelt | Fullt* byter läge direkt, med Ångra.
- **Rubriken blir "Fakturaunderlag och dagbok"** när dagboksrader är ikryssade, på skärmen, i PDF:en och i filnamnet.
- **Månadsöversikten:** projektets namn eller nummer går till projektsidan, kundnamnet till kunden, och ett klick någon annanstans på raden öppnar en meny (projektet, kunden, tidboken, dagboken, all öppen tid, fakturaunderlag). Månadsmenyn har också *Gå till projektet*.
- **Förslag på rapporter:** överst i Projektdagbok och Fakturaunderlag (och Öppen tid i enkelt läge) visas det som har öppen tid, äldst först – ett klick tar fram rapporten.
- **Smartshell – timpris i `proj`:** `proj Tennis 100k 850` eller `proj Golf 850/h` (även `850 kr/h`). Ett tal direkt efter budgeten är timpriset; med `/h` kan det stå var som helst.
- **Signera från tangentbordet:** bekräftelsen har en ruta där `sign` eller `ok` + Enter signerar och Esc avbryter. Fokus går tillbaka till smartshell.
- **Data och integritet:** ny ruta (Sisyfos-menyn, Om Sisyfos, Synpunkter och *Spara boken*) som beskriver vilken data boken innehåller, var den sparas, vad som skickas och vem som ansvarar för vad. Samma text står i README.

## 0.11.0

Enkelt läge. Filformatet är oförändrat (7) – läget sparas som ett nytt, valfritt fält i boken (`book.mode`) som äldre versioner bortser från.

- **Enkelt läge** för den som fakturerar sin egen tid: bara projekt med timpris och budget, intern tid och en rapport över öppen tid. Kunder, roller, normtid, kompsaldo, semester och frånvaro döljs. Väljs i guiden för ny bok eller under *Inställningar → Läge* och kan bytas fram och tillbaka utan att något försvinner.
- **Timpris direkt på projektet** i enkelt läge, i Nytt projekt och Redigera projekt. Priset syns på projektkortet, projektsidan och raden i veckan.
- **Rapporten Öppen tid**: alla projekt eller ett projekt, till och med vald månad, med summa per projekt, moms och summa inkl. moms – PDF, CSV och *Markera som hanterat*.
- **Fakturaunderlaget** (även i fullständigt läge) kan nu gälla *Alla projekt* och visa **dagboksrader** med datum och anteckning för varje projekt.
- Smartshell: `kund`, `pers` och `översikt` säger vänligt att de finns i fullständigt läge; förteckningen visar bara det som går att använda.

## 0.10.0

Fakturaunderlag. Filformatet är oförändrat (7).

- **Ny rapport: Fakturaunderlag.** Öppen debiterbar tid för en kund (alla projekt) eller ett projekt, summerad per uppgift, roll och timpris, med moms och summa inkl. moms och kundens fakturaadress, org.nr och referens. Som standard tas all äldre öppen tid med.
- **PDF och CSV.** CSV-filen har semikolon och decimalkomma och öppnas rätt i Excel – en rad per projekt, uppgift och pris, färdig att föra in i bokföringsprogrammet.
- **Markera som hanterat** direkt från underlaget låser alla månader som helt ingår i det, med en Ångra. Månader där projektet har tid utanför underlaget hanteras inte och visas för sig.
- Genvägar: knappen *Fakturaunderlag* på kund- och projektsidan och i månadsmenyn. Panelen visar vad underlaget innehåller och vilka kunder som har öppen tid.
- **Smartshell:** `fakt strand`, `fakt kund smeden`, `fakt ner fm strand` (PDF), `fakt csv öppet strand`. Även `fu`.

## 0.9.1

Småjusteringar. Filformatet är oförändrat (7).

- **Inställningar är lika breda som övriga sidor**, så att innehållet inte hoppar när man byter sida.
- **Asterisk för det som krävs** i guiden för ny bok, Ny kund, Nytt projekt, Redigera projekt och Inställningar, med en förklarande rad i varje formulär.
- **"Spara" i stället för "säkerhetskopia"**: menyn har *Spara kopia som fil* (direkt) och *Spara och återställ …*, avsnittet i Inställningar heter *Spara boken*, och knapparna har en diskett i stället för hänglås.

## 0.9.0

Smartshell. Filformatet är oförändrat (7).

- **Smartanteckningen heter nu smartshell** och står överst på alla sidor – på dator fäst när man rullar. Tid skrivs som förut, med timmarna först.
- **Kommandon med verbet först**, sedan period och projekt: `ch v43` checkar av, `öppna v43`, `sign v43` (med bekräftelse), `db okt strand` visar projektdagboken och `db ner okt strand` laddar ner den, `db ner öppet strand` tar all öppen tid, `pers fv`, `översikt 2025`, `hant fm strand` och `häv okt strand`.
- **Skapa och ändra**: `proj …` öppnar ett projekt eller skapar det med budget och kund (`proj Kv. Lärkan 2 100000 Diamanten`), `kund …` öppnar eller skapar en kund, `uppg`, `ant`, `budget`, `aktiv`/`inaktiv`/`avsluta`.
- **Frågor** med `?`: `? strand`, `? öppet`, `? saldo`, `? v43`, `? okt` – svaret visas i egenskapspanelen.
- **Perioder** överallt: `idag`, `tor`, `15/10-22/10`, `v40-43`, `fv`, `okt`, `sept-okt`, `fm`, `sept-`, `2026`, `öppet`. Bara en period hoppar dit i tidboken.
- Namn med siffror fungerar: en budget är minst fyra siffror, `100 000`, `100k` eller `löp`; annars skrivs namnet inom citattecken.
- Raden under fältet säger alltid vad Enter gör. Nästan allt kan ångras direkt. **Tab** fyller i kommandon, projekt och kunder; **pil upp** hämtar tidigare rader (sparas bara i webbläsaren).
- **Förteckningen över kommandon** visas i egenskapspanelen när man klickar i fältet, med det kommando man skriver överst. Klick på ett exempel lägger in det. På telefon öppnas den med `?`.
- Egna förkortningar för kommandon kommer med nästa filformat; förkortningar för projekt och uppgifter finns som förut.

## 0.8.1

Egenskapspanelen på alla sidor. Filformatet är oförändrat (7).

- **Panelen finns på alla sidor**, så att innehållet inte hoppar när man byter sida. Utfällt eller infällt läge sparas och är detsamma överallt.
- Utanför tidboken visar panelen läget på sidan och kort hjälp: projekt och kunder att fakturera (äldst först) och budgetar som snart tar slut i listorna, öppna månader med "redo"-status på projektsidan, innehållsförteckning i Inställningar.
- **Projektdagboken**: panelen visar äldsta ohanterade tid och hur mycket öppen tid som ligger före, i och efter den valda perioden, med knappar för att börja perioden vid den äldsta öppna tiden eller ta med all öppen tid. Projektsidan har knappen *Dagbok för all öppen tid*.
- **Redan hanterad tid i dagboken**: rader som ingår i en hanterad månad är gråa, på skärmen och i PDF:en, och sammanställningen visar "varav redan hanterat".

## 0.8.0

Sparad semester per år. **Nytt filformat 7** – böcker från tidigare versioner uppgraderas när de öppnas (en ögonblicksbild tas först). En bok som sparats i 0.8 kan inte öppnas i 0.7.

- Semesterkontot räknar själv vid varje årsskifte: årets dagar tas ut först, därefter sparade dagar, äldsta först. Outtagna dagar sparas – högst dagarna utöver de 20 som ska tas ut och högst 5 per år – och resten betalas ut som semesterlön. Sparade dagar som är äldre än 5 år betalas ut.
- Reglerna (dagar som ska tas ut, högst sparade per år, antal år) går att ändra efter kollektivavtal och gäller hela boken.
- Semestern kan visas som en pott eller som årets dagar och sparade för sig, med sparade dagar per år (år 1–5) och sista dag att ta ut dem.
- Sparade dagar anges per år, både i *Anställning, saldo och semester* och i guiden för ny bok ("Har du sparad semester från tidigare år?").
- Uppgradering: den tidigare "Sparade dagar in i året" blir sparade dagar från förra semesteråret.

## 0.7.1

Små justeringar. Filformatet är oförändrat (6).

- Vyerna ligger i ordningen **Månad – Vecka – Dag**.
- Avcheckade och signerade veckor markeras med fasta färger i stället för streck: grönt för avcheckad, blått för signerad (veckonummer och dagrutor i månadsvyn, veckans statusknapp och ruta).
- **Redo att hanteras**: projektsidans månader och månadsvyns projekttabell visar för avslutade månader om alla timmar ligger i avcheckade veckor ("redo") eller vilka veckor som inte är avcheckade. Månadsmenyn säger detsamma, och den som markerar en månad som hanterad varnas om veckor inte är avcheckade.

## 0.7.0

Trygg lagring och månadsvy. Filformatet är oförändrat (6) – böcker från 0.6 öppnas direkt och kan fortfarande öppnas i 0.6.

**Lagring och säkerhetskopior**
- Boken sparas i webbläsarens databas (IndexedDB) med en spegel i localStorage. Vid start väljs det senast sparade, så boken finns kvar även om det ena lagret rensas.
- Sisyfos ber om beständig lagring.
- Ögonblicksbilder före dagens första ändring (14 dagar) och före import, ny bok, exempelboken, återställning och uppgradering (12 st). Kan återställas och laddas ner under *Inställningar → Säkerhetskopior*.
- Påminnelse om säkerhetskopia (standard efter en vecka, kan ändras eller stängas av).
- Autospar till en vald mapp i Chrome och Edge på dator, med en kopia per dag.
- En bok som inte kan öppnas – eller som kommer från en nyare version – skrivs aldrig över. Den kan sparas som fil direkt från felmeddelandet.
- Två flikar med Sisyfos skriver inte över varandra: den andra fliken läser in det senaste.

**App och offline**
- Installeras som app (PWA) och startar utan nät. Favicon och appikoner.

**Tid**
- Ny **månadsvy**: kalender med tid per dag i projektfärger, veckornas status (avcheckad, signerad, inte avcheckad), månadens nyckeltal och tid per projekt. Klicka på en dag, ett veckonummer eller ett projekt.
- Projektsidan: klick på en månad → **Gå till tidboken**, som öppnar månadsvyn med projektet markerat.

**Övrigt**
- *Öppet* är orange så länge de öppna timmarna bara finns i innevarande månad, och en mindre mättad röd när äldre månader väntar på att faktureras.
- Färgval direkt i *Nytt projekt*.
- "Alfa" med versionsnummer i knappen uppe till höger.
- Synpunktsformuläret (`feedback.php`): kuvertavsändare, Message-ID och Date sätts så att Gmail tar emot vidarebefordrade brev.
- Rättat: den orange ringen för tider utan anteckning hamnade längst upp till höger på sidan i tabeller.

## 0.6

Kund- och projektsidor, öppet/hanterat, guide för ny bok, inbyggda typsnitt, filformat 6.
