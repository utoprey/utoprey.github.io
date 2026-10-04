# Updating the public profile

## Automatic discovery

`sync-profile.mjs` is the server-side JavaScript collector. It runs in a bounded
Docker job in GitHub Actions every day at **03:37 UTC / 12:37 Seoul**, on a push
to `main`, or through **Actions → Update profile and deploy → Run workflow**.
The same workflow renders EN/RU HTML, checks it, commits the snapshot, and deploys
the public assets. GitHub Pages must use **GitHub Actions** as its publishing
source; a bot commit alone does not trigger a legacy Pages build.

```sh
npm ci --ignore-scripts
npm run sync:preview           # inspect sources without changing files
npm run sync                   # update _data/auto-profile.json
python _tools/build_profile.py
python _tools/check_site.py
```

- `_data/profile.json` is the curated profile. The collector never writes it,
  overwrites the biography/CV, changes chosen images, or publishes private repos.
- `_data/auto-profile.json` stores source health, the initial GitHub baseline,
  discovered projects and Scholar records. Both sources establish an initial
  baseline: old unlisted papers are not unexpectedly republished on setup.
  It contains public metadata only.
  A daily source-health snapshot is committed even when no new work is found.
- `_data/sync-config.json` controls source identities and exclusions. GitHub's
  first successful run records the existing repositories as a baseline; only
  subsequently discovered public original repositories are added. Forks, empty,
  disabled and archived repositories are omitted. To import a specific old repo,
  add its name to `github.include_existing_repositories`. Add a repo to
  `exclude_repositories`, or set its GitHub topic to `website-hide`, to hide it.
  Scholar uses stable citation IDs for the same baseline policy. To deliberately
  backfill an existing record, add its ID to `scholar.include_existing_citation_ids`.
- Existing curated projects and publications are deduplicated. All curated paper
  titles, including `show_on_site: false`, prevent reimport; the four deliberately
  hidden papers stay hidden. Posters do not become publication entries.
- New GitHub projects appear below the curated projects. Scholar discoveries
  appear as compact bibliographic records below the illustrated papers, in the
  source's language. The script does not guess peer-review status, translate
  scientific titles, or invent paper figures. Promote a record into the curated
  profile when selecting its original illustration; the duplicate disappears.
- A failed/blocked source keeps its last successful content while the other
  source can update. A complete, successful GitHub snapshot removes automatic
  entries whose repositories are no longer public/eligible. Scholar retains
  older records outside the latest-page window. To hide a Scholar record, use
  `exclude_titles` or `exclude_citation_ids`; these also filter cached records.
- Both sources failing makes the workflow fail before publication. A single
  source failure produces a visible Actions warning and summary. Malformed or
  partial responses cannot wipe a previous snapshot. The public HTML is escaped;
  API keys, raw scraped HTML, tooling and source-state files are not deployed.

### Scholar access

The default adapter reads the public profile's latest 100 records once per run.
It does not use `cstart` pagination, solve CAPTCHAs, rotate proxies, or attempt to
bypass a block. Google may block automated requests, including from Actions.
Such a response is recorded as unavailable, never as an empty bibliography.

For the supported API adapter, add an existing SerpApi key as repository secret
**`SERPAPI_KEY`** in **Settings → Secrets and variables → Actions**. Do not place
the key in a file, issue, chat message or workflow YAML. The next run automatically
uses the Scholar Author API with the configured author ID and bounded pagination.
No provider account or paid plan is created by this project. API quota and access
remain dependent on the key's provider plan. The public profile adapter succeeded
locally during setup on 4 October 2026; an earlier request was blocked. Consult
the latest workflow summary for current status from the Actions runner.

References: [GitHub public repositories API](https://docs.github.com/en/rest/repos/repos#list-repositories-for-a-user),
[Scholar robots rules](https://scholar.google.com/robots.txt),
[Scholar access guidance](https://scholar.google.com/intl/en/scholar/help.html),
[SerpApi Scholar Author API](https://serpapi.com/google-scholar-author-api),
[GitHub token and Pages builds](https://docs.github.com/en/actions/concepts/security/github_token).

Validation: `npm test` covers discovery, pagination, identity checks, exclusions,
duplicate records, secrets in errors and source outages. `python -m unittest
discover -s _tools -p 'test_*.py'` exercises the real bilingual renderer with
untrusted metadata and checks that the public CV remains byte-for-byte unchanged.
`check_site.py` validates internal links, unique IDs, schema, verification and
editorial publication visibility before every deployment.

## Manual editorial updates

Edit `_data/profile.json`, then run:

```sh
python _tools/build_profile.py
```

Requires Python with `beautifulsoup4`. The command refreshes the English and
Russian timeline, project, publication, poster and talk sections. It preserves
`experience/EkaterinaAntipushinaCV.pdf`: selecting an authored CV is separate from
updating website content. The generated HTML is committed for GitHub Pages.
The rest of the bilingual biography remains in the HTML pages.

To update just publications, posters and talks, run:

```sh
python _tools/build_profile.py --research-only
```

Publications, posters and talks,
including their links and media, are maintained in `_data/profile.json`.
`updated` records the CV/content audit date; `page_updated` records the page
update date. `assets_version` versions the stylesheet, including multiple
design revisions on the same day. Keep `sitemap.xml` dates in sync with page
updates. Image dimensions are stored alongside each image URL.

`--cv-draft` optionally generates `_cv/academic.tex` and `_cv/academic-draft.pdf`
using XeLaTeX and Arial. It never replaces the public CV. Review/select the
public PDF independently; do not automatically publish the generated draft.

## Profile and poster update, 1 October 2026

- Added explicit LLM and computer vision focus to both introductions, biographies,
  search descriptions and structured data. Expanded the spatial-intelligence
  experience with RAG, tool calling and answer verification, supported by the
  author's July 2026 LLM Agent Engineer CV. Kept existing employment dates.
- Curated the website to eight papers. `show_on_site: false` hides `ventricular`,
  `kidney`, `pearson` and `sensations` at the author's request. Bibliography data
  remains available for archival use; every visible paper has an original figure.
- All four posters now have lightweight linked images, shown in full without
  cropping. `rest2task.webp` and `lift.webp` are previews of the existing files
  in `research/posters/`. `tms.webp` is the English poster from the author's
  [ResearchGate upload](https://www.researchgate.net/publication/380169968_Development_of_a_personalized_Transcranial_Magnetic_Stimulation_complex_utilizing_biofeedback).
- `benchmark.svg` is a website illustration, explicitly captioned as such; the
  original poster was not available. It contains no experimental results. The
  card now links to the [specific publication record](https://www.researchgate.net/publication/377979033_Benchmarking_of_Machine_Learning_and_Deep_Learning_approaches_for_Neuroimaging_Data)
  rather than the general author profile.
- The previous public CV is preserved pending the author's choice of an existing
  designed version. Updating the page must not regenerate or overwrite it.

## Publication and talk layout, 1 October 2026

- Replaced large cards with illustrated rows, grouped publications by year,
  and highlighted the profile owner's name in author lists.
- Preserved all 12 publication records, their statuses, and both talks.
  Only NeuroTalk is labeled an invited talk; DataFest is a conference talk.
- Added native expandable talk descriptions and compact resource links.
  Both language versions remain usable without JavaScript and on mobile.
- Nine WebP thumbnails in `img/publications/` use original paper illustrations,
  selected for clarity at preview size. Complete figures retain their labels,
  legends and original colours. These are extracted or rendered images, with
  no generated scientific content. Sources are listed below.
- NeuroTalk uses the event's [official announcement image](https://t.me/itatmisis/1676).
  DataFest reuses its existing talk image.
- Three publications still have topic covers: the kidney-cancer paper has
  tables but no figures in its public full text; the Artificial Sensations PDF
  and the 2021 ventricular-assist paper PDF were not available locally or from
  accessible publisher downloads. Do not substitute unrelated illustrations.

### Publication thumbnail sources

Paper URLs and authors are also stored in `_data/profile.json` and displayed
beside their thumbnails. The images are resized and encoded as WebP.

| Asset | Original illustration |
| --- | --- |
| `cardiac.webp` | Geometry-Aware Multi-View Cardiac MRI, figure 2, page 6: cine/LGE validation predictions; extracted from the author's PDF. |
| `tabs.webp` | TABS, figure 3, page 7: ultrasound landmark predictions; extracted from the author's PDF. |
| `oct.webp` | SynthOCT, figure 4, page 7: real, reconstructed and error maps; extracted from the author's PDF. |
| `organoids.webp` | [iScience graphical abstract](https://ars.els-cdn.com/content/image/1-s2.0-S2589004226010898-fx1_lrg.jpg). |
| `cstnet.webp` | CSTNet, figure 2, page 4: brain model and EEG/ECoG data generation; extracted from the author's PDF. |
| `biomarkers.webp` | [Fluids and Barriers of the CNS, figure 7](https://media.springernature.com/full/springer-static/image/art%3A10.1186%2Fs12987-025-00731-z/MediaObjects/12987_2025_731_Fig7_HTML.png): hypoxic injury at the ChP–CSF interface. |
| `pyopennft.webp` | pyOpenNFT, figure 1, page 4: neurofeedback interface; rendered from the author's PDF. |
| `eegfmri.webp` | EEG-to-fMRI Prediction for Neurofeedback, figure 1, page 5: four EEG topomaps; rendered from the author's PDF. |
| `pearson.webp` | [bioRxiv preprint](https://www.biorxiv.org/content/10.1101/2024.04.23.590747v1.full.pdf), figure 1, page 2: canonical-correlation preprocessing; extracted from the PDF. |

## Content audit, 12 September 2026

- Replaced the old CV containing two selected papers with an academic CV.
- Corrected employment dates using the owner's current CV, revised 7 September:
  Spatial Intelligence Lab starts October 2025; neuroimaging work runs from
  November 2024 to September 2025; Sharjah runs July 2024 to August 2025, part-time.
  Restored the Medical AI / BIMAI-Lab role, January 2023 to December 2024.
- Kept the PhD as an ongoing degree. Used neutral degree names for Skoltech:
  the official Life Sciences profile and the CV's research-specialization labels
  should not be treated as interchangeable official degree titles.
- Added foundation-model research, medical imaging, organoid data analysis,
  and Neuroforum using the current CV. Computational work is distinguished from
  experimental organoid work. Huawei is a collaborator, not a separate employer.
- Expanded the bibliography from 7 to 12 distinct records: 7 published papers,
  3 accepted 2026 contributions, and 2 preprints. Added two missing posters.
  Duplicate ResearchGate entries for CSTNet and the MICCAI proceedings volume
  are not separate papers. The four posters are separate from the paper count.
- Corrected CSTNet's publication year to 2026 while retaining the 2025 workshop.
  Added DOI links and the SynthOCT OpenReview record. Removed isolated benchmark
  figures and ranking claims from the short summaries, whose evaluation context
  was not given on the site. No blanket shared-first-authorship claim is made.
- Verified local links and anchors, public project repositories, and talk links.
  Reused the public CV path and versioned its download links to refresh caches.
- Google Scholar returned a rate limit during this audit. The bibliography was
  instead reconciled against publisher metadata, public OpenReview records,
  ResearchGate, and the owner's current CV. This is a verified collection,
  not a claim that no other publications exist.

## Bibliographic sources

Each paper's source URL is stored in `_data/profile.json`. DOI title, author,
year, and venue metadata were checked through Crossref where available.

- [OpenReview: cardiac MRI](https://openreview.net/forum?id=8fgjDHh6FH)
- [OpenReview: TABS](https://openreview.net/forum?id=5IcejzMtsU)
- [OpenReview: SynthOCT](https://openreview.net/forum?id=eT8xnrF58D)
- [ResearchGate profile](https://www.researchgate.net/profile/Ekaterina-Antipushina)
- [Skoltech profile](https://crei.skoltech.ru/cls/people/ekaterinaantipushina)
- [Skoltech interview](https://student.skoltech.ru/ekaterinaantipushinaeng)

OpenReview's public search API exposed the author-released records for the three
2026 papers. Their acceptance status also appears in the owner's current CV.
They are labeled accepted, rather than implying a published Springer volume.
The 2021 conference-paper record and the two added posters use ResearchGate
records; no unverified conference venue or DOI has been supplied for them.
