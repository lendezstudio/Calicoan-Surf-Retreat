# Calicoan Surf Retreat website

A static one-page site for Calicoan Surf Retreat (Guiuan, Eastern Samar). It is built by a small Python script from one content file. There is no framework or runtime dependency, and the output in `dist/` is plain HTML, CSS and JS.

## Folders

| Path | Purpose |
| --- | --- |
| `Initial Assets/` | Original supplied media and the brief. Local only (git-ignored), never edited or published. |
| `content/site.json` | Business facts, stays, captions and approval flags (`concept` / `hidden` / `approved`) |
| `src/` | Page template (`index.html.j2`), `styles.css`, `main.js`, self-hosted fonts (OFL), generated `media/` and `favicon/` |
| `scripts/media.py` | Builds optimized images, posters, videos, logo variants, favicons and the OG image from the originals |
| `scripts/build.py` | Renders `dist/` |
| `scripts/check.py` | Playwright screenshots and interaction checks |
| `docs/` | Asset manifest, design reference, content verification, launch checklist. Internal, local only (git-ignored). |
| `dist/` | Deployable output |

## Requirements

- Python 3.12+ with `pip install -r requirements.txt`
- ffmpeg on PATH (only for `media.py`)
- `python -m playwright install chromium` (only for checks)

## Build

```sh
python scripts/media.py          # only when originals or crops change
python scripts/build.py          # preview build (default)
```

**Preview builds** add `<meta name="robots" content="noindex, nofollow">` and a disallow-all `robots.txt`. They have no canonical URL or sitemap.

**Production builds** need the real URL:

```sh
python scripts/build.py --env production --site-url https://example.github.io/calicoan/
```

This adds the canonical URL, `og:url`, an absolute OG image URL, `sitemap.xml` and an allowing `robots.txt`. Never invent a URL; use the deployed one.

## Base path

All asset and anchor links are relative, so `dist/` works at a domain root or any subpath (such as GitHub Pages project sites) without configuration. `.nojekyll` is included.

## Preview and checks

```sh
python -m http.server 8765 --bind 127.0.0.1   # from the project root
# open http://127.0.0.1:8765/dist/
python scripts/check.py screenshots
```

The checks cover:
- 320 to 1920 px widths for overflow
- console and network errors
- menu focus and Escape
- anchor offsets
- lightbox keys
- gallery filters
- video play/pause
- FAQ
- composer validation, clipboard copy and fallback
- no-JS rendering

## Editing content

- Change text and facts in `content/site.json`, then rebuild.
- Room "chips" (capacity, amenities) render only when their `status` is `approved`.
- Contacts with `status: "hidden"` are not rendered.
- Section copy lives in `src/index.html.j2`. FAQ answers are in `scripts/build.py`.

## Inquiry composer

The composer builds a message in the browser. Nothing is submitted, stored or put in the URL. "Copy Inquiry" copies it to the clipboard, and "Open Facebook" opens the page in a new tab for the guest to paste and send. There is no booking engine or form endpoint.

## Deploy (GitHub Pages)

Pages serves the `gh-pages` branch, which holds only the contents of `dist/`. The live site is https://lendezstudio.github.io/Calicoan-Surf-Retreat/. After rebuilding and committing on `main`:

```sh
git push
git subtree split --prefix dist -b gh-pages-tmp
git push -f origin gh-pages-tmp:gh-pages
git branch -D gh-pages-tmp
```

The root `index.html` and `.nojekyll` on `main` are a fallback that forwards to `dist/` if Pages is ever switched back to the `main` branch.
