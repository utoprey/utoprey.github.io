# Updating the public profile

Edit `_data/profile.json`, then run:

```sh
python _tools/build_profile.py
```

Requires Python with `beautifulsoup4`, XeLaTeX, and Arial. The command refreshes
the English and Russian timeline, project, publication and talk sections, generates
`_cv/academic.tex`, and compiles `experience/EkaterinaAntipushinaCV.pdf`.
The generated HTML and PDF are committed; GitHub Pages serves them directly.
The rest of the bilingual biography remains in the HTML pages.

To update just publications and talks without rebuilding the CV, run:

```sh
python _tools/build_profile.py --research-only
```

This mode only requires Python with `beautifulsoup4`. Publications and talks,
including their links and media, are maintained in `_data/profile.json`.
`updated` records the CV/content audit date; `page_updated` records the page
update date and versions the stylesheet. Keep `sitemap.xml` dates in sync with
page updates.

## Publication and talk layout, 1 October 2026

- Replaced large cards with illustrated rows, grouped publications by year,
  and highlighted the profile owner's name in author lists.
- Preserved all 12 publication records, their statuses, and both talks.
  Only NeuroTalk is labeled an invited talk; DataFest is a conference talk.
- Added native expandable talk descriptions and compact resource links.
  Both language versions remain usable without JavaScript and on mobile.
- Five WebP thumbnails in `img/publications/` are crops from the owner's
  paper PDFs: TABS figure 1 (page 2), SynthOCT scanner diagram (page 4),
  pyOpenNFT interface figure (page 4), CSTNet workflow (page 3), and
  EEG-to-fMRI topomaps (page 5). Corresponding paper links are in the JSON.
  Other records use typographic topic/venue covers. DataFest reuses its
  existing talk image. No artwork from the design reference was copied.

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
