# RegBase

A regulatory corpus and scoping toolchain for oil & gas midstream projects —
midstream pipelines, produced water lines, saltwater disposal wells, compressor
stations, and gas processing plants — across **Colorado, Wyoming, New Mexico,
Utah, and Texas**.

It answers one question fast: *given a KMZ and a scope, what does it actually
take to permit this?* — and produces the Form 1.9 Pre-Project Regulatory Review
that a project manager can work from.

## Layout

```
regbase/
  sources/         the registry — one YAML per state + federal, plus notes.md
                   files recording what could not be verified
  schemas/         source.schema.json, person.schema.json, review.schema.json
  corpus/          harvested material
    raw/           downloaded bytes (gitignored)
    text/          extracted text, committed — this is what gets diffed
    manifest.jsonl every fetch with sha256, ETag, status
    regbase.sqlite the search index
    reports/       update-check and agenda-watch output
  people/          public-official and staff profiles + the ethics policy
  tools/           the toolchain (below)
  web/             registry.json + the browser KML review tool
  docs/            operating notes
```

## The registry

`sources/*.yaml` is the spine. Each record is a jurisdiction or agency with its
documents, permits, GIS endpoints, contacts, and a **confidence** value —
`verified`, `probable`, or `unverified`. Nothing in this system asserts a
requirement without carrying that flag along with it.

```bash
python3 regbase/tools/build_registry_json.py --indent 1   # rebuild web/registry.json
python3 -c "import sys; sys.path.insert(0,'regbase/tools'); import common; \
            print('\n'.join(common.validate_sources()) or 'registry valid')"
```

## Toolchain

| tool | what it does |
| --- | --- |
| `harvest.py` | downloads every registry document; `--crawl` walks a whole municipal code |
| `extract.py` | HTML/PDF/DOCX → citable text with heading paths |
| `build_index.py` | builds `corpus/regbase.sqlite` (FTS5 over chunks + permits + people) |
| `query.py` | `search` / `permits` / `jurisdiction` / `stack` / `gaps` / `people` |
| `kmlgeo.py` | KML/KMZ → centroid, bbox, centerline length, acreage, lookup samples |
| `review.py` | KMZ + scope → Form 1.9 draft as `.review.json`, `.md`, and `.doc` |
| `check_updates.py` | conditional-GET change detection with text diffs |
| `watch_agendas.py` | scans meeting agendas for pending regulatory changes |
| `refresh_people.py` | builds the officials-profile refresh work queue |
| `build_registry_json.py` | flattens the YAML registry for the web tool |

## Getting started

```bash
pip install -r regbase/tools/requirements.txt

# 1. see what would be downloaded, without touching the network
python3 regbase/tools/harvest.py --dry-run --state CO

# 2. harvest (needs outbound HTTPS — see below)
python3 regbase/tools/harvest.py --state CO --delay 1.5

# 3. index and query
python3 regbase/tools/build_index.py --rebuild
python3 regbase/tools/query.py stack --state CO --county Weld --asset compressor_station

# 4. scope a project
python3 regbase/tools/review.py project.kmz --project-name "Silo Station" \
    --asset midstream_pipeline --asset compressor_station --state CO --county Arapahoe
```

## Network

The harvester, update checker, agenda watcher, and the Census jurisdiction
lookup in `review.py` all need ordinary outbound HTTPS. Every one of them checks
first and exits with instructions rather than emitting a wall of failures.

In a Claude Code web environment, outbound access is set by the environment's
network policy — see
<https://code.claude.com/docs/en/claude-code-on-the-web>. Otherwise run the
tools on a machine with normal internet access.

## Asking it questions

Two skills drive this from Claude Code:

- **`regbase`** — the chat interface. "What permits do I need for a compressor
  station in Weld County?" It queries the index and cites jurisdiction, section,
  and URL.
- **`pre-project-review`** — the Form 1.9 workflow, end to end.

## Honesty rules

These are load-bearing, not decoration:

1. A requirement is never asserted without a citation and a confidence value.
2. A cost or timeline the registry does not have renders as a **blank**, never
   as an estimate.
3. Coverage gaps are reported, not hidden — `query.py gaps` exists for this.
4. Every generated review carries a provenance block listing unresolved
   questions and what a human must verify.

Every output is a draft. Confirm with the jurisdiction before it drives a
schedule or a budget.
