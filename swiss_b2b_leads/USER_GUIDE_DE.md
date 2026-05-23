# Swiss B2B Lead Search - Benutzerhandbuch

### Was Das Tool Macht

Swiss B2B Lead Search sammelt Schweizer Firmen-Leads aus mehreren Quellen, vergleicht die Qualitaet der Quellen, reichert Firmendaten nach Moeglichkeit an, speichert die Suchhistorie und exportiert Ergebnisse als Excel-Datei.

Das Tool ist dafuer gedacht, zu testen, welche Quellen und Suchparameter fuer eine bestimmte Branche und Region die besten B2B-Leads liefern.

### Uebersicht Der Menuefunktionen

#### Kopfbereich

- **Swiss B2B Lead Search**: Hauptseite fuer die Suche.
- **History**: oeffnet die Suchhistorie. Dort koennen fruehere Suchen angesehen, fortgesetzt, geloescht, zusammengefuehrt oder exportiert werden.

#### API Keys

In diesem Bereich werden externe API-Integrationen gesteuert.

- **Google Places**: Suche nach Firmen/Orten ueber Google Places.
- **SerpAPI**: Google-Suche aehnliche Web-Ergebnisse.
- **Tavily**: alternative Websuche, falls SerpAPI nicht verwendet wird.
- **Firecrawl**: optionale tiefere Website-Anreicherung.
- **Augen-Button**: zeigt oder versteckt einen API-Key beim Bearbeiten.
- **Save & Apply Keys**: speichert die Keys und wendet sie ohne Neustart der App an.

Kleine Statuspunkte zeigen, ob eine Quelle verfuegbar ist, fehlt oder kuerzlich ein API-Problem hatte, zum Beispiel Quota- oder Rate-Limit-Probleme.

#### Search Parameters

Hier wird die eigentliche Suche konfiguriert.

##### Locations

Die Standortsuche akzeptiert:

- Staedte, zum Beispiel `Zurich`, `Basel`, `Lugano`;
- Kantone, zum Beispiel `ZH`, `Canton Zurich`, `Ticino`;
- Regionen, zum Beispiel `Romandie`, `Central Switzerland`, `Ticino`;
- eigene Gebiete, die manuell eingegeben werden.

Ausgewaehlte Standorte erscheinen als Chips unter dem Suchfeld. Mit `x` kann ein Chip entfernt werden.

Coverage-Modi:

- **Top cities**: empfohlener Standard. Ein Kanton oder eine Region wird in die wichtigsten Staedte aufgeteilt. Das gibt gute Abdeckung, ohne zu viele API-Anfragen zu erzeugen.
- **Area query**: sucht direkt mit dem Namen des Gebiets, ohne es in Staedte aufzuteilen.
- **All cities**: erweitert den Kanton oder die Region auf alle aktuell in der internen Standortliste vorhandenen Staedte. Das ist breiter, kann aber teurer sein.

Wichtig: Wenn eine Region ausgewaehlt wird, bedeutet das nicht automatisch, dass jede Gemeinde oder jeder Bezirk der Schweiz durchsucht wird. Die Region wird in die verfuegbaren Staedte/Standorte dieser Region aufgeteilt.

##### Industries

Hier werden eine oder mehrere Zielbranchen ausgewaehlt.

Buttons:

- **All**: waehlt alle Branchen aus.
- **None**: entfernt alle ausgewaehlten Branchen.
- **Custom search term**: erlaubt einen eigenen Suchbegriff.
- **+**: fuegt den eigenen Begriff hinzu.

Beispiele:

- `Banks`
- `Insurance companies`
- `Shopping centers`
- `Property management companies`
- `Garages / Car dealerships`

##### Target Qualifying Leads

Legt fest, wie viele finale qualifizierte Leads das Tool finden soll.

Beispiel: Wenn das Ziel `30` ist, sucht das System bis zu 30 passende Leads oder bis die maximale Rundenzahl erreicht ist.

##### Quality Requirements

Optionale Filter fuer die finale Lead-Liste:

- **Phone number required**: nur Leads mit Telefonnummer.
- **Email address required**: nur Leads mit E-Mail-Adresse.
- **Website required**: nur Leads mit Website.
- **Clear**: entfernt alle Qualitaetsanforderungen.

Strengere Anforderungen reduzieren normalerweise die Anzahl der finalen Leads.

##### Max Fetch Rounds

Legt fest, wie viele Sammelrunden das System maximal ausfuehren darf.

Wenn das Ziel in der ersten Runde nicht erreicht wird, wird in der naechsten Runde die Abrufmenge erhoeht. Mehr Runden koennen bessere Ergebnisse liefern, dauern aber laenger und koennen mehr API-Credits verbrauchen.

##### Website Enrichment Workers

Legt fest, wie viele Websites parallel verarbeitet werden.

- Niedriger Wert: langsamer, stabiler.
- Hoeherer Wert: schneller, aber Websites koennen Anfragen eher blockieren.

Empfohlener Bereich: `5-10`.

#### Sources

Hier wird ausgewaehlt, welche Quellen verwendet werden.

- **search.ch**: Schweizer Verzeichnisquelle. Gut fuer Schweizer Firmeneintraege und Telefonnummern.
- **Google Places**: Google-Firmen- und Standortdaten. Benoetigt einen Google API-Key.
- **Google Search**: Websuche ueber SerpAPI oder Tavily. Nuetzlich fuer Websites und Kontaktseiten.
- **Website Parser**: besucht gefundene Firmen-Websites und versucht E-Mail, Telefon und Kontaktseiten zu extrahieren.
- **Firecrawl**: optionale erweiterte Website-Anreicherung. Benoetigt einen Firecrawl API-Key.

Wenn ein Key fehlt oder ein Anbieter ein Limit erreicht, kann diese Quelle uebersprungen werden, waehrend die restliche Suche weiterlaeuft.

#### Run Search

Startet die konfigurierte Suche.

Vor dem Start berechnet das System eine Schaetzung:

- Anzahl der erweiterten Standorte;
- geschaetzte Source Queries;
- geschaetzte externe API-Aufrufe;
- Kosten-Warnstufe.

Bei grossen Suchen kann die UI eine Bestaetigung verlangen, bevor die Suche gestartet wird.

#### Pause / Resume

Waehrend einer Suche:

- **Pause** fordert eine Pause des laufenden Jobs an.
- **Resume** setzt den pausierten Job fort.

Wenn der Server neu gestartet wird, koennen unterbrochene Suchen auch ueber die History-Seite fortgesetzt werden.

### Ergebnisbereich

#### Progress

Zeigt Live-Logs der Suche:

- aktuelle Runde;
- aktive Quelle;
- aktueller Standort / aktuelle Kategorie;
- gesammelte Datensaetze;
- Fortschritt der Website-Anreicherung;
- API-Warnungen oder uebersprungene Quellen.

API-Limit-Meldungen koennen hier erscheinen, wenn ein Anbieter Quota-, Rate-Limit-, Billing- oder Invalid-Key-Fehler meldet.

#### Metrics

Zeigt Zusammenfassungen waehrend oder nach der Suche:

- **Raw records**: gesammelte Rohdaten vor finaler Bereinigung.
- **Unique leads**: deduplizierte Leads.
- **Qualified**: Leads, die den Qualitaetsanforderungen entsprechen.
- **With phone**: Leads mit Telefonnummer.
- **With email**: Leads mit E-Mail-Adresse.

#### Source Comparison

Vergleicht die Qualitaet pro Quelle:

- gesammelte Leads;
- Telefonquote;
- E-Mail-Quote;
- durchschnittlicher Qualitaetsscore.

So kann entschieden werden, welche Quelle fuer eine bestimmte Branche oder Region am besten funktioniert.

#### Leads

Zeigt die finale Lead-Tabelle.

Das Filterfeld kann nach Firma, Stadt, E-Mail, Telefon und anderen sichtbaren Feldern suchen.

Typische Lead-Felder:

- Firmenname;
- Branche;
- Stadt/Kanton;
- Telefon;
- E-Mail;
- Website;
- Quelle;
- Qualitaetsscore.

#### Export

Exportiert die aktuellen Ergebnisse als Excel-Dateien:

- **File 1: Target Leads Excel**: exportiert die aktuell angezeigte Target-Liste, zum Beispiel die ersten 30 Leads, wenn das Ziel 30 ist.
- **File 2: All Qualified Excel**: exportiert alle deduplizierten Leads, die die gewaehlten Qualitaetsanforderungen erfuellen, ohne die Liste beim Target Count abzuschneiden.

Der Hinweis im Metrics-Bereich erklaert, wie viele Source Records gesammelt wurden, wie viele Unique Leads nach der Deduplizierung bleiben und wie viele Qualified Leads fuer File 2 verfuegbar sind.

### History-Seite

Die History-Seite wird ueber den **History** Link im Kopfbereich geoeffnet.

Funktionen:

- **Back to Search**: zurueck zur Hauptsuche.
- **Select all**: waehlt alle History-Eintraege aus.
- **Merge & Export Selected**: fuehrt ausgewaehlte Suchen zusammen und exportiert sie in eine Datei.
- **Delete Selected**: loescht ausgewaehlte History-Eintraege.
- **Export**: exportiert eine einzelne Suche.
- **Resume**: setzt eine unterbrochene oder pausierte Suche fort.
- **Watch Live**: verbindet sich wieder mit einer aktuell laufenden Suche.
- **Delete icon**: loescht einen einzelnen History-Eintrag.

Jede History-Karte zeigt:

- Standorte und erweiterte Suchbegriffe;
- Branchen;
- Zielanzahl;
- geschaetzte Queries;
- Status;
- Rohdaten / qualifizierte Leads / finale Leads;
- Kosten-Warnstufe;
- API-Warnungen;
- Quellenvergleich.

### Empfohlener Arbeitsablauf

1. Die App-URL oeffnen.
2. API-Keys im Bereich API Keys eintragen oder pruefen.
3. Zuerst einen Standort auswaehlen, zum Beispiel eine Stadt oder einen Kanton.
4. Eine oder zwei Branchen auswaehlen.
5. Den Coverage Mode fuer den ersten Test auf **Top cities** lassen.
6. Ein realistisches Ziel setzen, zum Beispiel `30-100`.
7. Fuer breite Tests keine Qualitaetsanforderungen setzen, oder Telefon/Website fuer strengere Ergebnisse verlangen.
8. Quellen auswaehlen.
9. Die Kostenschaetzung pruefen.
10. **Run Search** klicken.
11. Den **Progress** Log beobachten.
12. Unter **Source Comparison** pruefen, welche Quelle am besten funktioniert.
13. Die **Leads** Tabelle kontrollieren.
14. File 1 fuer die Target-Liste oder File 2 fuer alle qualifizierten Leads exportieren.
15. Ueber **History** Suchen spaeter fortsetzen, exportieren, zusammenfuehren oder loeschen.

### Hinweise Zu API-Limits

Das System erkennt haeufige API-Probleme:

- fehlender Key;
- ungueltiger Key;
- Quota exceeded;
- Rate limit;
- Billing-/Credit-Probleme.

Wenn ein Anbieter fehlschlaegt, soll die Suche mit den restlichen aktivierten Quellen weiterlaufen. Der betroffene Anbieter wird in der UI markiert und in der History als API-Warnung gespeichert.

Fuer produktive Nutzung sollten aktive bezahlte API-Keys mit ausreichendem Kontingent verwendet werden.

---

