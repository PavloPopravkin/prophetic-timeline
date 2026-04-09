# UUK-TIMELINE CLI — Software-Specific SOP

## What Is This

`uuk-timeline` is a CLI harness for the **Prophetic Timeline** web application — an
interactive 3D panorama + horizontal timeline built with Three.js.

The "backend" here is the timeline's own REST API served at `http://localhost:3000`.
All CLI operations translate to GET/PUT/POST calls against that API.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    uuk-timeline CLI                               │
│   click commands → APIClient → REST API → server.js → JSON files  │
└──────────────────────────────────────────────────────────────────┘
```

### Data files on the server
| File | Purpose |
|------|---------|
| `scenes.json` | Active timeline (all scenes) |
| `panorama.json` | Active panorama (intro screen) |
| `scenes.<name>.json` | Saved preset |
| `panorama.<name>.json` | Saved panorama preset |

### REST API endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/scenes` | Get full scenes document |
| PUT | `/api/scenes` | Replace full scenes document |
| GET | `/api/panorama` | Get full panorama document |
| PUT | `/api/panorama` | Replace full panorama document |
| GET | `/api/presets` | List preset names |
| POST | `/api/presets/:name/load` | Load a preset |
| POST | `/api/presets/:name/save` | Save current state as preset |
| GET | `/api/library` | List uploaded image files |
| POST | `/api/upload` | Upload image (multipart) |

## Data Model

### Scene

Each scene has an `elements` array containing image and text objects.

**Image element** — referenced by `src` path, positioned by `x` (0–1) and `bottom` (0–1).

**Text element** — `type: "text"`, positioned the same way. Rendered as a CSS div overlay
in the viewer with parallax scaling matching the image meshes.

### Panorama

Intro screen with two layers:
- `elements` — visible objects with animation (`float` or `zoom`)  
- `clickAreas` — invisible rectangles that navigate to a scene on click

All panorama coordinates are **percent (0–100)**, not 0–1 floats.

## CLI Command Groups

| Group | Commands |
|-------|----------|
| `scenes` | `get`, `list`, `set` |
| `scene` | `get`, `add`, `update`, `delete`, `reorder` |
| `element` | `list`, `add-image`, `add-text`, `add-json`, `update`, `delete` |
| `panorama` | `get`, `set`, `set-background`, `add-element`, `remove-element`, `add-clickarea`, `remove-clickarea` |
| `presets` | `list`, `load`, `save` |
| `library` | `list` |
| `upload` | (top-level) |
| `apply-json` | (top-level, bulk operation) |

## Agent Workflow — Complete Timeline

```bash
# 1. Start server (must be running)
#    cd /Users/pavlopopravkin/www/uuk-timeline && npm start

# 2. Create scenes
uuk-timeline scene add --title "В начале" --year "Вечность" --night
# → returns JSON with the new scene's id

# 3. Add elements
uuk-timeline element add-image 0 \
  --src "/uploads/0001.png" --x 0.5 --h 80 --parallax 1.2

uuk-timeline element add-text 0 \
  --text "В начале было Слово" \
  --font "'Cormorant Garamond', serif" \
  --size 7 --weight 300 --italic \
  --color "#f0d880" \
  --shadow "0 0 30px rgba(240,200,80,0.5),0 2px 20px rgba(0,0,0,0.9)"

# 4. Set panorama
uuk-timeline panorama set-background "/uploads/вариации_2K_202603191339-2.jpg"
uuk-timeline panorama add-element \
  --id "elem-word" --src "/uploads/0001.png" \
  --x 15 --y 30 --width 12 --scene-id 0 --anim float
uuk-timeline panorama add-clickarea \
  --scene-id 0 --x 8 --y 15 --width 18 --height 35

# 5. Save as preset
uuk-timeline presets save my-timeline
```

## Bulk JSON Format

Agents can push an entire timeline in one call using `apply-json`:

```json
{
  "scenes": {
    "name": "My Timeline",
    "scenes": [...]
  },
  "panorama": {
    "name": "My Panorama",
    "background": "/uploads/вариации_2K_202603191339-2.jpg",
    "elements": [...],
    "clickAreas": [...]
  },
  "preset_save": "my-snapshot"
}
```

```bash
cat my-timeline.json | uuk-timeline apply-json --stdin
```
