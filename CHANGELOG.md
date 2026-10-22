# Ändringar i Sisyfos

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
