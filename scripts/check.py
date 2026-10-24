"""Rendered checks with Playwright (Chromium).

Serve the project root first so the site is tested under a subpath:
  python -m http.server 8765 --bind 127.0.0.1
  python scripts/check.py [output-dir]

Takes full-page screenshots at several widths, reports horizontal overflow,
console errors and failed requests, then exercises the interactive parts.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/dist/"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "screenshots")
OUT.mkdir(parents=True, exist_ok=True)
WIDTHS = [(320, 640), (390, 844), (768, 1024), (1024, 768), (1440, 900), (1920, 1080)]

problems = []


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        problems.append(label)


def watch(page):
    page.on("console", lambda m: m.type == "error" and problems.append(f"console: {m.text}"))
    page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: problems.append(f"requestfailed: {r.url}"))
    page.on("response", lambda r: r.status >= 400 and problems.append(f"HTTP {r.status}: {r.url}"))


def load_all(page):
    """Scroll through so lazy images load before a full-page screenshot."""
    h = page.evaluate("document.body.scrollHeight")
    y = 0
    while y < h:
        page.mouse.wheel(0, 700)
        page.wait_for_timeout(120)
        y += 700
        h = page.evaluate("document.body.scrollHeight")
    page.wait_for_timeout(600)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)


with sync_playwright() as p:
    browser = p.chromium.launch()

    for w, h in WIDTHS:
        ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
        page = ctx.new_page()
        watch(page)
        page.goto(URL, wait_until="networkidle")
        page.screenshot(path=OUT / f"fold-{w}.png")
        load_all(page)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        check(overflow <= 0, f"{w}px: no horizontal overflow ({overflow}px)")
        page.screenshot(path=OUT / f"full-{w}.png", full_page=True)
        ctx.close()

    # Interactions at phone width with motion enabled.
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, permissions=["clipboard-read", "clipboard-write"])
    page = ctx.new_page()
    watch(page)
    page.goto(URL, wait_until="networkidle")

    check(page.locator("h1").count() == 1, "exactly one h1")
    check(page.locator('meta[name="robots"][content*="noindex"]').count() == 1, "preview build is noindex")

    page.click("[data-menu-open]")
    check(page.locator("[data-menu]").is_visible(), "mobile menu opens")
    check(page.evaluate("document.activeElement.closest('[data-menu]') !== null"), "focus moves into menu")
    page.keyboard.press("Escape")
    check(page.locator("[data-menu]").is_hidden(), "Escape closes menu")
    check(page.evaluate("document.activeElement.matches('[data-menu-open]')"), "focus returns to menu button")

    page.click("[data-menu-open]")
    page.click("[data-menu] a[href='#plan']")
    page.wait_for_timeout(2500)
    top = page.evaluate("document.querySelector('#plan').getBoundingClientRect().top")
    header_h = page.evaluate("document.querySelector('[data-header]').getBoundingClientRect().height")
    check(header_h - 2 <= top <= header_h + 40, f"anchor lands just below sticky header (top {top:.0f}, header {header_h:.0f})")

    page.click('[data-lightbox-set="loft"]')
    check(page.locator("[data-lightbox]").is_visible(), "stay photo viewer opens")
    page.keyboard.press("ArrowRight")
    check("2 / 5" in page.inner_text("[data-lightbox-count]"), "arrow key advances photos")
    page.keyboard.press("Escape")
    check(page.locator("[data-lightbox]").is_hidden(), "Escape closes photo viewer")

    page.click('[data-filter="calicoan"]')
    visible = page.locator(".gallery__item:not([hidden])").count()
    check(0 < visible < page.locator(".gallery__item").count(), f"gallery filter narrows photos ({visible})")
    page.locator(".gallery__item:not([hidden]) .gallery__open").first.click()
    check(page.locator("[data-lightbox]").is_visible(), "gallery lightbox opens")
    page.click("[data-lightbox-close]")
    page.click('[data-filter="all"]')

    page.locator("[data-film-toggle]").first.click()
    page.wait_for_timeout(1500)
    check(page.locator("[data-player]").is_visible(), "video opens enlarged in the player")
    playing = page.evaluate("!document.querySelector('[data-player-video]').paused")
    check(playing, "video plays on request")
    check("Pause video" in page.locator("[data-player-toggle]").text_content(), "player button shows Pause")
    check(page.evaluate("!document.querySelector('[data-player-video]').muted"), "video plays with sound")
    page.click("[data-player-mute]")
    check(page.evaluate("document.querySelector('[data-player-video]').muted") and page.locator("[data-player-mute]").text_content() == "Unmute", "mute button mutes")
    stage = page.evaluate("document.querySelector('.player__stage').getBoundingClientRect().height")
    check(stage > 500, f"player video is enlarged ({stage:.0f}px tall)")
    page.locator("[data-player-toggle]").click()
    check(page.evaluate("document.querySelector('[data-player-video]').paused"), "player pauses")
    page.keyboard.press("Escape")
    check(page.locator("[data-player]").is_hidden(), "Escape closes the player")
    check(page.evaluate("document.activeElement.matches('[data-film-toggle]')"), "focus returns to the video button")

    page.locator(".faq__item summary").first.click()
    check(page.locator(".faq__item").first.get_attribute("open") is not None, "FAQ opens")

    # Composer validation and copy.
    page.click('a[data-stay="family"]')
    page.wait_for_timeout(600)
    check(page.input_value("#stay") == "family", "stay link preselects the stay")
    page.click("button[type=submit]")
    check("Choose your arrival date." in page.inner_text("#arrival-error"), "missing arrival is reported")
    today = page.evaluate("(() => { const d = new Date(); d.setDate(d.getDate() + 10); return d.toISOString().slice(0,10) })()")
    page.fill("#arrival", today)
    page.fill("#departure", today)
    page.fill("#guests", "4")
    page.click("button[type=submit]")
    check("Choose a departure date after your arrival date." in page.inner_text("#departure-error"), "departure must follow arrival")
    page.fill("#departure", "")
    page.evaluate("""(() => { const a = document.querySelector('#arrival').value.split('-').map(Number);
        const d = new Date(a[0], a[1]-1, a[2] + 3); const p = n => String(n).padStart(2,'0');
        document.querySelector('#departure').value = `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`;
        document.querySelector('#departure').dispatchEvent(new Event('input', {bubbles:true})); })()""")
    page.fill("#guests", "0")
    page.click("button[type=submit]")
    check("1 or more" in page.inner_text("#guests-error"), "zero guests rejected")
    page.fill("#guests", "4")
    page.fill("#note", "Do you have space for two surfboards?")
    page.click("button[type=submit]")
    page.wait_for_timeout(300)
    status = page.inner_text("[data-status]")
    check(status.startswith("Inquiry copied."), f"copy success message ({status})")
    clip = page.evaluate("navigator.clipboard.readText()")
    check("Preferred stay: Container Family Room" in clip and "Guests: 4" in clip and "Question: Do you have space" in clip,
          "copied text follows the template")
    body = page.inner_text("body").lower()
    check("sent" not in status.lower() and "confirmed" not in status.lower(), "no sent/confirmed state")
    check("[business owner to confirm]" not in body and "coming soon" not in body, "no placeholders on the page")
    check(page.url.endswith("/dist/#inquiry") and "?" not in page.url, "no inquiry data in the URL")
    page.screenshot(path=OUT / "composer-390.png", full_page=False)

    # Clipboard denied: fallback message.
    ctx2 = browser.new_context(viewport={"width": 390, "height": 844})
    p2 = ctx2.new_page()
    watch(p2)
    p2.add_init_script("Object.defineProperty(navigator, 'clipboard', {value: {writeText: () => Promise.reject(new Error('denied'))}}); document.execCommand = () => false;")
    p2.goto(URL + "#inquiry", wait_until="networkidle")
    p2.fill("#arrival", today)
    p2.evaluate("""(() => { const a = document.querySelector('#arrival').value.split('-').map(Number);
        const d = new Date(a[0], a[1]-1, a[2] + 2); const p = n => String(n).padStart(2,'0');
        const el = document.querySelector('#departure'); el.value = `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}`;
        el.dispatchEvent(new Event('input', {bubbles:true})); })()""")
    p2.fill("#guests", "2")
    p2.click("button[type=submit]")
    p2.wait_for_timeout(300)
    check(p2.inner_text("[data-status]") == "Select and copy the message below.", "copy failure shows fallback")
    ctx2.close()

    # Desktop keyboard path and no-JS rendering.
    ctx3 = browser.new_context(viewport={"width": 1440, "height": 900}, java_script_enabled=False)
    p3 = ctx3.new_page()
    p3.goto(URL, wait_until="networkidle")
    check(p3.locator(".stay").count() == 3 and p3.locator(".gallery__item").first.is_visible(), "content renders without JavaScript")
    ctx3.close()

    browser.close()

print("\nProblems:" if problems else "\nAll checks passed.")
for pr in problems:
    print(" -", pr)
sys.exit(1 if problems else 0)
