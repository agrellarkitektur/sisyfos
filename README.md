# Sisyfos

Tidrapport och projektdagbok för en- och fåmansföretag. Körs i webbläsaren, även utan nät – inget konto behövs, ingen AI, ingen spårning. Vill du nå boken från flera enheter kan den sparas krypterad på webben, utan att servern kan läsa den.

## Om Sisyfos

<!--
  OM SISYFOS – skriv själv utifrån stödorden och ta sedan bort kommentaren:
  · tidrapport + projektdagbok, en- och fåmansföretag
  · kunder, projekt, tid per dag med anteckning
  · helt lokal: ingen server, inget konto, inget moln, ingen AI, ingen spårning
  · valfritt: krypterad lagring på webben för flera enheter – servern kan inte läsa boken
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

Sisyfos är en **alfaversion**. Den fungerar, men ändras fortfarande. Spara en kopia av boken som fil regelbundet (menyn *Sisyfos → Spara kopia som fil*).

## Smartshell

Fältet överst på alla sidor. Raden under fältet säger vad Enter gör innan något händer, och nästan allt kan ångras direkt efteråt. Klicka i fältet (eller skriv `?`) för hela förteckningen.

| Skriv | Gör |
|---|---|
| `3,5 strand ritade fasad` · `tor 8 strand` · `v43 fl` | tid – timmarna först, sedan projekt och anteckning |
| `v43` · `okt` · `idag` | går dit i tidboken |
| `ch` · `ch v43` · `öppna v43` · `sign v43` | checkar av, öppnar, signerar (bekräfta med `sign` eller `ok` + Enter, Esc avbryter) |
| `db okt strand` · `db ner okt strand` · `db ner öppet strand` | visar eller laddar ner projektdagboken |
| `pers fv` · `översikt 2025` | personsammanställning, månadsöversikt |
| `fakt strand` · `fakt kund smeden` · `fakt ner fm strand` · `fakt csv öppet strand` | visar eller laddar ner fakturaunderlaget (PDF eller CSV) |
| `hant fm strand` · `hant 1/10-15/10 strand` · `häv okt strand` | markerar en period som hanterad och låser, eller häver |
| `dag tor studieresa Sthlm` · `dag bort tor` | dagsanteckning – en kort text för hela dagen |
| `förk dbn = db ner` · `förk bort dbn` | egna kommandon: `dbn okt strand` blir `db ner okt strand` |
| `proj strand` · `proj Kv. Lärkan 2 100000 Diamanten` · `proj Tennis 100k 850` · `proj Golf 850/h` | öppnar eller skapar projekt (budget, timpris och kund valfritt – ett tal direkt efter budgeten är timpriset) |
| `kund Diamanten Bygg` · `uppg strand Bygglov` · `ant strand …` · `budget strand 180k` · `avsluta strand` | kunder, uppgifter, anteckningar, budget, status |
| `? strand` · `? öppet` · `? saldo` · `? v43` | frågor – svaret visas i panelen |

Perioder: `idag`, `tor`, `mån-fre`, `15/10-22/10`, `v40-43`, `fv` (förra veckan), `okt`, `sept-okt`, `fm` (förra månaden), `sept-`, `2026`, `öppet`. Ett projekt anges med ett ord ur namnet, numret eller en egen förkortning; namn med siffror kan skrivas inom citattecken.

## Enkelt läge

För dig som fakturerar din egen tid – till exempel konsult med eget bolag. Väljs i guiden för ny bok eller under *Inställningar → Läge*, och kan bytas när som helst utan att något försvinner.

- **Projekt med timpris och budget.** Timpriset anges direkt på projektet; tomt = ditt vanliga pris. Interna projekt (administration och liknande) finns kvar.
- **Inga kunder, ingen normtid, inget kompsaldo, ingen semester eller frånvaro.** Det som döljs ligger kvar i boken och syns igen i fullständigt läge.
- **En rapport: Öppen tid** – timmar och belopp som inte är hanterade, för alla projekt eller ett projekt, till och med vald månad. Med eller utan dagboksrader, som PDF eller CSV, och med *Markera som hanterat* när fakturan är skickad.

## Fakturaunderlag

Sisyfos gör alltid ett **underlag** att föra in i bokföringsprogrammet: *Rapporter → Fakturaunderlag*, eller knappen *Fakturaunderlag* på kund- och projektsidan. Riktiga fakturor är ett tillägg som slås på särskilt – se *Fakturor* nedan.

- Underlaget tar med **öppen debiterbar tid** för en kund (alla projekt) eller ett projekt, till och med vald månad eller för en egen period – som standard även äldre öppen tid. Hanterad tid ingår inte.
- Tiden summeras per projekt, uppgift, roll och timpris, med summa exkl. moms, moms och summa inkl. moms. Kundens fakturaadress, org.nr och referens står med.
- **PDF** att läsa eller bifoga och **CSV** (semikolon, decimalkomma, UTF-8) att öppna i Excel eller föra in i bokföringsprogrammet. Projektdagboken är specifikationen.
- **Markera som hanterat** låser tiden i underlaget per projekt – från den äldsta öppna tiden som ingår till periodens slut – så att den inte kommer med nästa gång. Det som redan är hanterat rörs inte.

### Hanterad tid

*Hanterad* betyder avstämd och fakturerad: projektets tid i perioden låses och kan inte ändras förrän markeringen hävs. Från 0.14.0 kan det vara **vilken period som helst** – en månad, två månader, halva oktober eller 28 september – 3 oktober:

- från månadsmenyn (en månad, eller *Hantera en annan period …*), projektdagboken (månad eller egen period), fakturaunderlaget och projektsidan (*Hanterad tid* listar perioderna med *Häv*),
- eller med smartshell: `hant 1/10-15/10 strand`, `hant v40-42 strand`, `hant öppet strand` (all öppen tid till och med förra månaden), `häv okt strand`.

Det som redan är hanterat rörs inte när en längre period markeras, och perioder som ligger kant i kant slås ihop. Att häva en del av en period delar den. Månadsöversikten visar en hel hanterad månad med ett lås och en delvis hanterad med ett ljusare lås.

## Fakturor

Från 0.15.0 kan Sisyfos göra **riktiga fakturor** med löpnummer, OCR och betal-QR direkt ur fakturaunderlaget. Det är ett tillägg som är av tills det slås på – i guiden för ny bok (steget *Fakturor*) eller under *Inställningar → Fakturor*. Innan det går att slå på måste villkoren godkännas:

- Varje faktura du utfärdar blir **räkenskapsinformation**. Du ansvarar för att innehållet är rätt och för att fakturorna **sparas i sju år**. Ladda ner arkivet regelbundet – webbläsaren är ingen arkivplats.
- En utfärdad faktura kan **aldrig ändras eller tas bort**. Fel rättas med en kreditfaktura.
- Numren löper i en **obruten serie**. Utfärda bara från en enhet – eller med boken synkad på webben, då delas numret ut först när synken har gått igenom.
- Sisyfos är fortfarande **inget bokföringsprogram**. Fakturorna förs in i ditt bokföringsprogram.
- Sisyfos är en **alfaversion utan garanti** (GPL). Det här är inte juridisk rådgivning – fråga din redovisningskonsult om något är oklart.

**Uppgifter.** Momsregistreringsnummer (föreslås ur org.nr: SE + org.nr + 01), bankgiro, plusgiro och/eller IBAN med BIC, Swish, betalningsvillkor i dagar, text om dröjsmålsränta, *Godkänd för F-skatt*, text före numret och första nummer, OCR, betal-QR, öresavrundning och en fri text längst ner. Företagets namn, adress och org.nr hämtas från *Inställningar → Företaget*. På kunden anges var den finns (Sverige, ett annat EU-land eller utanför EU), momsnummer och egna betalningsvillkor.

**Så gör man.** *Rapporter → Fakturaunderlag*: välj kund eller projekt och tryck *Skapa faktura* – ett **utkast** med en rad per projekt, uppgift, roll och pris och kundens fakturaadress. Utkastet går att ändra: kund, datum, villkor, referenser, rader (även egna rader, t.ex. utlägg), momssats och meddelande. *Utfärda* ger nästa nummer, fryser fakturan, låser tiden i underlaget (markerar den som hanterad) och laddar ner PDF:en. *Rapporter → Fakturor* listar utkast och utfärdade fakturor, och där finns *Tom faktura* för en faktura utan tid (till exempel fast pris).

**Rättelser.** *Kreditera* utfärdar en kreditfaktura med samma rader och negativa belopp, som hänvisar till originalet – och kan låsa upp tiden så att den kan faktureras på nytt. Häver man hanteringen av tid som ingår i en faktura varnar Sisyfos.

**Fakturan.** Innehåller det mervärdesskattelagen kräver av en fullständig faktura: fakturadatum, löpnummer, säljarens momsregistreringsnummer, namn och adress för säljare och köpare, vad som sålts och hur mycket, tidsperioden, belopp exkl. moms, momssats och momsbelopp – och därtill förfallodag, betalningsvillkor, dröjsmålsränta, bankgiro/plusgiro/IBAN, OCR och referenser. Med momssatsen 0 % står *Undantag från momsplikt* på fakturan. Allt som syns på en utfärdad faktura är kopierat in i den (även loggan), så **samma faktura ger alltid samma PDF** – utan utskriftsdatum, med en kontrollsumma (sha256) i sidfoten.

**OCR.** Välj det som står i ditt avtal med banken (Bankgiro Inbetalningar): ingen OCR (betalaren anger fakturanumret), OCR med kontrollsiffra eller OCR med längd- och kontrollsiffra. OCR-numret är fakturanumrets siffror, eventuellt en längdsiffra (antal siffror inklusive längd- och kontrollsiffra, modulo 10), och sist en kontrollsiffra enligt Luhn (modulus 10). Under *Inställningar → Fakturor* går det att kontrollera ett nummer. Bankens kontroll av OCR-nummer kräver ett avtal – utan det fungerar fakturanumret som referens.

**Betal-QR.** En QR-kod med betalningsuppgifterna i formatet för *QR-kod för betalning* (UsingQR: mottagare, org.nr, referens, datum, belopp, bankgiro/plusgiro/IBAN) som många bankappar kan läsa. Prova med din egen bankapp innan du litar på den.

**Numren och synken.** Nästa nummer är det högsta utfärdade plus ett (eller första numret). Med boken på webben synkas den före och efter utfärdandet, och utan nät går det inte att utfärda. Skulle två enheter ändå ge samma nummer samtidigt rättas det när böckerna slås ihop: den som utfärdades senare får nästa lediga nummer och fakturan visar det tidigare numret.

**Arkiv.** *Rapporter → Fakturor → Arkiv* laddar ner en zip per år med alla fakturor som PDF, en CSV-översikt och en JSON-fil med de frysta fakturorna. Spara den med din övriga bokföring. Panelen påminner om år vars arkiv inte är nedladdat.

**Betalningar** (0.15.1). Listan visar om en faktura är obetald, förfallen (och hur många dagar), betald eller krediterad, och filtren *Obetalda* och *Förfallna*. *Betald …* noterar datumet då pengarna kom – med Ångra, och det går att ändra eller ta bort. En kreditfaktura för en faktura som redan var betald visas som *att betala tillbaka* tills den är markerad som återbetald. Panelen visar obetalt och förfallet. Betalningarna ligger bredvid fakturorna (`register.payments`), så de frysta fakturorna och kontrollsummorna ändras inte.

**Kunder utomlands** (0.15.1). En kund i ett **annat EU-land** (ett företag med momsregistreringsnummer) får fakturor med **omvänd betalningsskyldighet**: ingen svensk moms, texten *Omvänd betalningsskyldighet (reverse charge)* och båda momsnumren. Försäljningen ska då också redovisas i en periodisk sammanställning till Skatteverket. En kund **utanför EU** får fakturor utan svensk moms med texten att tjänsten är omsatt utanför Sverige. Momsläget väljs av sig självt efter kunden och kan ändras i utkastet. Utländska kunder kan sällan betala till bankgiro – lägg in IBAN och BIC (Sisyfos varnar annars), och betal-QR kommer bara med på fakturor med svensk moms. Reglerna för var en tjänst är omsatt har undantag (till exempel tjänster som rör fastigheter, som räknas dit fastigheten finns) – fråga din redovisningskonsult om det gäller dig.

**SIE** (0.15.1). *Rapporter → Fakturor → Exportera SIE …* ger en SIE-fil (typ 4I, teckenkodning PC8) med de utfärdade fakturorna – och betalningarna, om du vill – som verifikationer att läsa in i bokföringsprogrammet. En faktura bokförs med kundfordringar i debet och försäljning och utgående moms i kredit (en kreditfaktura tvärtom), en betalning med banken i debet och kundfordringar i kredit. Kontona följer BAS och går att ändra: 1510 kundfordringar, 1930 bank, 3001/3002/3003 försäljning med 25/12/6 % moms och 2611/2621/2631 utgående moms, 3004 momsfri försäljning, 3308 tjänster till annat EU-land, 3305 tjänster utanför EU och 3740 öresavrundning. Verifikationsserien kan anges (tomt = bokföringsprogrammet väljer). Nästa export föreslås börja dagen efter den förra, och Sisyfos påminner om perioden överlappar – läs inte in samma verifikationer två gånger.

Kommer senare: påminnelsefaktura, flera momssatser på samma faktura, andra valutor, e-faktura (Peppol) och fakturakommandon i smartshell.

## Dagsanteckning och egna kommandon

- **Dagsanteckning** – en kort text för hela dagen (”studieresa Sthlm”, ”kurs”, ”mässa”) utöver anteckningarna per projekt. Skrivs i dagvyn, i panelen för en dag eller med `dag tor studieresa Sthlm`. Syns i veckans dagrubriker, i månadsvyn och i personsammanställningen. Låses med veckan.
- **Egna kommandon** i smartshell – ett eget ord som betyder ett kommando, med eller utan mer efter: `förk dbn = db ner` gör att `dbn okt strand` laddar ner dagboken. Listas och ändras under *Smartshell och förkortningar …* i Sisyfos-menyn (eller `förk`). Följer med boken till dina andra enheter.
- **Inställningar per enhet** – tema, panelens bredd, kompakt läge, utfällda rader, helgen och listornas filter sparas på varje enhet för sig och synkas inte. Telefonen kan alltså ha mörkt tema och datorn ljust.

Varför ingen riktig faktura? En faktura behöver löpnummer i obruten serie som aldrig återanvänds, kan inte ändras eller tas bort när den är utfärdad (bara krediteras) och ska arkiveras oförändrad. Det kräver ett eget, låst fakturaregister – det kan komma i en senare version.

## Var boken sparas

- Boken sparas **på din enhet**, i webbläsarens databas (IndexedDB) med en spegel i localStorage. Ingenting skickas någonstans – om du inte skapar ett konto och sparar den krypterad på webben (se nedan).
- Sisyfos ber webbläsaren om **beständig lagring**, så att boken inte rensas när utrymmet tryter.
- **Ögonblicksbilder** tas automatiskt före dagens första ändring (14 dagar bakåt) och före stora ändringar som import, ny bok och uppgradering. De kan återställas under *Inställningar → Spara boken*.
- **Kopia som fil**: *Spara kopia som fil* laddar ner hela boken som JSON. Sisyfos påminner om det efter en vecka (kan ändras).
- **Autospar till mapp** (Chrome och Edge på dator): välj en mapp – gärna en som säkerhetskopieras eller ligger i en molnmapp – så skriver Sisyfos boken dit vid varje ändring, plus en kopia per dag i undermappen *Säkerhetskopior*.
- Rensar du webbplatsdata för sidan försvinner boken ur webbläsaren. Då behövs en kopia.

## Kryptering

Sedan 0.12.0 kan boken sparas som en **krypterad kopia** (`.sisyfos`). Slå på krypteringen under *Inställningar → Spara boken → Kryptering*.

- **Två sätt att låsa upp.** Boken krypteras med en slumpad boknyckel (AES-256-GCM i webbläsarens Web Crypto). Boknyckeln låses dels med ditt lösenord (PBKDF2-SHA-256, 600 000 varv, eget salt), dels med en **återställningsnyckel** – 32 tecken som visas en gång och laddas ner som en PDF med QR-kod att skriva ut.
- **Lösenordet sparas ingenstans.** Byter du lösenord eller skapar en ny återställningsnyckel låses bara boknyckeln om; boken krypteras inte om, och gamla kopior öppnas med det som gällde när de sparades.
- **Öppna** en krypterad kopia med *Importera bok* – med lösenordet eller återställningsnyckeln. Krypteringen följer med till den nya enheten.
- Filen innehåller bara krypterad data plus det som behövs för att låsa upp den (salt, antal varv, de låsta nycklarna). Innehållet packas med gzip före krypteringen.
- Glömmer du både lösenordet och återställningsnyckeln går kopian inte att öppna – inte heller för Agrell Arkitektur.
- Smartshell: `kopia krypt`.

Samma nyckel används när boken sparas krypterad på webben: då lämnar varken lösenordet, boknyckeln eller boken i klartext enheten.

### Boken i delar och en nyckel per person (0.16.0)

Som grund för flera personer i samma bok krypteras boken sedan 0.16.0 i **delar** med en skribent var, och varje person har en **personlig nyckel**. Ensam märks ingen skillnad.

| Del | Innehåll | Skriver | Läser |
|---|---|---|---|
| `reg` – registret | företaget och inställningarna, kunder, roller, projekt (budget och timpriser), personernas namn, roll och offentliga nycklar, hanterade perioder (utan timmar och belopp) | admin | alla |
| `adm` | fakturor, betalningar, timmar och belopp för hanterad tid | admin | admin |
| `card.<person>` – personkortet | anställning, kompsaldo, semester och signerade veckor | admin | personen och admin |
| `log.<person>` – tidloggen | tidposterna och dagsanteckningarna; för den egna personen också bokens inställningar | personen | personen och admin |

- **Personlig nyckel:** ett nyckelpar för kryptering (ECDH P-256) och ett för signering (ECDSA P-256), skapade första gången boken sparas krypterad. De offentliga nycklarna står i registret; de privata ligger i en nyckelring som är låst med boknyckeln och följer med varje krypterad fil – så når du dem från alla dina enheter. Fingeravtrycket visas under *Kryptering*.
- **En del** krypteras med en egen slumpad nyckel (AES-256-GCM, gzip först), som i sin tur låses till varje läsare med en tillfällig ECDH-nyckel och HKDF – ungefär som verktyget *age*. Skribenten signerar delen. När filen öppnas kontrolleras signaturen och att skribenten får skriva delen; en ändrad del upptäcks.
- **Två enheter** som skapar nycklar samtidigt kommer överens: den äldsta nyckeln gäller.
- Filen har version 2 av det krypterade omslaget. Version 1 (0.12.0–0.15.1) öppnas som förut. En äldre app säger att boken kommer från en nyare version.
- Planen för flera personer – servern med organisationer (0.16.1) och arbetet med flera (0.16.2) – står i projektets planeringsdokument (etapp 4).

## Spara på webben

Sedan 0.13.0 kan boken sparas **krypterad på servern** där Sisyfos ligger, så att du når den från flera enheter – telefonen och datorn. Under *Inställningar → Spara boken → Spara på webben*:

- **Skapa konto** med en inbjudningskod, din e-postadress och ett lösenord. Är krypteringen inte på slås den på samtidigt, och du får en återställningsnyckel att skriva ut. Är den på loggar du in med krypteringens lösenord.
- **Logga in** på en annan enhet med e-postadressen och lösenordet. Boken hämtas och låses upp där. Finns redan en annan bok i webbläsaren frågar Sisyfos om den ska ersättas eller slås ihop med boken på webben.
- **Synk.** Varje ändring skickas krypterad några sekunder efter att den sparats, och boken hämtas vid start, när fönstret får fokus och när nätet kommer tillbaka. Utan nät fortsätter du som vanligt; ändringarna skickas när nätet finns. Sparindikatorn uppe till höger visar läget (*Synkad 10:42*, *Synkar …*, *Offline …*).
- **Två enheter samtidigt.** Har boken ändrats på båda sedan förra synken slås ändringarna ihop: tidposter, projekt, kunder och anteckningar från båda kommer med. Har samma sak ändrats olika på båda behålls den här enhetens version, och en dialog låter dig välja den andra enhetens i stället. En ögonblicksbild tas före sammanslagningen.
- **Tidigare versioner.** Servern sparar de tio senaste versionerna av boken. Under *Tidigare versioner …* kan en äldre version öppnas igen.
- **Byt lösenord** under Kryptering byter också inloggningen på webben – med möjlighet att logga ut dina andra enheter. Glömt lösenordet? Byt det med återställningsnyckeln på en enhet där du är inloggad.
- **Logga ut** den här enheten (boken ligger kvar, eller tas bort tillsammans med ögonblicksbilderna och nycklarna – t.ex. på en lånad dator) och **radera kontot** med allt på servern.
- Smartshell: `synk` synkar nu, `? synk` visar läget, `webb` öppnar inställningarna.

**Vad servern ser.** E-postadressen, när kontot skapades, vilka enheter som är inloggade och när de senast användes, och den krypterade boken med storlek och tidpunkter. Lösenordet lämnar aldrig enheten: ur det räknas 512 bitar fram med PBKDF2 – de första 256 låser upp boknyckeln, de sista 256 blir inloggningen, och servern sparar bara ett hashvärde (`password_hash`) av dem. Utan lösenordet eller återställningsnyckeln kan ingen läsa boken, inte heller den som driver servern.

**Ett ärligt förbehåll.** Krypteringen görs av appen, och appen hämtas från samma server. Den som kontrollerar servern skulle i teorin kunna byta ut appen. Sisyfos är öppen källkod och läggs bara ut på agrellarkitektur.se från det här repot via GitHub Actions; en installerad app minskar risken ytterligare.

### Servern

`api.php` är hela servern: PHP 8 utan databas, med JSON-filer och fillås. Den lägger sina data i mappen `sisyfos-data` två nivåer ovanför sig själv – utanför webbroten hos de flesta webbhotell – och annars i `data/` bredvid sig, spärrad med `.htaccess`. Kontots mapp får ett namn som inte går att gissa (HMAC av e-postadressen). Inga cookies, inga anrop från andra webbplatser (bara samma ursprung), och inget innehåll loggas. Gränser: 10 MB per bok, 20 MB per konto inklusive tidigare versioner, inloggningen gäller 90 dagar från senaste användning, och upprepade felaktiga inloggningar bromsas.

**Administratör.** Med adminnyckeln skapar du inbjudningskoder och ser och tar bort konton – i appen via länken *Administrera servern …* eller `webb admin` i smartshell. Nyckeln sparas aldrig i appen; servern har bara dess sha256 i `api-config.php`.

### Egen server

Vill du ha boken på ditt eget webbhotell: lägg Sisyfos med `api.php` i en mapp där (PHP 8.1 eller senare, https), och skapa `api-config.php` bredvid:

```php
<?php return ['admin' => '<sha256 av din adminnyckel>'];
```

Öppna Sisyfos från den adressen – appen använder alltid `api.php` i samma mapp. Kontrollera med `api.php?a=status` att `storage` är `outside`; är den `inside`, se till att `data/` inte går att läsa från webben.

## Data och integritet

Samma text finns i appen under *Sisyfos-menyn → Data och integritet*.

**Vad boken innehåller.** Företagets uppgifter och logga. Kunder: namn, organisations- eller personnummer, referens, kontaktperson, e-post, telefon, adresser och anteckningar. Projekt: namn, nummer, fastighetsbeteckning, budget, timpriser, uppgifter och anteckningar. Tid: datum, timmar, pris och anteckning för varje tidpost, dagsanteckningar, med historik över ändringar, avcheckning och signering; varje ändring märks med ett slumpat id för enheten den gjordes på (inget om själva enheten). Inställningar för boken, till exempel egna kommandon – det som bara gäller skärmen (tema, panelbredd, kompakt läge, utfällda rader, listfilter) sparas på varje enhet för sig och följer inte med boken. Om dig: namn, initialer, roll och timpris – i fullständigt läge även anställningsform, normtid, kompsaldo och semester. Med fakturor påslagna: fakturorna (köparens namn, adress, org.nr och referens, rader och belopp) och när de betalades, dina betalningsuppgifter (bankgiro, plusgiro, IBAN, Swish) och momsregistreringsnummer, och när villkoren godkändes. Personnummer, kontaktpersoner och anteckningar om människor är personuppgifter.

**Var den sparas.** I webbläsaren på enheten, tillsammans med automatiska ögonblicksbilder (se ovan). **Med konto på webben** dessutom krypterad på servern där Sisyfos ligger (agrellarkitektur.se, ett webbhotell hos Loopia i Sverige): e-postadressen, när kontot skapades, inloggade enheter och när de senast användes, och den krypterade boken med de tio senaste versionerna, deras storlek och tidpunkter. Lösenordet, boknyckeln och innehållet lämnar aldrig enheten okrypterade, och kontot med allt på servern kan raderas när du vill. Krypteringen görs av appen, som hämtas från samma server – se förbehållet under *Spara på webben*. Filer du själv sparar – kopior, autospar till mapp, PDF och CSV – är vanliga, okrypterade filer. Krypterade kopior (`.sisyfos`) kan bara öppnas med ditt lösenord eller din utskrivna återställningsnyckel; glömmer du båda går de inte att öppna, inte heller för oss. Sedan 0.16.0 krypteras boken i delar och du har en personlig nyckel, vars privata del bara finns låst i dina krypterade filer. Ingen annan kan läsa boken, inte heller Agrell Arkitektur, och därför kan ingen heller återställa den åt dig.

**Vad som skickas över nätet.** Appen hämtas från agrellarkitektur.se, och webbhotellet för som alla webbservrar tekniska loggar över anrop (IP-adress, tidpunkt, vilken fil) – inget ur boken följer med. Synpunkter skickas bara när du trycker på Skicka: det du skrivit, din e-postadress om du anger den och, om du vill, version och skärmstorlek. `feedback.php` skickar det vidare som e-post och sparar ingenting. Med konto på webben: den krypterade boken när den ändras, e-postadressen och en inloggning som räknas fram ur lösenordet (servern sparar bara ett hashvärde av den); webbhotellets loggar visar då också IP-adress och tidpunkt för synken. Inget annat: ingen statistik, spårning, reklam, AI eller tjänster från andra företag, och typsnitten är inbyggda.

**Ditt ansvar.** Du ansvarar för personuppgifterna du för in, som för ett eget kalkylark. Utan konto på webben når inget ur boken Agrell Arkitektur. Med konto sparar vi din e-postadress och den krypterade boken – som vi inte kan läsa – bara för att tjänsten ska fungera. Lagringen på webben är ett test utan garanti; ändras eller avvecklas den får du besked till e-postadressen, och boken finns kvar på dina enheter. Skriv inte mer om människor än uppdraget kräver. Sisyfos är en alfaversion och fri programvara under GPL, utan garanti – kontrollera underlagen och spara kopior.

## Installera som app

Sisyfos är en PWA och fungerar utan nät.

- **Chrome/Edge på dator:** installera-ikonen i adressfältet, eller *Installera som app* i Sisyfos-menyn. Appen och webbläsaren delar samma bok.
- **iPhone/iPad:** *Dela → Lägg till på hemskärmen*. Obs! Hemskärmsappen får en **egen lagring**, skild från Safari/Chrome. Spara boken som fil i webbläsaren och importera den i appen.

## Filformat och bakåtkompatibilitet

Boken är en JSON-fil med versionsnummer (`format`). Varje ändring av formatet får en migrering, och **gamla böcker går alltid att öppna** i nyare versioner. En bok från en nyare version öppnas inte av en äldre – och skrivs aldrig över.

Format 10 (0.16.0) lade till organisationen (`register.org = {id, created}` – id:t räknas fram ur bokens skapad-datum, så samma bok får samma id på alla enheter) och personernas offentliga nycklar (`register.people[].keys`, när boken sparas krypterad). Den krypterade filen fick version 2 med delar – se *Kryptering*.

Format 9 (0.15.0) lade till fakturor (`register.invoices`, med de loggor fakturorna använde i `register.invoiceLogos`) och inställningarna för dem (`book.invoicing`). I 0.15.1 kom betalningarna (`register.payments`), kundens land (`zone`) och fakturans momsläge (`vatMode`) som valfria fält – formatet är fortfarande 9. Utfärdade fakturor är frysta och har en kontrollsumma som testet räknar om.

Format 8 (0.14.0) ändrade hanterad tid från hela månader till datumintervall per projekt (`register.handled[projekt] = [{from, to, …}]`), lade till dagsanteckningar (händelsetypen `daynote`), egna kommandon (`prefs.aliases`) och enhets-id på händelser (`dev`), och flyttade skärminställningarna ur boken till enheten.

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
| `api.php` | Servern för lagring på webben – tar bara emot krypterade böcker |
| `test/` | Gamla böcker och kontrollen att de öppnas (`oppna_gamla_bocker.py`), test av fakturorna (`faktura_test.py` och `faktura2_test.py` – betalningar, kunder utomlands och SIE), test av boken i delar och nycklarna (`delar_test.py`), test av servern (`api_test.py`) och av synken mellan två enheter (`webb_test.py`, körs för hand). För hand vid omskrivningar: `stor_bok.py` bygger en testbok på tio år, `prestanda.py` mäter vanliga åtgärder med den och `jamfor_versioner.py` kontrollerar att skärmarna är lika med en tidigare version |

## Publicera på ett webbhotell

Lägg alla filer i roten (utom `test/`, README och LICENSE) i samma mapp, till exempel `/sisyfos/`. Appen behöver https för att fungera offline. `feedback.php` kräver att PHP:s `mail()` fungerar; peka `FEEDBACK_URL` i `index.html` dit. `api.php` kräver PHP 8.1 eller senare – se *Egen server*.

### Arbetsflöden

- **Publicera på webbhotellet** – laddar upp appen via FTPS vid varje push till `main`. Aktiveras när hemligheterna `FTP_SERVER`, `FTP_USERNAME` och `FTP_PASSWORD` finns (frivilligt `FTP_DIR`, standard `/sisyfos/`, och `FTP_PROTOCOL`, standard `ftps`).
- **Release-zip** – när en release publiceras på GitHub (tagg `vX.Y.Z`) läggs `sisyfos-vX.Y.Z.zip` till, färdig att lägga på webbhotellet (appen, `feedback.php` och `api.php`). Taggen måste ligga på en commit där `APP_VERSION` i `index.html` är samma version – GitHub föreslår `main` som *Target*, så har `main` hunnit få en nyare version väljs rätt commit under *Target → Recent commits*. Blir det fel säger körningen vilken commit som har versionen. Arbetsflödet kan också köras för hand med taggen och en annan commit (`ref`).
- **Publicera på webbhotellet** skriver också `api-config.php` med sha256 av hemligheten `SISYFOS_ADMIN_KEY` (adminnyckeln för inbjudningskoder) och kontrollerar efteråt att `api.php?a=status` svarar och att datamappen inte går att läsa från webben.
- **Test – gamla böcker öppnas** – se ovan. Kör också `test/delar_test.py` (boken i delar och nycklarna) och `test/api_test.py` (servern i båda lagringslägena).

## Licens

Fri programvara under [GNU GPL v3](LICENSE) eller senare. Typsnitten Archivo och IBM Plex Mono är inbyggda under SIL Open Font License 1.1.
