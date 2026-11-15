# How these docs work

This site is built with [MkDocs](https://www.mkdocs.org/) and the [Material](https://squidfunk.github.io/mkdocs-material/) theme, from `docs/mkdocs.yml` and the pages in `docs/docs/`.

## Two sections

- **The help centre** (Home, Start here, Equipment, Work, Community, Help) is for the people who use the app: clinic staff, engineers, community leads. Plain, short sentences; numbered steps; a screenshot per guide; no code.
- **Developers** (this tab) is for people who build and run the app.

Every user guide follows the same shape:

1. the title, then an **In the app** line naming the world and the menu entry (`<div class="in-app equipment|work|community|all" markdown>`);
2. **Who this is for** and **What you need before**;
3. numbered **Steps**;
4. **What happens next**;
5. **If something goes wrong**.

Use the app's exact labels, in bold, as they appear in `frontend/i18n.py` (English) and, on French pages, the French string of the same key.

## Page names are a contract

The app links to this site as `{DOCS_URL}{page}/`. These file names must stay, in `docs/docs/`, at the top level:

`index`, `three-worlds`, `start-clinic`, `start-engineer`, `start-lead`, `register-device`, `report-fault`, `attach-manual`, `clinic-devices`, `call-engineer`, `engineer-workspace`, `community-work`, `community-guide`, `faq`, `glossary`.

Renaming or moving one breaks a link in the app. Add new pages freely.

## Translations

Translations use the [mkdocs-static-i18n](https://github.com/ultrabug/mkdocs-static-i18n) plugin, with the **suffix** layout:

- `page.md` is English (the default language, served at `/page/`);
- `page.fr.md` next to it is French (served at `/fr/page/`);
- a page without a French file shows the English one on the French site;
- images follow the same rule: `images/guide/x.fr.png` replaces `x.png` on French pages.

The header has a language switcher. Menu titles are translated in `mkdocs.yml` (`nav_translations`).

Translated now: `index`, `three-worlds`, `start-clinic`, `start-engineer`, `start-lead`, `faq`, `glossary`, `register-device`, `report-fault`, `attach-manual`, `clinic-devices`, `call-engineer`, `engineer-workspace`, `community-work`. Spanish is not set up yet: add `- locale: es` under `languages` in `mkdocs.yml` and `page.es.md` files.

When you change an English page, change its French page in the same pull request.

## Build and preview

```bash
cd docs
pip install -r requirements.txt     # includes mkdocs-material and mkdocs-static-i18n
mkdocs serve                         # http://127.0.0.1:8000
mkdocs build --strict                # what to run before a pull request
```

The site is published to GitHub Pages (branch `gh-pages`) with `mkdocs gh-deploy` from `docs/`. Whoever deploys must install `docs/requirements.txt` first: without `mkdocs-static-i18n` the build fails with *"The "i18n" plugin is not installed"*.

The narrated videos (`docs/docs/videos/*.mp4`) are not in git (`.gitignore`). The guides link to them in a folded "Watch the video" block; they only play on the published site if the person who deploys has the files locally.

## Screenshots

The screenshots in `docs/docs/images/guide/` are made by `scripts/docs_screenshots.js` (Node and Playwright with Chromium). It signs in as the seeded accounts (`scripts/seed_test_data.py`, password `Pass123!`) and saves each shot in English (`name.png`) and French (`name.fr.png`), at phone width (390 px) for clinic and engineer flows and 1280 px for dashboards, at 2x.

```bash
# the local stack, seeded
docker compose -f docker-compose.local.yml up --build -d
python scripts/seed_test_data.py
python scripts/walk_onboarding.py            # an engineer with clinics (eng<run>@fmt-demo.org)

node scripts/docs_screenshots.js --seed-demo # first time: also creates a demo call and offer
node scripts/docs_screenshots.js --only=dashboard,qr-page --lang=fr
BASE_URL=http://localhost:8888 node scripts/docs_screenshots.js
```

- `--seed-demo` creates, once, a **Call an engineer** request on the seeded Ultrasound (as `admin@mulago.org`) and an offer on it (as `eng@mulago.org`), so the call, request and fault screens are not empty.
- The engineer with clinics is `eng759585@fmt-demo.org` in the script (`ACCOUNTS.engineer`); change it to the `eng<run>` account your `walk_onboarding.py` run printed.
- When `python3` with Pillow is installed, each PNG is reduced to 256 colours (about a third of the size). `--no-shrink` keeps the full PNG.
- Look at every image you change: it must show what the text says.
- The list of shots is the `SHOTS` array at the top of the script. Add one entry per new screenshot.

**To do at the next regeneration:** the in-app guides (`/community/guides`, "Learn the app") and the new Community home (`/community`) were not merged when these screenshots were taken. Add shots for them, and for the "?" help panel, once they are in `dev`.
