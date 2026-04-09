---
name: uuk-timeline
version: 1.0.0
description: CLI harness for the uuk-timeline Prophetic Timeline web application
command: uuk-timeline
install: pip install -e /Users/pavlopopravkin/www/uuk-timeline/agent-harness/
server_default: http://localhost:3000
---

# uuk-timeline CLI

Control the Prophetic Timeline web application programmatically.
Server must be running: `npm start` in the project directory.

## Quick start

```bash
# Check server is up
uuk-timeline scenes list

# Or point at a different server
uuk-timeline --server http://localhost:3000 scenes list
```

## Command reference

### Scenes

```bash
# Get full scenes document
uuk-timeline scenes get

# List scene ids + titles
uuk-timeline scenes list

# Replace entire scenes document from file
uuk-timeline scenes set path/to/scenes.json

# Add a new scene (appended, auto-assigned ID)
uuk-timeline scene add \
  --title "Благовещение" \
  --subtitle "Архангел Гавриил возвещает Марии" \
  --date "~7–5 лет до н.э." \
  --year "Благовест." \
  --bg "/uploads/вариации_2K_202603191339-2.jpg" \
  --night

# Update fields of an existing scene (by id)
uuk-timeline scene update 5 --title "Новый заголовок" --night

# Delete a scene
uuk-timeline scene delete 5

# Reorder all scenes (provide all IDs in order)
uuk-timeline scene reorder 0 1 2 5 3 4

# Get one scene
uuk-timeline scene get 5
```

### Elements (within a scene)

```bash
# List elements in scene 5
uuk-timeline element list 5

# Add image element to scene 5
uuk-timeline element add-image 5 \
  --src "/uploads/0009.png" \
  --x 0.28 \
  --bottom 0.0 \
  --h 78 \
  --parallax 1.2 \
  --anim float \
  --content "<h3>Ангел</h3><p>Посланник Бога.</p>"

# Add text element to scene 5
uuk-timeline element add-text 5 \
  --text "Благовещение" \
  --font "'Cormorant Garamond', serif" \
  --size 6 \
  --weight 300 \
  --italic \
  --color "#f0d880" \
  --shadow "0 0 30px rgba(240,200,80,0.5),0 2px 20px rgba(0,0,0,0.9)" \
  --x 0.5 \
  --bottom 0.72

# Add element from raw JSON string
uuk-timeline element add-json 5 '{"src":"/uploads/0012.png","x":0.68,"h":45,"bottom":0.2,"parallax":0.8,"anim":"zoom"}'

# Update element fields (merge patch by index)
uuk-timeline element update 5 0 '{"x": 0.3, "h": 80}'

# Delete element at index 2 in scene 5
uuk-timeline element delete 5 2
```

### Panorama

```bash
# Get panorama
uuk-timeline panorama get

# Replace entire panorama from file
uuk-timeline panorama set path/to/panorama.json

# Change background
uuk-timeline panorama set-background "/uploads/вариации_2K_202603191339-2.jpg"

# Add a visual element
uuk-timeline panorama add-element \
  --id "elem-cross" \
  --src "/uploads/0015.png" \
  --x 55 --y 12 \
  --width 16 \
  --scene-id 27 \
  --anim zoom

# Remove element by id
uuk-timeline panorama remove-element elem-cross

# Add invisible click area
uuk-timeline panorama add-clickarea \
  --scene-id 27 \
  --x 50 --y 5 \
  --width 18 --height 38

# Remove click area by scene id
uuk-timeline panorama remove-clickarea 27
```

### Presets

```bash
uuk-timeline presets list
uuk-timeline presets load humanity
uuk-timeline presets save my-draft
```

### Library & Upload

```bash
# List uploaded images
uuk-timeline library list

# Upload a new image
uuk-timeline upload /path/to/image.png
# Returns: {"path": "/uploads/filename.png", ...}
```

### Bulk apply

```bash
# Apply a complete timeline + panorama in one call
uuk-timeline apply-json timeline.json

# Via stdin
cat timeline.json | uuk-timeline apply-json --stdin
```

The bulk JSON format:
```json
{
  "scenes": { "name": "...", "scenes": [...] },
  "panorama": { "name": "...", "background": "...", "elements": [...], "clickAreas": [...] },
  "preset_save": "my-snapshot"
}
```

## Key data rules (from AGENT_INSTRUCTIONS.md)

### Image element coordinates
- `x`: 0–1 float. Left object ~0.15–0.30, center ~0.45–0.55, right ~0.65–0.80
- `bottom`: 0–1 float. Ground level = 0–0.05. Flying/celestial = 0.2–0.5
- `h`: 0–100 (% of scene height). Main object ~70–90, medium ~50–65, small decor ~25–45
- `parallax`: 0–2. Foreground ~1.0–1.5, background ~0–0.5, text ~0.3–0.6

### Text element
- `fontSize`: vh units (% of screen height). Title: 5–8, body: 2.5–4
- `maxWidth`: 0 = single line auto-width; >0 = wrapped block in vw units
- When `maxWidth > 0`, use `textAlign: "center"` by default
- Default spawn: `x: 0.5`, `bottom: 0.62`

### Panorama coordinates
- All in **percent (0–100)**, not 0–1 floats
- `x`, `y`: center of element
- `width`: element width in vh%
- `clickAreas` `x`, `y`: top-left corner of invisible rectangle

### Available backgrounds
- `/uploads/вариации_2K_202603191339-2.jpg` — dark/mysterious/night
- `/uploads/вариации_2K_202603191339.jpg` — deep dark, Golgotha
- `/uploads/вариации_2K_202603191339-3.jpg` — light/nature/life
- `/uploads/1775333598203_GrehGorBG.png` — mountain/mystic

### Main image assets
`/uploads/0001.png`–`/uploads/0020.png` — numbered thematic objects
`/uploads/3D Glass Flowers (1).png`–`(25).png` — decorative foreground flowers

## Cyrillic fonts (CSS font-family values)

```
Georgia, serif
'PT Serif', serif
'Lora', serif
'Merriweather', serif
'Philosopher', serif
'Cormorant Garamond', serif
'EB Garamond', serif
'Spectral', serif
'Crimson Text', serif
'Playfair Display', serif
'Roboto', sans-serif
'PT Sans', sans-serif
'Montserrat', sans-serif
'Nunito', sans-serif
'Exo 2', sans-serif
'Comfortaa', cursive
'Golos Text', sans-serif
'Russo One', sans-serif
'Yeseva One', serif
'Unbounded', sans-serif
'Oswald', sans-serif
```

## Text shadow presets

```
"0 2px 16px rgba(0,0,0,0.9),0 0 40px rgba(0,0,0,0.7)"         dark glow (default)
"0 0 30px rgba(240,200,80,0.5),0 2px 20px rgba(0,0,0,0.9)"     gold glow
"0 1px 3px rgba(0,0,0,0.8)"                                      subtle
"0 0 20px rgba(255,255,255,0.4),0 2px 12px rgba(0,0,0,0.8)"     white glow
```
