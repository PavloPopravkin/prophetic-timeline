# Background Removal Tool — Agent Guide

## What it does
Cuts the main subject from any image (any background) using AI.
Output: WebP with transparency (RGBA). ~1.2–2s per image.

## Script
`remove_bg.py` in project root.

---

## Basic usage

```bash
# Auto — AI picks the main subject
python3 remove_bg.py uploads/photo.jpg
# → uploads/photo_no_bg.webp

# Explicit output path
python3 remove_bg.py uploads/photo.jpg -o uploads/result.webp

# Batch
python3 remove_bg.py uploads/*.jpg
python3 remove_bg.py uploads/*.png
```

---

## Models

| Model | Use when | Speed |
|-------|----------|-------|
| `u2net` | Default. Any subject. | fast |
| `u2net_human_seg` | Photo has a person/portrait | fast |
| `isnet-general-use` | Need sharper edges (hair, fur) | slower |
| `silueta` | Simple subjects, speed priority | fastest |
| `sam` | Need to pick a SPECIFIC object by clicking | slow |

```bash
python3 remove_bg.py photo.jpg --model u2net_human_seg
python3 remove_bg.py photo.jpg --model isnet-general-use
```

---

## SAM — pick a specific object

Use when the image has multiple objects and auto-detection picks the wrong one.
Provide coordinates in pixels.

```bash
# Click a point ON the object you want to keep
python3 remove_bg.py photo.jpg --point 450,600

# Add background hint (label=0 means "this is background, remove it")
python3 remove_bg.py photo.jpg --point 450,600 --point 800,100,0

# Bounding box around the object [x1,y1,x2,y2]
python3 remove_bg.py photo.jpg --rect 100,50,800,1100

# Most precise: box + center point
python3 remove_bg.py photo.jpg --rect 100,50,800,1100 --point 450,600
```

**How to get pixel coordinates:**
- Open the image in any viewer → hover over the object → note x,y
- Or estimate: if image is 896×1200, center is ~448,600

---

## Performance

| Metric | Value |
|--------|-------|
| Time per image | ~1.2–2s |
| RAM | ~5–6 MB |
| Model download | 176 MB once, cached to `~/.u2net/` |
| Compression | PNG 3.7 MB → WebP 65–150 KB (20–50×) |

---

## Output

Always WebP (RGBA). Use directly in scenes.json:
```json
{ "src": "uploads/photo_no_bg.webp", "x": 0.5, "bottom": 0.3 }
```

---

## Decision guide

```
Has a person?           → --model u2net_human_seg
Need fine edges?        → --model isnet-general-use
Multiple objects?       → --point X,Y  (SAM, click the one you want)
Everything else?        → default (u2net), no flags needed
```
