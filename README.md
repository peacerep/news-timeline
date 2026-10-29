# PeaceRep News timeline — designer handoff

This is a self-contained, **local planning prototype** for the 172 captured PeaceRep News posts. Run it with Docker; it needs no host-side package manager or access to the original tracker repository. All 172 posts, including their saved full text, are in `data/news.json`.

```powershell
docker compose up --build -d
```

Open `http://localhost:8080`. Stop it with `docker compose down`. To check the JavaScript in Docker, run `docker compose --profile check run --rm check`. To test navigation, images, filters, colours, and A4 printing in Chromium, run `docker compose --profile check run --rm browser-check` (build its image first with `docker compose build browser-check`).

To regenerate all three A4 PDFs entirely in Docker, run `docker compose --profile compendium run --rm compendium`. The `output/` folder contains a short news summary, a full-text chronological edition with editorial candidate highlights, and a full-text edition organised by the ten story types. All three include all 172 saved posts; the two long editions retain their full captured text, available images and original source links. Their HTML source is saved alongside the PDFs for designer edits. The site mounts `output/` read-only as `/downloads`, so its three PDF buttons download these files directly. **Print current view** remains available for a filtered or focused page. The PDFs are **drafts for internal review**: highlights, image rights and impact wording need manager approval before they are sent to funders. Edit `editorial/compendium-highlights.json` to change the candidate selection, then regenerate. The generator is `scripts/build_compendia.py`.

## GitHub Pages preview

The standalone folder includes a manually triggered GitHub Pages workflow in `.github/workflows/pages.yml`. It assembles `pages-dist/` from `index.html`, `assets/`, `data/`, and the three finished PDFs. It does not publish `editorial/`, source scripts, the full-text compendium HTML files, or other files in the parent workspace. The package adds a visible **editorial preview** label and a `noindex,nofollow` request. These do not restrict access to a publicly published Pages site.

Build and check the project-site path in Docker:

```powershell
docker compose --profile pages run --rm pages-build
docker compose --profile pages up -d pages-preview
docker compose --profile pages run --rm pages-check
```

The local Pages preview is at `http://localhost:8081/news-timeline/`, matching the intended `peacerep/news-timeline` repository. Relative paths also work under a different repository name. To publish after the release decision, use this folder as the repository root, choose **GitHub Actions** in repository **Settings → Pages → Build and deployment**, then run the **Publish PeaceRep news preview** workflow. The site will be at `https://peacerep.github.io/news-timeline/` unless a custom domain is configured. The workflow has no push trigger, so uploading the source alone will not publish it. Check Pages visibility and editorial/image permissions before running it.

## What is here

- `index.html`, `assets/app.js`, `assets/styles.css`: an interactive date-scaled dot rail linked to scrolling image cards, story-type filters, full-text search, expandable full articles and portrait A4 print styling. On a normal desktop viewport the header, search and legend stay in place while the story list scrolls; the mouse wheel works over the date rail too. On narrower desktop layouts the controls stick to the top during page scrolling. Selecting a dot keeps its connector and card highlighted. A card can be opened directly with `?story=POST_ID` while keeping the timeline interface visible.
- `assets/images/`: locally saved featured images for 169 posts and 105 saved inline images (251 unique files). Three source posts have no saved featured image; three inline images failed in the original capture.
- `assets/fonts/`: locally bundled Montserrat variable font and its SIL Open Font License, sourced from the official Google Fonts repository. The site and print view do not need a live font service.
- `assets/brand/peacerep-logo.png`: the PeaceRep logo bundled from the project's [published logo library](https://peacerep.github.io/logos/).
- `data/news.json`: the single frozen, portable data snapshot, derived from the saved 28 October 2026 capture and the current version 5 classification proposal.
- `editorial/`: one current classification CSV, its report, and the ten-type guide for the designer and communications reviewer. These files are handoff copies; the original capture and review sheet remain in the parent workspace.
- `editorial/impact-news-crosswalk.md`: working links between the three existing PeaceRep impact pages and the saved News archive. It records exact, related and missing matches for manager review; no impact claims have been approved or added to the public timeline.
- `scripts/export_news.py`: regenerates that snapshot from a capture and proposal CSV supplied as arguments.

The visual starting point is the team's existing implementation narratives tracker (`src/views/timelineView.vue` in the original Vue 3 repository): dated cards linked to a vertical dot rail. This site implements the same core interaction with date-scaled dots, collision spacing, clickable navigation, hover highlighting, a scrolling card column, and SVG connectors. Hovering or focusing a story-type filter highlights its dots. Compact desktop cards show several stories in the timeline window. Small screens use a chronological card list. Print switches the scrolling column to full document flow so all filtered stories can print on A4 pages.

The [Yemen timeline source](https://github.com/peacerep/yemen-timeline) is a second design reference. Its repository is a compact HTML/CSS project with bilingual data files. It is useful for chronological storytelling, language switching, and presentation choices; the implementation narratives tracker is the closer reference for news cards. This folder does not depend on either repository at runtime.

The story colours are drawn from the [PeaceRep and PA-X main colours](https://peacerep.github.io/logos/#colors). The filter chips form the colour legend, and every card badge and date dot uses the same type colour. The labels and outline remain readable for the lighter brand colours.

The header, warm page background and restrained borders take cues from the adjacent `peace-resources-landing/PA-X-landing.html` draft. The logo sits beside the **PeaceRep news and impact** title, which uses Montserrat like the rest of the interface. The news timeline's own cards, dots and category colours are kept as a separate component. The introduction distinguishes the full news archive from individual stories about how PeaceRep's work is used; no impact claims have been approved.

## Editorial status

The labels are an **unreviewed proposal**, not approved impact claims. `impact_area`, impact story assignments, and publication approval were left out of this portable snapshot. The prototype uses the post **publication date** for the timeline and includes the saved article body in a focused card. It covers WordPress News posts only, not the separate Event posts or blogs. Article HTML is rebuilt from a restricted set of safe elements and attributes before display. Links to other captured News posts open inside this interface; other source links still point to their original destinations and need mapping before the existing site is retired. Captured images are included for this **local design prototype**; source metadata marks their public reuse rights as unreviewed. Review image rights and credits before publishing or sharing the site publicly.

The source archive and review template remain outside this folder and are not changed by it. Earlier proposal versions are also outside this folder: there is only one current news snapshot here. If this folder is copied to a designer, it remains usable on its own.

## Suggested designer work

1. Refine the cards, year navigation, ten type colours, mobile spacing, and accessible interaction.
2. Decide whether a beeswarm overview helps readers move between dense periods; keep the vertical cards as the readable article view.
3. Design a separate, curated funder PDF from approved impact stories. The print stylesheet here is an A4 layout test for the news timeline, not the final PDF.
4. Replace proposal data with an approved editorial export before publication; retain source IDs and URLs.

## Refresh the snapshot

From this folder, run the exporter in Docker:

```powershell
docker compose --profile export run --rm export
docker compose up --build -d
```

The default input mounts point to the current capture directory and version 5 proposal in the parent workspace. If the folder is handed over separately, set `NEWS_CAPTURE_DIR` and `NEWS_PROPOSAL_FILE` to the relevant absolute source paths before running the exporter. The script validates 172 unique IDs, matching source metadata, allowed story types, blank impact/approval fields, and saved image checksums. It writes `data/news.json` and copies featured images. The input files are separate editorial sources and are not included in this handoff folder.
