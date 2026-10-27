# Ändringar i Sisyfos

## 0.18.0

Filformat 11, oförändrat (personkortet har två nya valfria fält). **Arbetet med flera** – steg 3 av etapp 4. Ladda om på alla enheter i organisationen: en enhet med 0.17.x ser inte veckor som admin har öppnat åt någon annan.

- **Vems tidbok.** Administratören väljer med knappen *Din tid* ovanför veckan vems tidbok som visas – veckan, månaden, dagen, saldot och semestern gäller då den personen. Menyn visar för varje person vilka veckor de senaste tolv veckorna som inte är avcheckade. En annans tid är **skrivskyddad**: admin skriver aldrig i någon annans tid (inte heller i smartshell), utan öppnar veckan så att personen rättar själv.
- **Öppna, signera och låsa upp åt andra.** I en medarbetares tidbok har raden överst *Öppna åt Anna* och *Signera* för en avcheckad vecka och *Lås upp …* för en signerad. Det sparas i personens kort (som admin skriver) – checkar personen av igen gäller det på nytt. I smartshell: `sign v43 Anna`, `öppna v40-42 Anna Berg` (förnamn, efternamn, hela namnet eller initialer).
- **Anställning, saldo och semester** för en medarbetare ändrar admin i personens tidbok (*Anna Bergs anställning, saldo och semester …* i menyn). Medarbetaren ser sina uppgifter men ändrar dem inte.
- **Så påverkas summan tar med medarbetarnas tid.** När admin ändrar ett pris visar dialogen också medarbetarnas rapporterade tid. Admin godkänner i dialogen – också om avcheckad tid ska få det nya priset – och godkännandet sparas i personens kort. Medarbetarens app räknar om hennes egen tid nästa gång hon synkar, med ett besked; signerad och hanterad tid rörs aldrig. När omräkningen är gjord tar admins app bort den.
- **Timpris för en person i smartshell:** `proj Tennishallen 100k Anna 850` skapar projektet med Annas pris, `proj strand Anna 1100` sätter Annas pris i ett befintligt projekt från i dag (via *Så påverkas summan* när rapporterad tid berörs). Namnet tolkas bara som en person om det är en befintlig persons.
- **Projektsidans Medarbetare** visar varje person med roll, pris i projektet, timmar, belopp, öppet och veckor som inte är avcheckade – och för admin en knapp till personens tidbok.
- **Personsammanställningen** har ett val av person för admin.
- **Medarbetarens gränssnitt.** Det medarbetaren inte skriver syns men går inte att ändra: inga knappar för nytt projekt, redigera projekt eller kund, budget, hantering, roller och timpriser; bokens inställningar är skrivskyddade (tema, visning och *Spara boken* går att använda); smartshell säger ifrån för `budget`, `hant`, `uppg`, `ant`, nya projekt och kunder. Budgetens förbrukning visas bara för admin.
- Test: `test/flera_test.py` (ny, körs i GitHub).

## 0.17.2

Filformat 11, oförändrat. Synpunkterna från 27 oktober.

- **Så påverkas summan.** En prisändring som rör rapporterad tid visas i en dialog *innan* den sparas – samma dialog oavsett om priset ändras i projektet, för kunden, på en uppgift eller centralt under Inställningar. Tabellen visar per projekt och uppgift timmarna, beloppet före och efter, skillnaden och budgetens nya procent. Tid i avcheckade veckor väljs i dialogen (*Använd det nya priset* är förvalt, eller *Behåll de gamla priserna*); signerad och hanterad tid behåller sitt pris och nämns under tabellen. *Avbryt* (eller Esc) lämnar både priset och tiden orörda. Rör ändringen ingen rapporterad tid sparas den direkt som förut. Dialogen ersätter frågan *Tid med ett annat timpris* från 0.17.1.
- **Månadsvyn i tidboken.** Hela projektraden under kalendern är klickbar: projektet markeras i kalendern och smartmenyn öppnas (dagbok, fakturaunderlag, hantering, *Sluta markera i kalendern*). Projektets uppgifter fälls ut under raden och kan markeras för sig. *+ Projekt eller uppgift* markerar ett projekt som inte har tid i månaden. Klicka sedan på en dag så öppnas samma smartmeny som i veckovyn – timmar, snabbval, anteckning och Rensa – med projektets uppgifter som knappar överst (den markerade, annars den senast använda).
- **Enter till smartshell.** Trycker du Enter när inget fält, ingen knapp, meny eller dialog har fokus hamnar markören i smartshell.
- **Startruta i stället för exempelboken.** Första gången (ingen egen bok på enheten och inte inloggad) väljer du *Logga in och synka*, *Öppna en bok från fil* eller *Starta en ny bok* – och den som har en inbjudningskod kan skapa ett konto. *Titta på exempelboken* finns som länk under valen och i Sisyfos-menyn.
- Test: `test/manad_test.py` (ny, körs i GitHub) – månadsvyn, Enter och startrutan; `test/priser_test.py` utökat med dialogen, Avbryt och Esc.

## 0.17.1

Filformat 11, oförändrat. Rättningar efter test av 0.17.0.

- **Timpriser bakåt i tiden.** Ett pris som först sattes *från i dag* gick inte att rätta till *från början* eller ett tidigare datum utan att ändra beloppet – Sisyfos såg ingen ändring, och tiden som redan var rapporterad behöll det gamla priset tills rutan rensades. Nu räknas det som en ändring när priset skrivs om eller datumet byts, och rapporterad tid från datumet med ett annat sparat pris får det nya priset.
- **Avcheckad tid frågas om.** Finns det tid i avcheckade veckor med ett annat pris visar Sisyfos en varning och låter dig välja: *Använd det nya priset* eller *Behåll de gamla priserna* (med Ångra). Signerad tid behåller sitt pris (lås upp veckan först), hanterad och fakturerad tid räknas aldrig om.
- **Rensa i egenskapspanelen** – samma som *Rensa rutan* i smartmenyn.
- **Snabbknappar för tiden i smartmenyn** (½, 1, 2, 4 och 8 timmar), som i egenskapspanelen.
- **Panelens rubrik leder till projektsidan** – klicka på projektnamnet, numret, uppgiften eller timpriset överst i egenskapspanelen.
- **Projekt › Månader:** hela raden öppnar menyn, inte bara månadens namn.
- **`db strand`** visar projektdagboken för all ohanterad tid i projektet, inte bara innevarande månad. En månad anges som förut (`db okt strand`).
- **Projektdagboken i ny uppställning:** tiden grupperas per medarbetare (när fler än en har tid i perioden) och per uppgift med à-pris, timmar och belopp, och under varje uppgift datum, anteckning, timmar och belopp. Sist en sammanställning per medarbetare (eller per uppgift för den som är ensam) och totalsumman. Samma på skärmen och i PDF:en.
- Arbetet med flera personer (välja vems tidbok, signera åt andra med mera) kommer i 0.18.0.

## 0.17.0

Filformat 11 – **timpriser med datum, på kund och uppgift, och signering efter behov**. Böcker i format 10 och äldre uppgraderas när de öppnas, och inga belopp ändras. Ladda om på alla enheter: en enhet med 0.16.x kan inte öppna boken efteråt och säger att den kommer från en nyare version.

- **Timpris på kunden och på uppgiften.** Ordningen är bok → kund → projekt → du i projektet → uppgift, och det mest specifika priset gäller. Kunden får pris per roll (*Redigera kund → Timpriser för kunden*), uppgiften ett pris för alla roller (rutan *kr/h* på uppgiftens rad i *Redigera projekt*).
- **Priset gäller från ett datum.** När ett pris ändras väljer du *från* ett datum (i dag som standard) eller *från början*. Ett pris med datum blir en prislista: tid som skrivs in i efterhand för en tidigare dag får priset som gällde då. Prislistan visas under priserna, i Inställningar och på projektsidan.
- **Olåst tid följer prislistan.** Förut behöll varje tidpost priset den fick när den skrevs in, även när priset varit fel från början. Nu får de egna tidposter som inte är avcheckade, signerade eller hanterade det nya priset från datumet – låst tid behåller sitt. Beskedet säger hur många poster som räknades om, och *Ångra* lägger tillbaka priset och posterna. En prisändring från en annan enhet (eller från organisationens admin) räknar om den här enhetens olåsta tid vid synken.
- **Centralt pris** under *Inställningar → Roller och timpriser* frågar från när det nya priset gäller.
- **Signering behövs inte för den som är ensam.** Inställningen *Avcheckning och signering* (ny i Inställningar) är av som standard när boken har en person: knapparna *Signera som administratör* syns inte och avcheckning räcker – som förut för att hantera och fakturera. Med flera personer är den på. Redan signerade veckor syns som förut.
- **En signerad vecka kan låsas upp.** Administratören kan låsa upp en signerad vecka (veckans status → *Lås upp veckan …*, eller `öppna v43` i smartshell) efter en bekräftelse – veckan blir öppen och tiden kan rättas. Hanterad och fakturerad tid förblir låst. Texterna säger inte längre att en signerad vecka är slutgiltig.
- README (*Timpriser*, *Avcheckning och signering*, *Filformat*) uppdaterad. Arbetet med flera personer (välja vems tidbok, signera åt andra med mera) kommer i 0.17.1.
- Test: `test/priser_test.py` (ny, körs i GitHub) och `test/bocker/format-11.json`.

## 0.16.1

Filformat 10, oförändrat. **Organisationer på servern** – etapp 4, andra steget: flera personer i samma bok. Är du ensam och vill fortsätta så märks ingen skillnad. Servern (`api.php`) är ny och måste ligga ute samtidigt som appen (publiceringen gör det).

- **Gör boken till en organisation** under *Inställningar → Spara boken → Spara på webben → Organisation*, med en kod från den som driver servern. Du blir organisationens admin och boken flyttar från ditt konto till organisationen; dina andra enheter följer med vid nästa synk (ändringar som inte var synkade slås ihop).
- **Bjud in en medarbetare.** Personen läggs in i boken (namn, initialer, roll, anställningsform) och får en kod som gäller en gång i 30 dagar. Upp till 10 personer per organisation, admin inräknad. En kod kan tas bort eller bytas mot en ny.
- **Medarbetaren går med** med *Skapa konto* och koden – eller *Gå med i en organisation …* med ett befintligt konto – och får en personlig nyckel. Sparindikatorn säger *Väntar på att admin tar in dig i boken*.
- **Admin tar in personen** med *Ta in i boken …*, som visar nyckelns fingeravtryck att jämföra med personens enhet. Därefter krypteras registret, personens kort och tidlogg också till personen.
- **Varje del för sig på servern.** Registret, fakturorna, personkorten och tidloggarna sparas var för sig, och servern kontrollerar skribenten: registret, fakturorna och korten bara admin, en tidlogg bara personen själv (admin förvaltar den tills personen har börjat rapportera). En enhet hämtar bara de delar som är krypterade till personen och skickar bara de delar personen skriver och som har ändrats. Krock bara när samma del har ändrats på två ställen.
- **Medarbetaren** ser projekt, kunder och timpriser, sitt kort och sin egen tid – inte kollegornas tid, budgetens förbrukning eller fakturorna (fliken *Fakturor* syns inte). En ändring i något annat än den egna tiden tas bort vid nästa synk, med ett besked.
- **Registrets nyckel fästs på enheten** första gången organisationens bok hämtas; byts den stoppas synken. Admins enhetsnyckel gäller i registret (också när boken en gång importerats med en äldre nyckel).
- **Ta bort en medarbetare.** Personen når inte boken längre och delarna krypteras om utan henne eller honom; tiden ligger kvar.
- **Inloggning med flera böcker.** Har kontot både en egen bok och organisationer får du välja vilken som öppnas.
- **Radera kontot**: en medarbetare går ur organisationen, en admin tar bort organisationen (medarbetarna behåller sina konton).
- **Serverns ägare** skapar koder för ett konto eller en organisation och ser organisationerna (namn, admin, antal personer, utrymme) under *Administrera servern*.
- Servern sparar inga tidigare versioner av en organisations bok än.
- README (*Organisationer*, *Servern*, *Data och integritet*) och Data och integritet i appen beskriver det nya. Kvar till 0.16.2: välja vems tidbok admin ser, vem som inte har checkat av, signera och öppna åt andra, smartshell åt andra och *Medarbetare* på projektsidan.
- Test: `test/api_test.py` provar organisationerna på servern (koder, taket på 10, vem som får skriva vilken del, krock per del, att en medarbetare bara får sina delar, borttagning, radering); `test/org_test.py` (ny, körs i GitHub) provar en organisation i tre webbläsare – admin på två enheter och en medarbetare.

## 0.16.0

Filformat 10 – **grunden för flera personer** (etapp 4, första steget). Är du ensam i boken märks ingen skillnad. Böcker i format 9 och äldre uppgraderas när de öppnas. Ladda om på alla enheter: en enhet med 0.15.x kan inte öppna boken efteråt och säger att den kommer från en nyare version.

- **Organisationen.** Boken får ett organisations-id (`register.org`), räknat ur bokens skapad-datum så att samma bok får samma id på alla enheter.
- **Boken i delar.** När boken krypteras delas den i delar med en skribent var: registret (admin skriver, alla läser), fakturorna och det som rör budgetens förbrukning (bara admin), ett personkort per person med anställning, saldo, semester och signerade veckor (admin skriver, personen och admin läser) och en tidlogg per person (personen skriver, personen och admin läser). Så blir det möjligt att en medarbetares tid bara syns för personen själv och admin, och att varje fil har en enda skribent.
- **En personlig nyckel.** Varje person får ett nyckelpar för kryptering (ECDH P-256) och ett för signering (ECDSA P-256), första gången boken sparas krypterad – som kopia eller på webben. De offentliga nycklarna står i registret, de privata i en nyckelring som låses med boknyckeln och följer med varje krypterad fil. *Inställningar → Spara boken → Kryptering* visar nyckelns fingeravtryck.
- **Krypterad fil version 2.** Varje del krypteras med en egen nyckel som låses till varje läsare (som *age*) och signeras av skribenten; en ändrad del eller en del från fel skribent upptäcks när filen öppnas. Gäller både kopior som fil och boken på webben. Krypterade kopior från 0.12.0–0.15.1 (version 1) öppnas som förut. Servern behöver inte ändras.
- **Två enheter samtidigt.** Uppgraderar telefonen och datorn samtidigt och skapar var sin nyckel kommer de överens om den äldsta.
- Synken jämför böckernas innehåll i stället för fältens ordning.
- README (*Kryptering*, *Filformat*) och Data och integritet beskriver det nya. Planen för resten av etapp 4: servern med organisationer och inbjudningar (0.16.1) och arbetet med flera – välja vems tidbok, signera åt andra, smartshell åt andra (0.16.2).
- Test: `test/delar_test.py` (delning fram och tillbaka, att registret saknar fakturor, personkort och budgetens förbrukning, kryptering till rätt läsare – en medarbetare ser inte fakturorna eller någon annans tid –, ändrad del, nyckelkrock, nyckelringen mellan enheter, import av version 2; körs i GitHub), `test/bocker/format-10.json` och `test/bocker/krypterad-2.sisyfos`. `webb_test.py` kontrollerar att filen på servern är version 2 och att båda enheterna har samma nyckel.

## 0.15.1

Filformat 9, oförändrat – betalningarna, kundens land och fakturans momsläge är nya valfria fält. Fakturor utfärdade i 0.15.0 och deras kontrollsummor ändras inte. Ladda om på alla enheter: en enhet med 0.15.0 behåller de nya uppgifterna vid synken men visar dem inte.

- **Betalstatus.** *Rapporter → Fakturor* visar om en faktura är obetald, förfallen (med antal dagar), betald eller krediterad, och filtren *Alla*, *Obetalda* och *Förfallna*. *Betald …* noterar datumet då pengarna kom (inte i framtiden, inte före fakturadatumet), med Ångra; datumet går att ändra eller ta bort. En kreditfaktura för en redan betald faktura visas som *att betala tillbaka* tills den markeras som återbetald; annars är den kvittad mot originalet. Panelen visar obetalt, förfallet och att betala tillbaka. Arkivets CSV har kolumnerna *Moms*, *Status* och *Betald*, och JSON-filen betalningarna. Betalningarna sparas i `register.payments`, utanför de frysta fakturorna.
- **Kunder i andra EU-länder.** Kunden får fältet *Kunden finns i* (Sverige, ett annat EU-land, utanför EU). Ett EU-företag kräver momsregistreringsnummer med utländsk landskod. Fakturan får **omvänd betalningsskyldighet**: 0 % moms, texten *Omvänd betalningsskyldighet (reverse charge)* och båda momsnumren; utkastet påminner om periodisk sammanställning och om att tjänster som rör en fastighet i Sverige ändå har svensk moms.
- **Kunder utanför EU.** Fakturan får 0 % moms och texten att tjänsten är omsatt utanför Sverige.
- **Momsläget** väljs efter kunden och kan ändras i utkastet (*Svensk moms*, *Omvänd betalningsskyldighet*, *Ingen svensk moms*); det fryses på fakturan och följer med en kreditfaktura. Betal-QR kommer bara med på fakturor med svensk moms, och utfärdandet varnar när en utländsk kund inte kan betala till IBAN.
- **SIE-export.** *Exportera SIE …* ger en SIE 4I-fil (PC8) med fakturorna och – valfritt – betalningarna som verifikationer: kundfordringar mot försäljning och utgående moms per momssats, försäljning till EU och utanför EU på egna konton, öresavrundning, och bank mot kundfordringar för betalningarna. Kontona följer BAS och kan ändras, liksom verifikationsserien. Nästa export föreslås börja dagen efter den förra, och dialogen varnar när perioden överlappar.
- **Kreditering och överlappande perioder.** *Lås upp tiden* låser nu bara upp den tid som ingen annan okrediterad faktura omfattar.
- På telefon staplas raderna i fakturalistan, så att knapparna får plats.
- Momsregistreringsnummer för kunder får nu vara 4–15 tecken med landskod (t.ex. ATU12345678, DE123456789).
- README (*Fakturor*) och Data och integritet beskriver det nya.
- Test: `test/faktura2_test.py` (betalstatus, filter, Betald … med Ångra, EU-kund och kund utanför EU med PDF:ernas texter, SIE-filen – kodning, att varje verifikation går jämnt ut, konton, period – och att fakturorna från 0.15.0 är oförändrade; körs i GitHub).

## 0.15.0

Filformat 9 – **riktiga fakturor** som tillägg. Böcker i format 8 och äldre uppgraderas när de öppnas; inget annat ändras. En enhet med en äldre version av appen kan inte öppna boken efteråt (ladda om sidan så hämtas den nya).

- **Fakturor är av tills de slås på** – i guiden för ny bok (nytt steg *Fakturor* före *Klart*) eller under *Inställningar → Fakturor*. Villkoren måste godkännas först: en utfärdad faktura är räkenskapsinformation som ska sparas i sju år, kan inte ändras eller tas bort, numren löper i en obruten serie, och Sisyfos är fortfarande inget bokföringsprogram. Godkännandet sparas med datum och vem.
- **Uppgifter:** momsregistreringsnummer (föreslås ur org.nr), bankgiro, plusgiro, IBAN och BIC, Swish, betalningsvillkor, dröjsmålsränta, *Godkänd för F-skatt*, text före numret och första nummer, OCR, betal-QR, öresavrundning och en text längst ner. Kunden kan ha eget momsnummer och egna betalningsvillkor.
- **Skapa faktura** i fakturaunderlaget gör ett utkast av kundens eller projektets öppna tid. Utkastet går att ändra – kund (även hämtad från en annan kund), datum, villkor, referenser, rader och egna rader, momssats och meddelande – och förhandsgranska som PDF. *Tom faktura* för en faktura utan tid.
- **Utfärda** ger nästa nummer, fryser fakturan (säljarens och köparens uppgifter, rader, belopp, OCR och loggan kopieras in), låser tiden i underlaget och laddar ner PDF:en. Varnar om tiden har ändrats sedan utkastet skapades.
- **Kreditera** utfärdar en kreditfaktura med negativa belopp som hänvisar till originalet, och kan låsa upp tiden igen. Att häva hanterad tid som ingår i en faktura ger en varning.
- **Fakturans PDF** har det en fullständig faktura ska innehålla, betalningsruta med bankgiro/plusgiro/IBAN, OCR och betal-QR, och säljarens uppgifter i sidfoten. Samma faktura ger alltid samma PDF – utan utskriftsdatum, med en kontrollsumma (sha256). Momssatsen 0 % ger texten *Undantag från momsplikt*.
- **OCR** med kontrollsiffra eller med längd- och kontrollsiffra (Luhn, modulus 10), efter avtalet med banken, och en ruta som kontrollerar ett nummer.
- **Numren och synken:** med boken på webben synkas den före och efter utfärdandet. Två enheter som ändå ger samma nummer samtidigt rättas när böckerna slås ihop – den som utfärdades senare får nästa lediga nummer, likadant på båda.
- **Rapporter → Fakturor:** utkast och utfärdade fakturor, PDF igen, kreditera, och **arkiv** – en zip per år med alla PDF:er, en CSV och en JSON-fil. Panelen visar årets summor, nästa nummer och påminner om år vars arkiv inte är nedladdat.
- QR-koderna kan nu vara större (version 1–10), så att betalningsuppgifterna ryms.
- Data och integritet och README (*Fakturor*) beskriver tillägget.
- Test: exempelbok `test/bocker/format-9.json` (fakturorna ska vara oförändrade och kontrollsummorna stämma), `test/faktura_test.py` (påslag, utkast, utfärdande, PDF, kreditering, arkiv, varning, telefon, guiden – körs i GitHub), `webb_test.py` (en faktura på varje enhet ger nummer i följd).

## 0.14.0

Filformat 8 – en migrering för allt som väntat på ett nytt format. Böcker i format 7 och äldre uppgraderas när de öppnas; en enhet med en äldre version av appen kan inte öppna boken efteråt (ladda om sidan så hämtas den nya). Samma bok uppgraderad på två enheter slås ihop utan dubbletter.

- **Hantera valfri period.** Hanterad tid kan nu vara vilken period som helst – mitt i en månad, två månader eller 28 september – 3 oktober – i stället för bara hela månader. Från månadsmenyn (*Hantera en annan period …*), projektdagboken med *Egen period*, fakturaunderlaget och projektsidan, eller med smartshell: `hant 1/10-15/10 strand`, `hant v40-42 strand`, `häv 5/10-10/10 strand`. Det som redan är hanterat rörs inte, perioder kant i kant slås ihop och att häva en del delar perioden. Befintliga hanterade månader följer med oförändrade.
- **Fakturaunderlaget markerar hela underlaget som hanterat** – från den äldsta öppna tiden som ingår till periodens slut, per projekt. Förut bara månader som helt ingick.
- **Projektsidan: Hanterad tid** listar de senaste hanterade perioderna med timmar, belopp och *Häv*, och knappen *Hantera en period …*. Månadsöversikten och projektets månader visar en delvis hanterad månad med ett ljusare lås och perioden (t.ex. *1–15 okt*).
- **Dagsanteckning** – en kort text för hela dagen, t.ex. *studieresa Sthlm*. Skrivs i dagvyn, i panelen för en dag eller med `dag tor studieresa Sthlm` (`dag mån-fre …` för flera dagar, `dag bort tor` tar bort). Syns i veckans dagrubriker, i månadsvyns dagrutor och i personsammanställningen (skärm och PDF). Sparas som händelse i din tidlogg och låses med veckan.
- **Egna kommandon i smartshell.** `förk dbn = db ner` gör att `dbn okt strand` laddar ner dagboken; `förk bort dbn` tar bort det. Listas och ändras i dialogen *Smartshell och förkortningar* och i förteckningen. De tidigare inbyggda `db-rapp`, `db-rp` och `dbrapp` blir egna kommandon i befintliga böcker (och kan tas bort).
- **Inställningar per enhet.** Tema, panelens bredd, kompakt läge, utfällda rader, helgen och listornas filter sparas på varje enhet och synkas inte längre med boken – telefonen kan ha mörkt tema och datorn ljust. Första gången tas värdena från boken, så inget ändras vid uppgraderingen.
- **Enhets-id på händelser.** Varje ändring i tidloggen märks med ett slumpat id för enheten (`dev`) – grunden för synk per enhet när fler personer kommer.
- Data och integritet och README beskriver dagsanteckningar, enhets-id och inställningarna per enhet.
- Test: exempelbok `test/bocker/format-8.json`; `webb_test.py` kontrollerar att dagsanteckningar och hanterade perioder synkas men inte temat.

## 0.13.2

Småjusteringar efter test och snabbare med stora böcker. Filformatet är oförändrat (7) – det som sparas om löpande-tipset ligger i projektets befintliga fält `notices`.

- **Menyknappen ligger till höger på telefon**, efter knappen *Alfa · Skicka synpunkter*. Stängknappen i menyn som öppnas sitter på samma ställe.
- **Löpande räkning – påminn senare eller visa inte.** Tipset om att skicka en budget (panelen och projektsidan) har knapparna *Påminn senare* (om en vecka, en månad eller tre månader) och *Visa inte i projektet*, båda med Ångra. Medan tipset vilar visas bara en diskret rad med upparbetat belopp och *Visa tipset nu*/*Visa tipset igen*. När påminnelsen kommer visas den överst i tidboken med *Ange budget*, *Påminn senare* och *Visa inte igen*.
- **Snabbare med många års tid.** Summorna per projekt och per dag räknas nu i ett svep över boken och sparas tills något ändras, i stället för ett svep per projekt och dag. Med en testbok på tio år (11 500 tidposter, 250 projekt) gick Projekt-sidan från cirka 210 till 60 ms, Kunder från 150 till 40 ms och ett tangenttryck i en anteckning från 50 till 16 ms. Uppslag av projekt, kunder och roller på id går också snabbare. Allt som visas är oförändrat – kontrollerat genom att jämföra skärmarna i 0.13.1 och 0.13.2 med samma böcker.
- **Release-zip:** zippen innehåller nu också `api.php`. Ligger taggen på fel commit (GitHub föreslår main, som kan ha hunnit få en nyare version) säger körningen vilken commit som har versionen och hur releasen rättas. Kan köras för hand med en annan commit.
- **Arbetsflödena** använder versioner av GitHubs actions som kör på Node 24, och testerna körs på Ubuntu 24.04. Publiceringen visar om webbhotellet skickar `index.html` komprimerad.

## 0.13.1

- **Adminnyckeln får innehålla å, ä, ö och andra tecken.** Nyckeln skickas nu URL-kodad till servern. Förut gav å, ä och ö *Fel adminnyckel*, och tecken som € eller typografiska citattecken gav *Ingen kontakt med servern*. Mellanslag och radbrytningar före och efter nyckeln (t.ex. när den klistrats in i GitHub) räknas inte.

## 0.13.0

Spara på webben – krypterad synk för en person på flera enheter. Filformatet för boken är oförändrat (7), och den krypterade filen är samma omslag som i 0.12.0.

- **Spara på webben** under *Inställningar → Spara boken*: skapa konto med inbjudningskod, e-postadress och lösenord, eller logga in på en ny enhet. Boken krypteras på enheten innan den skickas – servern ser e-postadressen och en krypterad fil, aldrig innehållet eller lösenordet.
- **Synk** några sekunder efter varje ändring, vid start, när fönstret får fokus och när nätet kommer tillbaka. Fungerar utan nät; ändringarna skickas sedan. Sparindikatorn uppe till höger visar *Synkad 10:42*, *Synkar …*, *Offline – synkas när nätet finns* eller *Inloggningen har gått ut*.
- **Ändringar på två enheter slås ihop.** Tidposter, projekt, kunder och anteckningar från båda kommer med. Har samma sak ändrats olika behålls den här enhetens version, och en dialog låter dig välja den andra enhetens. En ögonblicksbild tas före sammanslagningen.
- **Inloggning på en enhet som redan har en bok:** välj att öppna boken från webben (en ögonblicksbild tas först) eller slå ihop dem.
- **Tidigare versioner:** servern sparar de tio senaste; en äldre version kan öppnas igen.
- **Byt lösenord** byter också inloggningen på webben, med möjlighet att logga ut dina andra enheter. Ny återställningsnyckel och nytt lösenord följer med till de andra enheterna vid nästa synk.
- **Logga ut** (boken ligger kvar – eller tas bort med ögonblicksbilder och nycklar) och **radera kontot** med allt på servern.
- **Administrera servern** (med adminnyckeln, sparas inte): skapa och ta bort inbjudningskoder, se och ta bort konton. Länk i avsnittet och `webb admin` i smartshell.
- **Smartshell:** `synk` synkar nu, `? synk` visar läget, `webb` öppnar inställningarna.
- **Servern** `api.php` (publicerad redan före versionen): PHP 8 utan databas, data utanför webbroten, inbjudningskoder, versioner med krockkontroll, kvot 20 MB per konto, broms för felaktiga inloggningar. Se README, *Spara på webben* och *Egen server*.
- **Data och integritet** och README beskriver vad servern sparar och ser, med ett ärligt förbehåll om att appen hämtas från samma server.
- Påminnelsen om att spara kopia som fil visas inte när boken synkas med webben.
- Test: `test/webb_test.py` kör två webbläsare mot `api.php` på en lokal PHP-server – konto, inloggning, sammanslagning, krock, lösenordsbyte, admin, utloggning och radering.

## 0.12.1

Rättningar efter test. Filformatet är oförändrat (7).

- **Återställningsnyckeln ryms på telefon.** På smala skärmar ligger QR-koden överst, nyckeln centrerad under och knapparna i full bredd – inget sticker ut ur rutan längre.
- **Filväljaren i Importera bok följer temat.** Webbläsarens egen knapp är ersatt av en knapp i appens stil (*Välj fil …*) med filnamnet bredvid, rätt placerad i fältet och läsbar även i mörkt tema.

## 0.12.0

Krypterad kopia – första steget mot lagring på webben. Filformatet för boken är oförändrat (7); den krypterade filen är ett eget, versionerat omslag (`sisyfos-krypterad`, version 1).

- **Kryptering** under *Inställningar → Spara boken*: välj ett lösenord, få en **återställningsnyckel** (visas en gång, PDF med QR-kod att skriva ut) och bekräfta med de fyra sista tecknen.
- **Spara krypterad kopia** (`.sisyfos`) i avsnittet, i Sisyfos-menyn och med `kopia krypt` i smartshell. AES-256-GCM, lösenordet sträcks med PBKDF2-SHA-256 (600 000 varv), innehållet packas med gzip.
- **Importera bok** öppnar krypterade kopior med lösenordet eller återställningsnyckeln. Med återställningsnyckeln får du välja ett nytt lösenord direkt. Krypteringen följer med till den nya enheten.
- **Byt lösenord** (med det gamla eller med återställningsnyckeln), **ny återställningsnyckel** och **stäng av** – utan att boken krypteras om.
- **Data och integritet** och README beskriver krypteringen.

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
