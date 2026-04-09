#!/usr/bin/env python3
"""
Autonomous scene builder for uuk-timeline.

Searches free stock images, downloads them, removes backgrounds,
and assembles a complete scene in scenes.json.

USAGE:
    python3 build_scene.py "Angel appearing to Abraham" --scenes 1
    python3 build_scene.py "Noah's Ark" --scenes 2 --dry-run
    python3 build_scene.py "Crucifixion at Golgotha" --model isnet-general-use

REQUIREMENTS:
    - Server running: npm start
    - API key set:    export PEXELS_API_KEY=your_key_here
                      (or PIXABAY_API_KEY for Pixabay)
    - rembg + onnxruntime installed for cutout
"""

import sys, os, json, time, argparse, urllib.request, urllib.parse

SERVER   = os.environ.get("UUK_SERVER", "http://localhost:3000")
ADMIN    = os.environ.get("UUK_ADMIN_USER", "timelineAdmin")
PASSWD   = os.environ.get("UUK_ADMIN_PASS", "hwbUNWHqR9N4mT")

import base64
AUTH = "Basic " + base64.b64encode(f"{ADMIN}:{PASSWD}".encode()).decode()


# ── HTTP helpers ─────────────────────────────────────────────

def _req(method, path, body=None):
    url = SERVER + path
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type",  "application/json")
    req.add_header("Authorization", AUTH)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())

def get(path):    return _req("GET",  path)
def put(path, b): return _req("PUT",  path, b)
def post(path, b=None): return _req("POST", path, b)


# ── Steps ────────────────────────────────────────────────────

def search_images(query, source="pexels", per_page=12):
    """Search stock photos. Returns list of result dicts."""
    q = urllib.parse.quote(query)
    data = get(f"/api/image-search?q={q}&source={source}&per_page={per_page}")
    return data.get("results", [])


def fetch_image(url, name=""):
    """Download remote image to uploads. Returns server path."""
    result = post("/api/image-fetch", {"url": url, "filename": name})
    return result["path"]


def cutout(src, model="u2net", points="", rect=""):
    """AI background removal. Returns server path of WebP result."""
    result = post("/api/remove-bg", {"src": src, "model": model, "points": points, "rect": rect})
    return result["path"]


def get_scenes():
    return get("/api/scenes")


def save_scenes(doc):
    return put("/api/scenes", doc)


# ── Main builder ─────────────────────────────────────────────

# Default backgrounds available on the server
BACKGROUNDS = [
    "/uploads/вариации_2K_202603191339-2.jpg",   # dark, night
    "/uploads/вариации_2K_202603191339-3.jpg",   # light, nature
    "/uploads/вариации_2K_202603191339.jpg",      # dark depth
]

def build(
    prompt: str,
    *,
    num_scenes: int  = 1,
    source: str      = "pexels",
    model: str       = "u2net",
    dry_run: bool    = False,
    bg: str          = "",
    night: bool      = None,       # None = auto-detect from prompt
    verbose: bool    = True,
):
    """
    Build `num_scenes` new scenes from a text prompt.

    Steps per scene:
      1. Search for 2 subject images (main + secondary)
      2. Download both
      3. Remove backgrounds
      4. Compose scene JSON
      5. Append to scenes.json (unless dry_run)

    Returns list of composed scene dicts.
    """

    def log(msg):
        if verbose: print(f"  {msg}", flush=True)

    # Auto-detect night mode
    if night is None:
        dark_words = {"night", "dark", "cross", "death", "tomb", "crucif", "exile",
                      "flood", "judgment", "plague", "desert", "babylon", "ночь", "тьма"}
        night = any(w in prompt.lower() for w in dark_words)

    chosen_bg = bg or (BACKGROUNDS[0] if night else BACKGROUNDS[1])

    print(f"\n🔍  Searching: «{prompt}» [{source}]")
    results = search_images(prompt, source=source, per_page=15)
    if not results:
        print("❌  No images found. Check API key or try a different query.")
        return []

    log(f"Found {len(results)} images")

    # Pick best: prefer portrait/tall for main subject, landscape for background feel
    portraits   = [r for r in results if r["height"] >= r["width"] * 0.9]
    landscapes  = [r for r in results if r not in portraits]
    ordered     = (portraits + landscapes)[:10]

    new_scenes = []

    for scene_n in range(num_scenes):
        offset   = scene_n * 2
        main_res = ordered[offset % len(ordered)]
        sec_res  = ordered[(offset + 1) % len(ordered)] if len(ordered) > 1 else None

        print(f"\n📥  Downloading image 1/2: {main_res['description'][:60]}")
        main_src = fetch_image(main_res["url"], name=f"main_{scene_n}")
        log(f"→ {main_src}")

        print(f"✂️   Cutting out background …")
        main_cut = cutout(main_src, model=model)
        log(f"→ {main_cut}")

        sec_cut = None
        if sec_res:
            print(f"📥  Downloading image 2/2: {sec_res['description'][:60]}")
            sec_src = fetch_image(sec_res["url"], name=f"sec_{scene_n}")
            log(f"→ {sec_src}")
            print(f"✂️   Cutting out background …")
            try:
                sec_cut = cutout(sec_src, model=model)
                log(f"→ {sec_cut}")
            except Exception as e:
                log(f"⚠ secondary cutout failed: {e}")

        # Compose scene
        title = prompt.title()
        year_label = prompt[:10].title()

        elements = []

        # Main subject — left of center, large
        elements.append({
            "src":      main_cut,
            "x":        0.28,
            "bottom":   0.0,
            "h":        80,
            "parallax": 1.2,
            "anim":     "float",
            "content":  f"<h3>{title}</h3><p>Source: {main_res.get('author','')} / {main_res.get('source','')}</p>",
        })

        # Secondary subject — right of center, medium
        if sec_cut:
            elements.append({
                "src":      sec_cut,
                "x":        0.72,
                "bottom":   0.0,
                "h":        60,
                "parallax": 0.9,
                "anim":     "float",
            })

        # Title text
        elements.append({
            "type":        "text",
            "text":        title,
            "font":        "'Cormorant Garamond', serif",
            "fontSize":    5.5,
            "fontWeight":  300,
            "fontStyle":   "italic",
            "color":       "#f0d880" if night else "#3a2a10",
            "opacity":     0.9,
            "textAlign":   "center",
            "letterSpacing": 0.12,
            "lineHeight":  1.2,
            "textShadow":  "0 0 30px rgba(240,200,80,0.5),0 2px 20px rgba(0,0,0,0.9)"
                           if night else "0 1px 8px rgba(0,0,0,0.4)",
            "textTransform": "",
            "maxWidth":    0,
            "x":           0.5,
            "bottom":      0.75,
            "parallax":    0.4,
        })

        scene = {
            "title":    title,
            "subtitle": f"Source: {main_res.get('author','')} / {source}",
            "date":     "",
            "year":     year_label,
            "bg":       chosen_bg,
            "night":    night,
            "elements": elements,
        }
        new_scenes.append(scene)
        print(f"✅  Scene «{title}» composed ({len(elements)} elements)")

    if dry_run:
        print("\n[dry-run] Would append scenes:")
        print(json.dumps(new_scenes, ensure_ascii=False, indent=2))
        return new_scenes

    # Append to existing scenes.json
    doc    = get_scenes()
    scenes = doc.get("scenes", [])
    next_id = max((s.get("id", i) for i, s in enumerate(scenes)), default=-1) + 1
    for i, s in enumerate(new_scenes):
        s["id"] = next_id + i
        scenes.append(s)
    doc["scenes"] = scenes
    save_scenes(doc)
    print(f"\n🎬  {len(new_scenes)} scene(s) added to timeline. Total scenes: {len(scenes)}")
    return new_scenes


# ── CLI entrypoint ────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Build timeline scenes from stock images + AI cutout.")
    p.add_argument("prompt",                         help="What to search for (in English)")
    p.add_argument("--scenes",   type=int, default=1, help="Number of scenes to create (default 1)")
    p.add_argument("--source",   default="pexels",   choices=["pexels","pixabay"], help="Image API")
    p.add_argument("--model",    default="u2net",
                   choices=["u2net","u2net_human_seg","isnet-general-use","silueta"],
                   help="AI cutout model")
    p.add_argument("--bg",       default="",         help="Override background image path")
    p.add_argument("--night",    action="store_true", default=None, help="Force night mode")
    p.add_argument("--dry-run",  action="store_true", help="Print JSON without saving")
    p.add_argument("--server",   default="",          help="Override server URL")
    args = p.parse_args()

    if args.server:
        SERVER = args.server

    build(
        args.prompt,
        num_scenes = args.scenes,
        source     = args.source,
        model      = args.model,
        bg         = args.bg,
        night      = args.night,
        dry_run    = args.dry_run,
    )
