# Swiss B2B Lead Search - User Guide

### What The Tool Does

Swiss B2B Lead Search collects Swiss company leads from several sources, compares source quality, enriches company records where possible, saves search history, and exports results to Excel.

The tool is designed for testing which sources and search parameters produce the best B2B lead data for a selected industry and location.

### Main Menu Overview

#### Header

- **Swiss B2B Lead Search**: main search screen.
- **History**: opens the search history page, where previous searches can be reviewed, resumed, deleted, merged, or exported.

#### API Keys

This section controls external API integrations.

- **Google Places**: used for company/place search through Google Places.
- **SerpAPI**: used for Google Search style web results.
- **Tavily**: alternative web search provider if SerpAPI is not used.
- **Firecrawl**: optional deeper website enrichment.
- **Eye button**: shows or hides a key while editing.
- **Save & Apply Keys**: saves the entered keys and applies them without restarting the app.

Small status dots show whether a source is available, missing, or has a recent API issue such as quota/rate limit problems.

#### Search Parameters

This is where the actual search is configured.

##### Locations

The location search bar accepts:

- cities, for example `Zurich`, `Basel`, `Lugano`;
- cantons, for example `ZH`, `Canton Zurich`, `Ticino`;
- regions, for example `Romandie`, `Central Switzerland`, `Ticino`;
- custom areas, typed manually.

Selected locations appear as chips below the search field. Click the `x` on a chip to remove it.

Coverage modes:

- **Top cities**: recommended default. A canton or region is expanded into its main cities. This gives good coverage without creating too many API calls.
- **Area query**: searches using the area name directly, without expanding it into cities.
- **All cities**: expands the canton or region into all cities currently available in the internal location list. This is broader and can be more expensive.

Important: selecting a region does not mean every municipality or district in Switzerland is searched automatically. The region is expanded into the available city/location list for that region.

##### Industries

Choose one or more target industries from the list.

Buttons:

- **All**: selects all industries.
- **None**: clears all selected industries.
- **Custom search term**: allows adding a manual industry/search phrase.
- **+**: adds the custom term.

Examples:

- `Banks`
- `Insurance companies`
- `Shopping centers`
- `Property management companies`
- `Garages / Car dealerships`

##### Target Qualifying Leads

Controls how many final qualified leads the tool should try to return.

Example: if the target is `30`, the system searches until it finds up to 30 matching leads, or until the maximum number of rounds is reached.

##### Quality Requirements

Optional filters for the final lead list:

- **Phone number required**: only keep leads with a phone number.
- **Email address required**: only keep leads with an email.
- **Website required**: only keep leads with a website.
- **Clear**: removes all quality requirements.

Stricter requirements usually reduce the number of final leads.

##### Max Fetch Rounds

Controls how many collection rounds the system may run.

If the target is not reached in the first round, the next round increases the fetch size. More rounds can improve results, but also take longer and may use more API credits.

##### Website Enrichment Workers

Controls how many websites are processed in parallel.

- Lower value: slower, more stable.
- Higher value: faster, but websites may block requests more often.

Recommended general range: `5-10`.

#### Sources

Choose which sources should be used.

- **search.ch**: Swiss directory source. Good for Swiss company listings and phone data.
- **Google Places**: Google business/place data. Requires a Google API key.
- **Google Search**: web search through SerpAPI or Tavily. Useful for finding websites and contact pages.
- **Website Parser**: visits company websites found by the sources and tries to extract email, phone, and contact page information.
- **Firecrawl**: optional advanced website enrichment. Requires a Firecrawl API key.

If a key is missing or a provider hits a limit, that source may be skipped while the rest of the search continues.

#### Run Search

Starts the configured search.

Before the search starts, the system calculates an estimate:

- expanded location count;
- estimated source queries;
- estimated external API calls;
- cost warning level.

If a search is large, the UI may require confirmation before running it.

#### Pause / Resume

During a search:

- **Pause** requests the running job to pause.
- **Resume** continues the paused job.

If the server is restarted, interrupted searches can also be resumed from the History page.

### Results Area

#### Progress

Shows live search logs:

- current round;
- active source;
- current location/category;
- collected records;
- enrichment progress;
- API warnings or skipped sources.

API limit notifications may appear here if a provider returns quota, rate limit, billing, or invalid key errors.

#### Metrics

Shows summary numbers after or during a search:

- **Raw records**: total collected before final cleanup.
- **Unique leads**: deduplicated leads.
- **Qualified**: leads matching selected quality requirements.
- **With phone**: leads containing phone numbers.
- **With email**: leads containing emails.

#### Source Comparison

Compares data quality by source:

- leads collected;
- phone rate;
- email rate;
- average quality score.

This helps decide which source is best for a specific industry or region.

#### Leads

Shows the final lead table.

The filter field can search by company, city, email, phone, and other visible fields.

Typical lead fields include:

- company name;
- industry;
- city/canton;
- phone;
- email;
- website;
- source;
- quality score.

#### Export

Exports the current result set as Excel files:

- **File 1: Target Leads Excel**: exports the currently shown target list, for example the first 30 leads if the target is 30.
- **File 2: All Qualified Excel**: exports all deduplicated leads that passed the selected quality requirements, without cutting the list at the target count.

The metrics note explains how many source records were collected, how many unique leads remain after deduplication, and how many qualified leads are available for File 2.

### History Page

Open it from the **History** link in the header.

Functions:

- **Back to Search**: returns to the main search page.
- **Select all**: selects all history entries.
- **Merge & Export Selected**: combines selected searches and exports them into one file.
- **Delete Selected**: deletes selected history entries.
- **Export**: exports one search.
- **Resume**: continues an interrupted or paused search.
- **Watch Live**: reconnects to a currently running search.
- **Delete icon**: deletes one history entry.

Each history card shows:

- locations and expanded terms;
- industries;
- target count;
- estimated queries;
- status;
- raw/qualified/final lead count;
- cost warning level;
- API warnings;
- source breakdown.

### Recommended Workflow

1. Open the application URL.
2. Add or verify API keys in the API Keys section.
3. Select one location first, for example one city or canton.
4. Choose one or two industries.
5. Keep coverage mode as **Top cities** for the first test.
6. Set a realistic target, for example `30-100`.
7. Keep quality requirements empty for broad testing, or require phone/website for stricter results.
8. Select sources.
9. Review the cost estimate.
10. Click **Run Search**.
11. Watch the **Progress** log for source activity and warnings.
12. Review **Source Comparison** to see which provider performs best.
13. Check the **Leads** table.
14. Export File 1 for the target list, or File 2 for all qualified leads.
15. Use **History** to resume, export, merge, or delete searches later.

### Notes About API Limits

The system detects common API problems such as:

- missing key;
- invalid key;
- quota exceeded;
- rate limit;
- billing/credit problems.

If one provider fails, the search should continue with the remaining enabled sources. The affected provider is marked in the UI and saved in history as an API warning.

For production usage, use active paid API keys with enough quota for the planned search volume.

---

