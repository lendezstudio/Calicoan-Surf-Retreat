"""Build optimized web media from the untouched originals in "Initial Assets".

Outputs go to src/media/ together with src/media/manifest.json, which the
page build reads for intrinsic dimensions and srcset widths.

Run:  python scripts/media.py
Requires Pillow (with AVIF support) and ffmpeg/ffprobe on PATH.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Initial Assets"
OUT = ROOT / "src" / "media"

# Source files, matched by filename prefix so long social filenames stay out of the specs.
FILES = {
    "I00": "498231292_",            # guests outside a kubo with a surfboard
    "I02": "559697310_",            # open-air garden bathroom
    "I04": "565393510_",            # kubo sala (matched to the property tour, 78-80 s)
    "I09": "842719465_",
    "I13": "844302344_",
    "I14": "844462994_",            # hero: longboarder on a reef wave
    "I15": "844545003_",
    "I16": "844860207_",
    "I18": "845291478_",
    "I19": "845298842_",
    "I20": "845564361_",
    "I21": "845747741_",
    "LOGO": "Calicoan surf retreat wave logo",
    "V0": "AQMxH38n800",            # landscape property tour with room overlays
    "V1": "AQObBu7JGVv",            # vertical drone surf footage
    "V2": "AQOqUctl0Sr",            # vertical property reel
    "V3": "AQOuslfeQ9j",            # vertical property reel
    "P_BOARDS": "pexels-jess-vide-4318971",
    "P_WADE": "pexels-jess-vide-4322488",
    "P_YELLOW": "pexels-jess-vide-9269513",
    "P_SPRAY": "pexels-ollivves-1005456",
    "P_SHORE": "pexels-ryan-hiebendahl",
    "P_FINS": "pexels-zulfikar-najwan",
}

# Vertical reels carry a location sticker near the top; this crop keeps a clean 4:5 frame below it.
REEL_4x5 = (0, 165, 360, 615)
# Landscape tour frames carry a round badge at the bottom right.
TOUR_CLEAN = (8, 0, 552, 340)

# id: (source, video time or None, crop box or None, output widths)
IMAGES = {
    "hero":            ("I14", None, None, [768, 1280, 1600, 2048]),
    "hero-portrait":   ("I14", None, (758, 300, 1782, 1365), [480, 768, 1024]),
    "kubo-sala":       ("I04", None, None, [480, 800, 1200]),
    "kubo-exterior":   ("V0", 76.5, TOUR_CLEAN, [544, 960]),
    "loft-lounge":     ("V2", 12.5, REEL_4x5, [360, 720]),
    "loft-bed":        ("V2", 9.5, REEL_4x5, [360, 720]),
    "loft-kitchen":    ("V2", 15.5, REEL_4x5, [360, 720]),
    "loft-billiards":  ("V2", 6.5, REEL_4x5, [360, 720]),
    "loft-exterior":   ("V0", 14.5, TOUR_CLEAN, [544, 960]),
    "family-bed":      ("V3", 15.5, REEL_4x5, [360, 720]),
    "family-bunks":    ("V3", 16.5, REEL_4x5, [360, 720]),
    "family-exterior": ("V0", 10.5, TOUR_CLEAN, [544, 960]),
    "garden-bath":     ("I02", None, (0, 64, 1536, 1984), [480, 800, 1200]),
    "guests-kubo":     ("I00", None, None, [640, 1024, 1600]),
    "aerial-coast":    ("V2", 25.0, (0, 100, 360, 550), [360, 720]),
    "aerial-property": ("V2", 0.5, REEL_4x5, [360, 720]),
    "road":            ("V3", 19.0, REEL_4x5, [360, 720]),
    "surf-21":         ("I21", None, None, [640, 1024, 1600]),
    "surf-13":         ("I13", None, None, [480, 960, 1600]),
    "surf-09":         ("I09", None, None, [480, 960, 1600]),
    "surf-16":         ("I16", None, None, [480, 960, 1600]),
    "surf-18":         ("I18", None, None, [480, 960, 1600]),
    "surf-19":         ("I19", None, None, [480, 960, 1600]),
    "surf-20":         ("I20", None, None, [480, 960, 1600]),
    "surf-15":         ("I15", None, None, [480, 960, 1600]),
    # Square crops for the full-bleed photo strip.
    "strip-sala":      ("I04", None, (0, 189, 1512, 1701), [320, 640]),
    "strip-boards":    ("P_BOARDS", None, (0, 450, 3600, 4050), [320, 640]),
    "strip-yellow":    ("P_YELLOW", None, (0, 900, 4800, 5700), [320, 640]),
    "strip-fins":      ("P_FINS", None, (0, 270, 2160, 2430), [320, 640]),
    "strip-bath":      ("I02", None, (0, 420, 1536, 1956), [320, 640]),
    "strip-surf":      ("I21", None, (506, 0, 1871, 1365), [320, 640]),
    # Pexels photography for mood sections.
    "wade":            ("P_WADE", None, None, [480, 800, 1200]),
    "shore":           ("P_SHORE", None, None, [480, 800, 1200]),
    "spray-wide":      ("P_SPRAY", None, (0, 1300, 4000, 3014), [960, 1600, 2400]),
    "spray-tall":      ("P_SPRAY", None, (0, 400, 4000, 4400), [480, 800, 1200]),
    # Video posters.
    "poster-tour":     ("V3", 0.5, None, [360, 720]),
    "poster-surf":     ("V1", 31.0, None, [360, 720]),
}

# id: (source, start, duration)
VIDEOS = {
    "tour": ("V3", 0.0, 24.5),
    "surf": ("V1", 26.0, 20.0),
}


def source(key):
    matches = [p for p in SRC.iterdir() if p.name.startswith(FILES[key])]
    if len(matches) != 1:
        raise SystemExit(f"Expected one file for {key}, found {matches}")
    return matches[0]


def frame(key, t, tmp):
    path = Path(tmp) / f"{key}_{t}.png"
    if not path.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(source(key)),
                        "-frames:v", "1", str(path)], check=True)
    return Image.open(path).convert("RGB")


def save_set(name, im, widths):
    out = []
    for w in widths:
        if w > im.width * 2:
            continue
        h = round(im.height * w / im.width)
        resized = im.resize((w, h), Image.LANCZOS)
        if w > im.width:
            # Gentle sharpening after upscaling low-resolution video frames.
            resized = resized.filter(ImageFilter.UnsharpMask(radius=1.2, percent=40, threshold=2))
        resized.save(OUT / f"{name}-{w}.avif", quality=58, speed=4)
        resized.save(OUT / f"{name}-{w}.jpg", quality=80, optimize=True, progressive=True)
        out.append(w)
    return {"widths": out, "width": im.width, "height": im.height}


def build_images(tmp):
    manifest = {}
    for name, (key, t, crop, widths) in IMAGES.items():
        if t is None:
            im = ImageOps.exif_transpose(Image.open(source(key))).convert("RGB")
        else:
            im = frame(key, t, tmp)
        if crop:
            im = im.crop(crop)
        manifest[name] = save_set(name, im, widths)
        print(f"{name:16} {im.size} -> {manifest[name]['widths']}")
    return manifest


def build_logo(manifest):
    logo = Image.open(source("LOGO")).convert("RGBA")
    mark = logo.crop((396, 22, 1148, 760))           # wave and surfer
    word = logo.crop((236, 764, 1312, 984))          # CALICOAN / SURF RETREAT

    # Stacked logo, trimmed to its content, for the footer.
    full = logo.crop(logo.getchannel("A").getbbox())
    for w in (360, 720):
        full.resize((w, round(full.height * w / full.width)), Image.LANCZOS).save(OUT / f"logo-full-{w}.png", optimize=True)
        full.resize((w, round(full.height * w / full.width)), Image.LANCZOS).save(OUT / f"logo-full-{w}.webp", quality=90)
    manifest["logo-full"] = {"widths": [360, 720], "width": full.width, "height": full.height}

    # Horizontal lockup for the header: the same mark and wordmark, side by side.
    H = 220
    m = mark.resize((round(mark.width * H / mark.height), H), Image.LANCZOS)
    wh = round(H * 0.62)
    wd = word.resize((round(word.width * wh / word.height), wh), Image.LANCZOS)
    gap = round(H * 0.16)
    lock = Image.new("RGBA", (m.width + gap + wd.width, H), (0, 0, 0, 0))
    lock.alpha_composite(m, (0, 0))
    lock.alpha_composite(wd, (m.width + gap, (H - wh) // 2 + 4))
    for h in (64, 128):
        w = round(lock.width * h / lock.height)
        r = lock.resize((w, h), Image.LANCZOS)
        r.save(OUT / f"logo-lockup-{h}.png", optimize=True)
        r.save(OUT / f"logo-lockup-{h}.webp", quality=92)
    manifest["logo-lockup"] = {"width": lock.width, "height": lock.height}

    # Favicons from the wave mark on a calm ivory disc so it reads at small sizes.
    side = max(mark.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
    fav_dir = OUT.parent / "favicon"
    fav_dir.mkdir(exist_ok=True)
    for size, name in ((180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")):
        bg = Image.new("RGBA", (size, size), (247, 243, 234, 255))
        pad = round(size * 0.08)
        bg.alpha_composite(sq.resize((size - 2 * pad, size - 2 * pad), Image.LANCZOS), (pad, pad))
        bg.convert("RGB").save(fav_dir / name, optimize=True)
    sq.resize((256, 256), Image.LANCZOS).save(
        fav_dir / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    sq.resize((32, 32), Image.LANCZOS).save(fav_dir / "favicon-32.png", optimize=True)
    return full


def build_og(full):
    """1200 x 630 share image: the Kubo sala photo beside the supplied logo."""
    W, H = 1200, 630
    canvas = Image.new("RGB", (W, H), (247, 243, 234))
    photo = ImageOps.exif_transpose(Image.open(source("I04"))).convert("RGB")
    pw = 660
    photo = ImageOps.fit(photo, (pw, H), Image.LANCZOS, centering=(0.5, 0.55))
    canvas.paste(photo, (0, 0))
    logo = full.copy()
    lw = 440
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    x = pw + (W - pw - lw) // 2
    y = (H - logo.height) // 2
    canvas.paste(logo, (x, y), logo)
    canvas.save(OUT / "og-image.jpg", quality=84, optimize=True)


def build_videos():
    for name, (key, start, dur) in VIDEOS.items():
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(dur), "-i", str(source(key)),
            "-vf", "scale=360:640:flags=lanczos,fps=30", "-c:v", "libx264", "-preset", "slow",
            "-crf", "27", "-profile:v", "main", "-pix_fmt", "yuv420p",
            "-af", f"afade=t=in:d=0.4,afade=t=out:st={dur - 1.2}:d=1.2", "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart",
            str(OUT / f"{name}.mp4")], check=True)
        print(f"video {name}: {(OUT / f'{name}.mp4').stat().st_size // 1024} KB")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.iterdir():
        old.unlink()
    with tempfile.TemporaryDirectory() as tmp:
        manifest = build_images(tmp)
    full = build_logo(manifest)
    build_og(full)
    build_videos()
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
