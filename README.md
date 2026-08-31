# Job Search Aggregator

A personal tool that checks a list of company career pages, pulls new job
postings, scores them against your target-role profile (Senior Associate /
Investor Relations / ESG / product marketing, Boston-based), and writes a
single HTML page you can open and scan — sorted by relevance, newest and
most relevant first.

It only talks to public, no-login-required JSON APIs that companies expose
for their own career pages (Greenhouse, Lever, Ashby, Workday). It does not
scrape LinkedIn or Indeed.

## Quick start

You need Python 3.10+ installed. Then, from this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

That's a one-time setup. After that, whenever you want a fresh check:

```bash
python refresh.py
```

This fetches every company listed in `config.yaml`, scores the postings,
saves everything to a local history file (`output/jobs.db`), and writes
`output/jobs.html`. Open that file in your browser (double-click it, or
`open output/jobs.html` on a Mac) to see the results — newest, most
relevant postings at the top, with a green **NEW** badge on anything you
haven't seen in a previous run.

Run `python refresh.py` any time you want an updated check — there's no
schedule, it only runs when you tell it to.

## Editing the config (no coding required)

Everything you'd want to tune lives in `config.yaml`. It's a plain text
file — open it in any text editor.

**To add a company:**
```yaml
  - name: Some Firm
    platform: greenhouse        # or lever, ashby, workday, rss
    board_id: somefirm          # see "finding a company's board ID" below
```

**To remove a company:** delete its block (or comment it out by putting a
`#` at the start of each of its lines).

**To adjust keywords or their weight:** edit the `scoring.priority_keywords`
list — `weight_title` is how many points a keyword is worth when it appears
in the job title, `weight_description` is how many points when it only
shows up in the description text.

**To change the location rule:** edit `location.target_location_terms` and
`location.remote_terms`. Setting `exclude_if_no_location_match: false` will
stop dropping non-Boston/non-remote postings and just score them low
instead, if you'd rather see everything.

**To change what counts as "too junior":** edit `seniority.exclude_terms`
(titles containing any of these are dropped entirely) and
`seniority.include_terms` (titles containing any of these get a bonus).

After editing, just run `python refresh.py` again — no restart, no
reinstall needed.

### Finding a company's board ID

Visit the company's careers page and look at the URL once it takes you to
the actual job listing (not just the marketing page):

| Platform | URL looks like | The ID you need |
|---|---|---|
| Greenhouse | `job-boards.greenhouse.io/acme` | `acme` |
| Lever | `jobs.lever.co/acme` | `acme` |
| Ashby | `jobs.ashbyhq.com/acme` | `acme` |
| Workday | `acme.wd5.myworkdayjobs.com/AcmeCareers` | tenant=`acme`, wd_host=`wd5`, site=`AcmeCareers` |
| RSS | any feed URL the company publishes | the feed URL itself, as `feed_url:` |

If you're not sure what platform a company uses, tell me the company name
and I can look it up for you.

## What's currently tracked

Companies with a confirmed, working board (Greenhouse or Workday):
TA Associates* is not on this list — see below — but Audax Group, Summit
Partners, General Catalyst, HarbourVest Partners, Bain Capital, Advent
International, Cambridge Associates, Wellington Management, and Fidelity
Investments are all wired up.

Not yet wired up (no public Greenhouse/Lever/Ashby/Workday board turned up
in research — likely they only post firm-level roles on LinkedIn or via a
plain "email us" page): TA Associates, Berkshire Partners, Thomas H. Lee
Partners, Charlesbank Capital Partners, Riverside Partners. These are left
as commented-out placeholders in `config.yaml`. If you find the actual
careers URL for any of them, send it along and it can likely be added.

## How scoring works

Every posting starts at 0 points. Points are added for:
- Priority keywords (investor relations, LP relations, ESG, etc.) found in
  the title (worth more) or description (worth less)
- Being located in Boston/MA, or being remote/hybrid
- The title containing a seniority term like "Associate", "Director", etc.

Postings are **hard-excluded** (never shown, though still recorded in the
history database) if:
- The title contains a junior-level term (Intern, Coordinator, etc.)
- The title contains an excluded term (Compliance, Legal Counsel, Paralegal)
- The location doesn't match Boston/MA and isn't remote/hybrid

Everything else is sorted by score (highest first), then by post date
(newest first).

## Output files

- `output/jobs.html` — the report you actually look at
- `output/jobs.csv` — same data as CSV, if you set `write_csv: true` in
  `config.yaml` (useful for opening in Excel)
- `output/jobs.db` — a SQLite database holding every posting ever seen,
  including excluded ones, so you have a running history. You generally
  don't need to open this yourself, but it's a normal SQLite file if you
  ever want to poke around in it with a SQLite browser tool.

## Adding more sources later

- **RSS feeds**: already supported — add `platform: rss` with a `feed_url:`
  field for any company that publishes one.
- **A paid job-aggregator API** (e.g. a Google Jobs API service): not built
  yet, and not needed to start. If you want it later, it would slot in as
  a new file under `sources/` the same way Greenhouse/Lever/etc. work, and
  you'd need to get an API key from that provider first.

## Troubleshooting

- **A company shows `[error]` when you run refresh.py**: most often the
  company changed their board ID or switched ATS platforms. Re-check the
  company's careers page URL and update `config.yaml`.
- **A company shows `[skip]`**: its `platform:` value in `config.yaml`
  isn't one of `greenhouse`, `lever`, `ashby`, `workday`, `rss` (or it's a
  commented-out placeholder — see "What's currently tracked" above).
- **Nothing shows up for a company you know is hiring**: check whether the
  posting is being hard-excluded by the location or seniority filters (it's
  still saved in `output/jobs.db`, just not in the HTML report) — try
  loosening the filter it's being caught by in `config.yaml`.
