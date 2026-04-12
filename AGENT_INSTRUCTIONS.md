# Agent Instructions: Prophetic Timeline

## About the Project

An interactive diorama-timeline. Two screens:

1. **Panorama** — entry screen: background + clickable objects, each leading to a scene
2. **Timeline** — horizontal reel of 3D scenes, navigated by swipe/arrows

Start server: `npm start` in `/Users/pavlopopravkin/www/uuk-timeline/`
Admin: `http://localhost:3000/admin` → project picker (then choose a project to edit)
Editor: `http://localhost:3000/admin/editor`
Preview: `http://localhost:3000`

---

## Project / Preset System

Each **project** is a separate named timeline stored as `scenes.<name>.json` and `panorama.<name>.json`. The active working copy is always `scenes.json` / `panorama.json`.

**Workflow:**
1. Visit `/admin` → choose a project card → loads it into `scenes.json` → opens `/admin/editor`
2. Edit scenes and panorama in the editor
3. Press **Save** to persist changes to `scenes.json`
4. Project selection is remembered per-browser via `localStorage`

**API:**
```
GET    /api/presets                    List all projects (name, title, sceneCount, thumb)
POST   /api/presets/:name/load         Copy scenes.<name>.json → scenes.json (activates project)
POST   /api/presets/:name/save         Copy scenes.json → scenes.<name>.json (snapshot)
POST   /api/presets/:name/create       Create new project (copies current scenes.json as starting point)
DELETE /api/presets/:name              Delete project files
```

**Creating a new project via CLI:**
```bash
curl -X POST http://localhost:3000/api/presets/my_project/create \
  -u timelineAdmin:hwbUNWHqR9N4mT
# Then load it:
curl -X POST http://localhost:3000/api/presets/my_project/load \
  -u timelineAdmin:hwbUNWHqR9N4mT
```

---

## CLI for Agents

A `uuk-timeline` CLI tool is installed for managing the timeline without a browser.
Full docs: `agent-harness/cli_anything/uuk_timeline/skills/SKILL.md`

All commands return JSON. Use `--server URL` for a non-default server address.

---

## Data Files

| File | Purpose |
|------|---------|
| `scenes.json` | Active scene set (working copy) |
| `panorama.json` | Active panorama (working copy) |
| `scenes.<name>.json` | Saved project snapshot |
| `panorama.<name>.json` | Saved panorama snapshot for that project |

---

## `scenes.json` Structure

```json
{
  "name": "Project title",
  "scenes": [ /* array of scenes */ ]
}
```

### Scene fields

```json
{
  "id": 0,
  "title": "Scene heading",
  "subtitle": "Quote or short description",
  "date": "Date or period (free text)",
  "year": "Timeline label — max 8–10 chars",
  "bg": "/uploads/background.jpg",
  "bg_video": "https://www.youtube.com/watch?v=XXXXXXXXXXX",
  "night": true,
  "elements": [ /* array of elements */ ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | number | Sequential index (0, 1, 2…) |
| `title` | string | Large heading shown on screen |
| `subtitle` | string | Quote or description |
| `date` | string | Full date / period |
| `year` | string | Short timeline label |
| `bg` | string | Path to background image |
| `bg_video` | string | YouTube URL — overrides `bg` if set |
| `night` | boolean | `true` = dark scene with stars |
| `elements` | array | All scene objects (images and texts) |

> If `bg_video` is set, `bg` is ignored.

---

## Scene Elements (`elements`)

Two types: **image** (default) and **text** (`type: "text"`).

### Image

```json
{
  "src": "/uploads/0009.png",
  "x": 0.35,
  "bottom": 0.05,
  "h": 75,
  "w": 0,
  "parallax": 1.0,
  "flip": false,
  "softEdge": 0,
  "anim": "float",
  "content": "<h3>Title</h3><p>HTML shown on click</p>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `src` | string | Path to PNG/JPG |
| `x` | 0–1 | Horizontal anchor: 0 = left edge, 1 = right edge |
| `bottom` | 0–1 | Bottom offset as fraction of scene height (0 = ground, 0.5 = middle) |
| `h` | 0–100 | Height as % of scene height; 0 = auto |
| `w` | 0–100 | Width as % of scene width; 0 = auto |
| `parallax` | 0–2 | Parallax scaling strength on scroll (0 = none, 1 = normal, 2 = strong) |
| `flip` | boolean | Horizontal mirror |
| `softEdge` | 0–100 | Edge feathering (0 = none) |
| `anim` | string | `"float"` = bobbing animation, otherwise static |
| `content` | string | HTML content for detail panel on click (optional) |

**Positioning rules:**
- `x`: left object ~0.15–0.30, center ~0.45–0.55, right ~0.65–0.80. Avoid edges (0.0 or 1.0) — will be clipped.
- `bottom`: main figures at ground → 0–0.05. Flying/sky objects → 0.2–0.5.
- `h`: main object ~70–90, medium ~50–65, small decor ~25–45.
- `parallax`: foreground objects → 1.0–1.5. Background/decorative → 0–0.5.

### Text (`type: "text"`)

```json
{
  "type": "text",
  "text": "Text displayed on scene",
  "font": "Georgia, serif",
  "fontSize": 4,
  "fontWeight": 400,
  "fontStyle": "normal",
  "color": "#f5e6c8",
  "opacity": 1,
  "textAlign": "left",
  "letterSpacing": 0.05,
  "lineHeight": 1.2,
  "textShadow": "0 2px 16px rgba(0,0,0,0.9),0 0 40px rgba(0,0,0,0.7)",
  "textTransform": "",
  "maxWidth": 0,
  "x": 0.5,
  "bottom": 0.62,
  "parallax": 0.4
}
```

| Field | Type | Description |
|-------|------|-------------|
| `fontSize` | number | Font size in vh % |
| `maxWidth` | number | 0 = single line (auto width); >0 = block width in vw with wrapping |
| `textShadow` | string | CSS text-shadow value |
| `textTransform` | string | `"uppercase"`, `"capitalize"`, or `""` |
| `parallax` | 0–2 | Texts typically 0.3–0.6 to move less than images |

---

## `panorama.json` Structure

```json
{
  "name": "Panorama title",
  "background": "/uploads/bg.jpg",
  "elements": [
    { "id": "el1", "src": "/uploads/obj.png", "x": 30, "y": 20, "width": 15, "sceneId": 2, "anim": "float" }
  ],
  "clickAreas": [
    { "sceneId": 2, "x": 25, "y": 15, "width": 25, "height": 40 }
  ]
}
```

All coordinates in percent (0–100). `elements` = visible objects; `clickAreas` = invisible click regions.

---

## Full API Reference

```
GET    /api/scenes                     Get active scenes
PUT    /api/scenes                     Replace active scenes
       Body: { "name": "...", "scenes": [...] }

GET    /api/panorama                   Get active panorama
PUT    /api/panorama                   Replace active panorama
       Body: { "name": "...", "background": "...", "elements": [...], "clickAreas": [...] }

GET    /api/presets                    List all projects
POST   /api/presets/:name/load         Activate project
POST   /api/presets/:name/save         Snapshot current state to project
POST   /api/presets/:name/create       Create new project
DELETE /api/presets/:name              Delete project

GET    /api/library                    List uploaded images
POST   /api/upload                     Upload image
       Body: multipart/form-data, field "file"
POST   /api/delete-upload              Delete uploaded file
       Body: { "path": "/uploads/..." }

GET    /api/image-search               Search stock images
       ?q=angel&source=pexels&per_page=12
       source: "pexels" (needs PEXELS_API_KEY) | "pixabay" (needs PIXABAY_API_KEY)
       Returns: { results: [{ id, url, thumb, width, height, description, author, page_url }] }

POST   /api/image-fetch                Download image by URL to uploads
       Body: { "url": "https://...", "filename": "optional_name" }
       Returns: { ok: true, path: "/uploads/..." }

POST   /api/remove-bg                  AI background removal
       Body: { "src": "/uploads/...", "model": "u2net", "points": "", "rect": "" }
       Models: u2net, u2net_human_seg, isnet-general-use, silueta
       Returns: { path: "/uploads/..._no_bg_timestamp.webp" }

POST   /api/save-svg                   Save modified SVG
       Body: { "content": "<svg>...</svg>", "originalPath": "/uploads/..." }
```

All write endpoints require HTTP Basic Auth (credentials in `.env` or server defaults).

---

## Available Images in `/uploads/`

- `0001.png`–`0020.png` — symbolic objects (Word, Radiance, Water, Plant, Cloud, Temple, Planet, Person, Angel, Tablets, Fire, Star, Tree, Prophet, Cross, Resurrection, Spirit, City, Book, New World)
- `3D Glass Flowers (1).png`–`(25).png` — decorative glass flowers
- Named files: AdamEve, Greh, Jerusalem, landscapes, layers
- Backgrounds: `вариации_2K_202603191339-2.jpg` (night/mystery), `…-1.jpg` (dark depth), `…-3.jpg` (light/nature), `GrehGorBG.png` (mountain/mystique)

---

## Autonomous Scene Creation

```bash
python3 build_scene.py "Angel appearing to shepherd"   # single scene
python3 build_scene.py "Noah's flood" --scenes 3       # multiple scenes
python3 build_scene.py "Crucifixion" --dry-run         # without saving
```

Or step-by-step:
```bash
uuk-timeline image search "angel"
uuk-timeline image fetch <url>
uuk-timeline image cutout /uploads/angel.png
uuk-timeline scene add --title "Annunciation" --year "Annun."
uuk-timeline element add-image 5 --src /uploads/angel_no_bg.webp --x 0.5 --h 80
```

---

## Tips

1. `elements` is a single array — order = draw order (first = farthest back)
2. `parallax`: background 0–0.5, midground 0.8–1.2, foreground 1.5–2.0, text 0.3–0.6
3. `night: true` — adds stars; use for dark/mysterious scenes
4. `bg_video` overrides `bg`
5. `maxWidth: 0` = single line; `maxWidth: 35` = 35vw block with word-wrap
6. Panorama: use both `elements` (visible) + `clickAreas` (invisible) for each entry point
7. `year` on timeline — max 8–10 characters
8. Decorative flowers: put at start/end of `elements`, `x` near edges (0.02–0.12 or 0.82–0.95)
