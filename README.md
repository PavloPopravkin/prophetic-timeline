# Prophetic Timeline

An immersive, cinematic interactive timeline for telling rich visual stories across history — from creation to eternity.

Build stunning timelines with parallax 3D scenes, animated panoramas, and a smooth scrollable timeline that expands as you explore.

![Prophetic Timeline](uploads/preview.jpg)

## Features

- **Panorama entry screen** — a rich illustrated world map where users click objects to zoom into specific eras
- **3D diorama scenes** — each timeline event is a fully layered parallax scene with foreground, midground and background elements
- **Smooth expandable timeline** — scroll to zoom in/out, drag to navigate, labels auto-hide to prevent overlap
- **Cosmic visual design** — deep space color palette with nebula lighting, glowing accents, and star fields
- **Detail panel** — expandable rich-text content panel for each scene
- **Object content panels** — individual objects in a scene can carry their own rich HTML content
- **Multilingual** — English and Ukrainian (easily extendable)
- **Mobile friendly** — responsive layout, touch-friendly timeline
- **Lazy loading** — panorama loads first so users can start browsing while scene images load in the background
- **Visual editor (Admin)** — drag-and-drop scene builder with live preview, parallax controls, and preset management

## Getting Started

```bash
npm install
npm start
```

Open [http://localhost:3000](http://localhost:3000) to view the timeline.  
Open [http://localhost:3000/admin.html](http://localhost:3000/admin.html) to edit content.

## Project Structure

```
prophetic-timeline/
├── index.html          # Frontend — timeline viewer
├── admin.html          # Visual content editor
├── server.js           # Express server + API
├── scenes.json         # Scene data (title, images, elements)
├── panorama.json       # Panorama entry screen data
├── uploads/            # Uploaded images (gitignored)
└── package.json
```

## Editor Guide

### Scenes Tab
- Create and order scenes on the **Scenes** tab
- Each scene has a **title**, **subtitle**, **date**, **year**, and a **background image**
- Add layered elements (images) with parallax, opacity, size, and position controls
- Elements can carry rich HTML content that appears in the detail panel

### Panorama Tab
- Set a full-screen background image for the entry panorama
- Add **image objects** (characters, illustrations) that float and react to hover
- Add **click zones** — invisible hotspots that navigate to a specific scene on click
- All objects are draggable directly on the canvas

### Presets
Multiple preset files (`scenes.*.json`, `panorama.*.json`) allow switching between completely different timeline collections without losing data.

## Customization

- **Colors** — the palette is CSS custom properties inside `index.html` (search for `#02010a`, `rgba(200,160,80`)
- **Translations** — extend the `TRANSLATIONS` object in `index.html` with new language keys
- **Timeline density** — adjust `MIN_LABEL_PX` in `index.html` to control how many labels show at default zoom

## Tech Stack

- **Three.js** (via ESM CDN) — 3D scene rendering and parallax
- **Vanilla JS** — no framework dependencies
- **Express** — lightweight Node.js backend for file uploads and JSON API
- **Multer** — image upload handling

## License

MIT
