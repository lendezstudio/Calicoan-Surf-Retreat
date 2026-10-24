"""Inventory supplied media: dimensions, video metadata, contact sheets and sample frames."""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

SRC = Path(__file__).resolve().parent.parent / "Initial Assets"
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

imgs = sorted(p for p in SRC.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
vids = sorted(p for p in SRC.iterdir() if p.suffix.lower() == ".mp4")

info = {}
for i, p in enumerate(imgs):
    with Image.open(p) as im:
        info[f"I{i:02d}"] = {"file": p.name, "size": im.size, "mode": im.mode}

for i, p in enumerate(vids):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate",
                        "-of", "json", str(p)], capture_output=True, text=True)
    meta = json.loads(r.stdout)
    dur = float(meta["format"]["duration"])
    info[f"V{i}"] = {"file": p.name, "meta": meta}
    for k, t in enumerate([0.5, dur * 0.25, dur * 0.5, dur * 0.75, max(dur - 0.5, 0)]):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(p),
                        "-frames:v", "1", "-vf", "scale=360:-2", str(OUT / f"V{i}_f{k}.jpg")])

print(json.dumps(info, indent=1))

def sheet(entries, name, cell=300, cols=4):
    rows = (len(entries) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell, rows * (cell + 24)), "white")
    d = ImageDraw.Draw(canvas)
    for n, (label, path) in enumerate(entries):
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((cell - 8, cell - 8))
            x, y = (n % cols) * cell, (n // cols) * (cell + 24)
            canvas.paste(im, (x + 4, y + 4))
            d.text((x + 6, y + cell + 4), label, fill="black")
    canvas.save(OUT / name, quality=85)

keys = [k for k in info if k.startswith("I")]
for s in range(0, len(keys), 12):
    sheet([(k, SRC / info[k]["file"]) for k in keys[s:s + 12]], f"sheet_{s // 12}.jpg")
frames = sorted(OUT.glob("V*_f*.jpg"))
sheet([(f.stem, f) for f in frames], "sheet_video.jpg", cell=240, cols=5)
