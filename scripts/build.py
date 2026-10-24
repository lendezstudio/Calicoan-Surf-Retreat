"""Render the one-page site into dist/.

Usage:
  python scripts/build.py                          # preview build: noindex, no canonical or sitemap
  python scripts/build.py --env production --site-url https://example.com/path/

Media derivatives must exist first (python scripts/media.py).
"""
import argparse
import datetime
import hashlib
import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DIST = ROOT / "dist"

FAQ = [
    ("Where is Calicoan Surf Retreat?",
     "In Calicoan Island, Guiuan, Eastern Samar, near ABCD Beach. Use the map link and confirm the entrance before your first visit."),
    ("Do I need to surf to stay?",
     "Your trip doesn’t have to revolve around surfing. Explore the stay options and plan the visit around the people you’re traveling with."),
    ("How do I check rates and available stays?",
     "Send your arrival and departure dates, number of guests and preferred accommodation. Ask for the current rate, inclusions and reservation terms before confirming."),
    ("Are surf lessons or board rentals included?",
     "Don’t assume lessons or equipment are included with accommodation. Check arrangements with the property and the local operator before making plans."),
    ("What should I confirm before reserving?",
     "Ask about your room’s capacity and amenities, payment and cancellation terms, check-in arrangements and any specific needs for your party."),
]


def public(entry):
    return entry.get("status") != "hidden"


def lightbox_item(media, text, id):
    m = media[id]
    return {
        "avif": ", ".join(f"media/{id}-{w}.avif {w}w" for w in m["widths"]),
        "jpg": ", ".join(f"media/{id}-{w}.jpg {w}w" for w in m["widths"]),
        "src": f"media/{id}-{m['widths'][-1]}.jpg",
        "width": m["width"], "height": m["height"],
        "alt": text[id]["alt"], "caption": text[id]["caption"],
    }


def structured_data(c, site_url):
    b, contact = c["business"], c["contact"]
    data = {
        "@context": "https://schema.org",
        "@type": "LodgingBusiness",
        "name": b["name"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": b["locality"],
            "addressRegion": b["region"],
            "addressCountry": b["countryCode"],
        },
    }
    if b["streetAddress"]["status"] == "approved":
        data["address"]["streetAddress"] = b["streetAddress"]["value"]
        data["address"]["postalCode"] = b["streetAddress"]["postalCode"]
    if public(contact["phone"]):
        data["telephone"] = contact["phone"]["e164"]
    if public(contact["facebook"]):
        data["sameAs"] = [contact["facebook"]["url"]]
    if site_url:
        data["url"] = site_url
        data["image"] = site_url + "media/og-image.jpg"
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=["preview", "production"], default="preview")
    ap.add_argument("--site-url", default="", help="Absolute production URL ending in /")
    args = ap.parse_args()
    site_url = args.site_url.strip()
    if args.env == "production":
        if not site_url.startswith("https://"):
            raise SystemExit("Production builds need --site-url https://.../ (the real deployment URL).")
        site_url = site_url.rstrip("/") + "/"
    else:
        site_url = ""

    content = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))
    media = json.loads((SRC / "media" / "manifest.json").read_text())
    text = content["media"]

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for folder in ("media", "fonts", "favicon"):
        shutil.copytree(SRC / folder, DIST / folder, ignore=shutil.ignore_patterns("manifest.json"))
    for name in ("styles.css", "main.js"):
        shutil.copy2(SRC / name, DIST / name)

    version = hashlib.sha1(b"".join((SRC / n).read_bytes() for n in ("styles.css", "main.js"))).hexdigest()[:8]
    client_data = {
        "gallery": [dict(lightbox_item(media, text, id), group=text[id]["group"]) for id in content["gallery"]],
        "stays": {s["id"]: {"name": s["name"], "photos": [lightbox_item(media, text, p) for p in s["photos"]]}
                  for s in content["stays"]},
        "stayNames": {s["id"]: s["name"] for s in content["stays"]},
        "businessName": content["business"]["name"],
    }

    env = Environment(loader=FileSystemLoader(SRC), undefined=StrictUndefined, autoescape=True,
                      trim_blocks=False, lstrip_blocks=False)
    html = env.get_template("index.html.j2").render(
        business=content["business"], contact=content["contact"], stays=content["stays"],
        gallery=content["gallery"], strip=content["strip"], videos=content["videos"],
        credit=content["credit"], seo=content["seo"], media=media, media_text=text, faq=FAQ,
        year=datetime.date.today().year, version=version, client_data=client_data,
        structured_data=structured_data(content, site_url),
        env={"noindex": args.env != "production", "site_url": site_url},
    )
    (DIST / "index.html").write_text(html, encoding="utf-8")

    (DIST / "site.webmanifest").write_text(json.dumps({
        "name": content["business"]["name"], "short_name": "Calicoan",
        "icons": [{"src": "favicon/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "favicon/icon-512.png", "sizes": "512x512", "type": "image/png"}],
        "theme_color": "#f7f3ea", "background_color": "#f7f3ea", "display": "browser",
    }, indent=1))

    if args.env == "production":
        (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site_url}sitemap.xml\n")
        (DIST / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"  <url><loc>{site_url}</loc><lastmod>{datetime.date.today().isoformat()}</lastmod></url>\n"
            "</urlset>\n")
    else:
        (DIST / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    (DIST / ".nojekyll").write_text("")

    size = sum(p.stat().st_size for p in DIST.rglob("*") if p.is_file())
    print(f"Built {args.env} site in dist/ ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
