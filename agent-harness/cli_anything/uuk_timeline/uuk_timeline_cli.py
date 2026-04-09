#!/usr/bin/env python3
"""
CLI harness for uuk-timeline — Prophetic Timeline web application.

Allows agents to create and manage timelines and panoramas
via the REST API without using the browser admin UI.

Usage:
    uuk-timeline [--server URL] [--json] COMMAND [ARGS]

Examples:
    uuk-timeline scenes get
    uuk-timeline scene add --title "Рождество" --year "Рожд." --bg /uploads/0001.png
    uuk-timeline panorama get
"""

import json
import shlex
import sys
import click

from cli_anything.uuk_timeline.core import APIClient, APIError

try:
    from cli_anything.uuk_timeline.utils.repl_skin import ReplSkin
    _skin = ReplSkin("uuk-timeline", version="1.0.0")
except Exception:
    _skin = None


# ---------------------------------------------------------------------------
# Shared context
# ---------------------------------------------------------------------------

pass_client = click.make_pass_decorator(APIClient)


def out(data, as_json: bool = True):
    """Print data as JSON."""
    click.echo(json.dumps(data, ensure_ascii=False, indent=2))


def err(msg: str):
    click.echo(f"Error: {msg}", err=True)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.option("--server", default="http://localhost:3000", envvar="UUK_SERVER",
              show_default=True, help="Timeline server base URL.")
@click.pass_context
def cli(ctx, server):
    """uuk-timeline agent CLI — manage timelines and panoramas."""
    ctx.ensure_object(dict)
    ctx.obj = APIClient(server)
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.command(hidden=True)
@pass_client
def repl(client):
    """Interactive REPL mode (default when no subcommand given)."""
    if _skin:
        _skin.print_banner()
    else:
        click.echo("uuk-timeline v1.0.0 — type 'help' or a command, 'exit' to quit")

    try:
        if _skin:
            pt_session = _skin.create_prompt_session()
        else:
            pt_session = None
    except Exception:
        pt_session = None

    while True:
        try:
            if _skin and pt_session:
                line = _skin.get_input(pt_session, project_name="timeline")
            else:
                line = input("uuk-timeline> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not line or line.startswith("#"):
            continue
        if line in ("exit", "quit", "q"):
            break
        if line == "help":
            click.echo(cli.get_help(click.Context(cli)))
            continue

        try:
            args = shlex.split(line)
            # Re-invoke the CLI in standalone mode so REPL commands work
            cli.main(args=args, obj=client, standalone_mode=False)
        except SystemExit:
            pass
        except Exception as e:
            if _skin:
                _skin.error(str(e))
            else:
                click.echo(f"Error: {e}", err=True)

    if _skin:
        _skin.print_goodbye()
    else:
        click.echo("Bye.")


# ===========================================================================
# SCENES
# ===========================================================================

@cli.group()
def scenes():
    """Manage the active timeline (scenes.json)."""


@scenes.command("get")
@pass_client
def scenes_get(client):
    """Get the full scenes document."""
    try:
        data = client.get("/api/scenes")
        out(data, True)
    except APIError as e:
        err(str(e))


@scenes.command("set")
@click.argument("json_file", required=False)
@click.option("--stdin", is_flag=True, help="Read JSON from stdin.")
@pass_client
def scenes_set(client, json_file, stdin):
    """Replace the entire scenes document. Provide a JSON file or --stdin."""
    if stdin:
        raw = sys.stdin.read()
    elif json_file:
        with open(json_file, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        err("Provide a JSON file path or --stdin")
        return
    try:
        body = json.loads(raw)
        result = client.put("/api/scenes", body)
        out(result or {"ok": True}, True)
    except json.JSONDecodeError as e:
        err(f"Invalid JSON: {e}")
    except APIError as e:
        err(str(e))


@scenes.command("list")
@pass_client
def scenes_list(client):
    """List all scenes with id, year, title."""
    try:
        data = client.get("/api/scenes")
        rows = [
            {"id": s.get("id"), "year": s.get("year", ""), "title": s.get("title", "")}
            for s in data.get("scenes", [])
        ]
        out(rows, True)
    except APIError as e:
        err(str(e))


# ---------------------------------------------------------------------------
# Single scene operations
# ---------------------------------------------------------------------------

@cli.group()
def scene():
    """Add, update, or delete individual scenes."""


@scene.command("get")
@click.argument("scene_id", type=int)
@pass_client
def scene_get(client, scene_id):
    """Get one scene by ID."""
    try:
        data = client.get("/api/scenes")
        scenes_list_data = data.get("scenes", [])
        match = next((s for s in scenes_list_data if s.get("id") == scene_id), None)
        if match is None:
            err(f"Scene {scene_id} not found")
        out(match, True)
    except APIError as e:
        err(str(e))


@scene.command("add")
@click.option("--title", required=True, help="Scene title (displayed large on screen).")
@click.option("--subtitle", default="", help="Subtitle / quote.")
@click.option("--date", default="", help="Date or period (free text).")
@click.option("--year", default="", help="Short label for timeline bar (max 10 chars).")
@click.option("--bg", default="/uploads/вариации_2K_202603191339-2.jpg",
              help="Background image path.")
@click.option("--bg-video", default="", help="YouTube URL (overrides bg if set).")
@click.option("--night/--no-night", default=False, help="Enable star overlay.")
@pass_client
def scene_add(client, title, subtitle, date, year, bg, bg_video, night):
    """Add a new scene to the end of the timeline."""
    try:
        data = client.get("/api/scenes")
        scenes_arr = data.get("scenes", [])
        new_id = max((s.get("id", 0) for s in scenes_arr), default=-1) + 1
        new_scene = {
            "id": new_id,
            "title": title,
            "subtitle": subtitle,
            "date": date,
            "year": year or title[:10],
            "bg": bg,
            "night": night,
            "elements": [],
        }
        if bg_video:
            new_scene["bg_video"] = bg_video
        scenes_arr.append(new_scene)
        data["scenes"] = scenes_arr
        client.put("/api/scenes", data)
        out(new_scene, True)
    except APIError as e:
        err(str(e))


@scene.command("update")
@click.argument("scene_id", type=int)
@click.option("--title", default=None)
@click.option("--subtitle", default=None)
@click.option("--date", default=None)
@click.option("--year", default=None)
@click.option("--bg", default=None)
@click.option("--bg-video", default=None)
@click.option("--night/--no-night", default=None)
@pass_client
def scene_update(client, scene_id, title, subtitle, date, year, bg, bg_video, night):
    """Update fields of an existing scene."""
    try:
        data = client.get("/api/scenes")
        scenes_arr = data.get("scenes", [])
        scene_obj = next((s for s in scenes_arr if s.get("id") == scene_id), None)
        if scene_obj is None:
            err(f"Scene {scene_id} not found")
            return
        if title is not None:
            scene_obj["title"] = title
        if subtitle is not None:
            scene_obj["subtitle"] = subtitle
        if date is not None:
            scene_obj["date"] = date
        if year is not None:
            scene_obj["year"] = year
        if bg is not None:
            scene_obj["bg"] = bg
        if bg_video is not None:
            scene_obj["bg_video"] = bg_video
        if night is not None:
            scene_obj["night"] = night
        client.put("/api/scenes", data)
        out(scene_obj, True)
    except APIError as e:
        err(str(e))


@scene.command("delete")
@click.argument("scene_id", type=int)
@pass_client
def scene_delete(client, scene_id):
    """Delete a scene by ID."""
    try:
        data = client.get("/api/scenes")
        scenes_arr = data.get("scenes", [])
        before = len(scenes_arr)
        scenes_arr = [s for s in scenes_arr if s.get("id") != scene_id]
        if len(scenes_arr) == before:
            err(f"Scene {scene_id} not found")
            return
        data["scenes"] = scenes_arr
        client.put("/api/scenes", data)
        out({"deleted": scene_id}, True)
    except APIError as e:
        err(str(e))


@scene.command("reorder")
@click.argument("scene_ids", nargs=-1, type=int, required=True)
@pass_client
def scene_reorder(client, scene_ids):
    """Reorder scenes by providing all IDs in desired order."""
    try:
        data = client.get("/api/scenes")
        scenes_arr = data.get("scenes", [])
        id_map = {s["id"]: s for s in scenes_arr}
        missing = [sid for sid in scene_ids if sid not in id_map]
        if missing:
            err(f"Unknown scene IDs: {missing}")
            return
        data["scenes"] = [id_map[sid] for sid in scene_ids]
        client.put("/api/scenes", data)
        out({"order": list(scene_ids)}, True)
    except APIError as e:
        err(str(e))


# ---------------------------------------------------------------------------
# Element operations within a scene
# ---------------------------------------------------------------------------

@cli.group()
def element():
    """Manage elements (images, texts) within a scene."""


@element.command("list")
@click.argument("scene_id", type=int)
@pass_client
def element_list(client, scene_id):
    """List all elements in a scene."""
    try:
        data = client.get("/api/scenes")
        scene_obj = next((s for s in data.get("scenes", []) if s.get("id") == scene_id), None)
        if scene_obj is None:
            err(f"Scene {scene_id} not found")
            return
        elements = scene_obj.get("elements", [])
        rows = [{"index": i, "type": e.get("type", "image"), "src_or_text": e.get("src") or e.get("text", "")[:40]}
                for i, e in enumerate(elements)]
        out(rows, True)
    except APIError as e:
        err(str(e))


@element.command("add-image")
@click.argument("scene_id", type=int)
@click.option("--src", required=True, help="Image path, e.g. /uploads/0009.png")
@click.option("--x", type=float, default=0.5, show_default=True,
              help="Horizontal anchor 0–1 (0=left, 1=right).")
@click.option("--bottom", type=float, default=0.0, show_default=True,
              help="Vertical offset from bottom 0–1.")
@click.option("--h", type=float, default=70, show_default=True,
              help="Height as % of scene height (0=auto).")
@click.option("--w", type=float, default=0, show_default=True,
              help="Width as % of scene width (0=auto).")
@click.option("--parallax", type=float, default=1.0, show_default=True,
              help="Parallax scale factor 0–2.")
@click.option("--anim", default="float", show_default=True,
              type=click.Choice(["float", "zoom", "none"]),
              help="Animation type.")
@click.option("--flip/--no-flip", default=False, help="Horizontal mirror.")
@click.option("--soft-edge", type=int, default=0, help="Edge blur 0–100.")
@click.option("--content", default="", help="HTML shown in detail panel on click.")
@pass_client
def element_add_image(client, scene_id, src, x, bottom, h, w, parallax, anim, flip, soft_edge, content):
    """Add an image element to a scene."""
    try:
        data = client.get("/api/scenes")
        scene_obj = next((s for s in data.get("scenes", []) if s.get("id") == scene_id), None)
        if scene_obj is None:
            err(f"Scene {scene_id} not found")
            return
        elem = {
            "src": src,
            "x": x,
            "bottom": bottom,
            "h": h,
        }
        if w > 0:
            elem["w"] = w
        elem["parallax"] = parallax
        if anim != "none":
            elem["anim"] = anim
        if flip:
            elem["flip"] = True
        if soft_edge > 0:
            elem["softEdge"] = soft_edge
        if content:
            elem["content"] = content
        scene_obj.setdefault("elements", []).append(elem)
        client.put("/api/scenes", data)
        out(elem, True)
    except APIError as e:
        err(str(e))


@element.command("add-text")
@click.argument("scene_id", type=int)
@click.option("--text", required=True, help="Text content (use \\n for newlines).")
@click.option("--font", default="Georgia, serif", show_default=True,
              help="CSS font-family. Use Cyrillic-supporting fonts.")
@click.option("--size", type=float, default=4.0, show_default=True,
              help="Font size in vh (% of scene height).")
@click.option("--weight", type=int, default=400, show_default=True,
              help="Font weight 100–900.")
@click.option("--italic/--no-italic", default=False, help="Italic style.")
@click.option("--color", default="#f5e6c8", show_default=True, help="CSS color.")
@click.option("--opacity", type=float, default=1.0, show_default=True,
              help="Opacity 0–1.")
@click.option("--align", default="left", show_default=True,
              type=click.Choice(["left", "center", "right"]),
              help="Text alignment.")
@click.option("--letter-spacing", type=float, default=0.05, show_default=True,
              help="Letter spacing in em.")
@click.option("--line-height", type=float, default=1.2, show_default=True,
              help="Line height multiplier.")
@click.option("--shadow", default="0 2px 16px rgba(0,0,0,0.9),0 0 40px rgba(0,0,0,0.7)",
              show_default=True, help="CSS text-shadow.")
@click.option("--transform", default="",
              type=click.Choice(["", "uppercase"]),
              help="Text transform.")
@click.option("--max-width", type=float, default=0, show_default=True,
              help="Max width in vw (0=auto, single line).")
@click.option("--x", type=float, default=0.5, show_default=True,
              help="Horizontal position 0–1.")
@click.option("--bottom", type=float, default=0.62, show_default=True,
              help="Vertical position 0–1 from bottom.")
@click.option("--parallax", type=float, default=0.5, show_default=True,
              help="Parallax scale factor 0–2.")
@pass_client
def element_add_text(client, scene_id, text, font, size, weight, italic, color, opacity,
                     align, letter_spacing, line_height, shadow, transform, max_width, x, bottom, parallax):
    """Add a text element to a scene."""
    try:
        data = client.get("/api/scenes")
        scene_obj = next((s for s in data.get("scenes", []) if s.get("id") == scene_id), None)
        if scene_obj is None:
            err(f"Scene {scene_id} not found")
            return
        elem = {
            "type": "text",
            "text": text.replace("\\n", "\n"),
            "font": font,
            "fontSize": size,
            "fontWeight": weight,
            "fontStyle": "italic" if italic else "normal",
            "color": color,
            "opacity": opacity,
            "textAlign": align,
            "letterSpacing": letter_spacing,
            "lineHeight": line_height,
            "textShadow": shadow,
            "textTransform": transform,
            "maxWidth": max_width,
            "x": x,
            "bottom": bottom,
            "parallax": parallax,
        }
        scene_obj.setdefault("elements", []).append(elem)
        client.put("/api/scenes", data)
        out(elem, True)
    except APIError as e:
        err(str(e))


@element.command("add-json")
@click.argument("scene_id", type=int)
@click.argument("element_json", required=False)
@click.option("--stdin", is_flag=True, help="Read element JSON from stdin.")
@pass_client
def element_add_json(client, scene_id, element_json, stdin):
    """Add an element from a raw JSON string or stdin."""
    try:
        if stdin:
            raw = sys.stdin.read()
        elif element_json:
            raw = element_json
        else:
            err("Provide element JSON as argument or --stdin")
            return
        elem = json.loads(raw)
        data = client.get("/api/scenes")
        scene_obj = next((s for s in data.get("scenes", []) if s.get("id") == scene_id), None)
        if scene_obj is None:
            err(f"Scene {scene_id} not found")
            return
        scene_obj.setdefault("elements", []).append(elem)
        client.put("/api/scenes", data)
        out(elem, True)
    except json.JSONDecodeError as e:
        err(f"Invalid JSON: {e}")
    except APIError as e:
        err(str(e))


@element.command("update")
@click.argument("scene_id", type=int)
@click.argument("elem_index", type=int)
@click.argument("updates_json")
@pass_client
def element_update(client, scene_id, elem_index, updates_json):
    """Merge JSON updates into element at index within a scene.

    Example: uuk-timeline element update 5 0 '{"x": 0.3, "h": 80}'
    """
    try:
        updates = json.loads(updates_json)
        data = client.get("/api/scenes")
        scene_obj = next((s for s in data.get("scenes", []) if s.get("id") == scene_id), None)
        if scene_obj is None:
            err(f"Scene {scene_id} not found")
            return
        elements = scene_obj.get("elements", [])
        if elem_index < 0 or elem_index >= len(elements):
            err(f"Element index {elem_index} out of range (scene has {len(elements)} elements)")
            return
        elements[elem_index].update(updates)
        client.put("/api/scenes", data)
        out(elements[elem_index], True)
    except json.JSONDecodeError as e:
        err(f"Invalid JSON: {e}")
    except APIError as e:
        err(str(e))


@element.command("delete")
@click.argument("scene_id", type=int)
@click.argument("elem_index", type=int)
@pass_client
def element_delete(client, scene_id, elem_index):
    """Delete an element by index within a scene."""
    try:
        data = client.get("/api/scenes")
        scene_obj = next((s for s in data.get("scenes", []) if s.get("id") == scene_id), None)
        if scene_obj is None:
            err(f"Scene {scene_id} not found")
            return
        elements = scene_obj.get("elements", [])
        if elem_index < 0 or elem_index >= len(elements):
            err(f"Element index {elem_index} out of range")
            return
        removed = elements.pop(elem_index)
        client.put("/api/scenes", data)
        out({"deleted_index": elem_index, "element": removed}, True)
    except APIError as e:
        err(str(e))


# ===========================================================================
# PANORAMA
# ===========================================================================

@cli.group()
def panorama():
    """Manage the panorama intro screen (panorama.json)."""


@panorama.command("get")
@pass_client
def panorama_get(client):
    """Get the full panorama document."""
    try:
        data = client.get("/api/panorama")
        out(data, True)
    except APIError as e:
        err(str(e))


@panorama.command("set-background")
@click.argument("image_path")
@pass_client
def panorama_set_background(client, image_path):
    """Set the panorama background image."""
    try:
        data = client.get("/api/panorama")
        data["background"] = image_path
        client.put("/api/panorama", data)
        out({"background": image_path}, True)
    except APIError as e:
        err(str(e))


@panorama.command("add-element")
@click.option("--id", "elem_id", required=True, help="Unique element ID string.")
@click.option("--src", required=True, help="Image path.")
@click.option("--x", type=float, required=True, help="Center X position 0–100 (%).")
@click.option("--y", type=float, required=True, help="Center Y position 0–100 (%).")
@click.option("--width", type=float, default=10, show_default=True,
              help="Width in vh%.")
@click.option("--scene-id", type=int, default=None, help="Scene to navigate to on click.")
@click.option("--anim", default=None, type=click.Choice(["float", "zoom"]),
              help="Animation type.")
@pass_client
def panorama_add_element(client, elem_id, src, x, y, width, scene_id, anim):
    """Add a visual element to the panorama."""
    try:
        data = client.get("/api/panorama")
        elem = {"id": elem_id, "src": src, "x": x, "y": y, "width": width}
        if scene_id is not None:
            elem["sceneId"] = scene_id
        if anim:
            elem["anim"] = anim
        data.setdefault("elements", []).append(elem)
        client.put("/api/panorama", data)
        out(elem, True)
    except APIError as e:
        err(str(e))


@panorama.command("remove-element")
@click.argument("elem_id")
@pass_client
def panorama_remove_element(client, elem_id):
    """Remove a panorama element by its ID."""
    try:
        data = client.get("/api/panorama")
        before = len(data.get("elements", []))
        data["elements"] = [e for e in data.get("elements", []) if e.get("id") != elem_id]
        if len(data["elements"]) == before:
            err(f"Element '{elem_id}' not found")
            return
        client.put("/api/panorama", data)
        out({"removed": elem_id}, True)
    except APIError as e:
        err(str(e))


@panorama.command("add-clickarea")
@click.option("--scene-id", type=int, required=True, help="Target scene ID.")
@click.option("--x", type=float, required=True, help="Left edge 0–100 (%).")
@click.option("--y", type=float, required=True, help="Top edge 0–100 (%).")
@click.option("--width", type=float, required=True, help="Width 0–100 (%).")
@click.option("--height", type=float, required=True, help="Height 0–100 (%).")
@pass_client
def panorama_add_clickarea(client, scene_id, x, y, width, height):
    """Add an invisible click area to the panorama."""
    try:
        data = client.get("/api/panorama")
        area = {"sceneId": scene_id, "x": x, "y": y, "width": width, "height": height}
        data.setdefault("clickAreas", []).append(area)
        client.put("/api/panorama", data)
        out(area, True)
    except APIError as e:
        err(str(e))


@panorama.command("remove-clickarea")
@click.argument("scene_id", type=int)
@pass_client
def panorama_remove_clickarea(client, scene_id):
    """Remove a click area by its target scene ID."""
    try:
        data = client.get("/api/panorama")
        before = len(data.get("clickAreas", []))
        data["clickAreas"] = [a for a in data.get("clickAreas", []) if a.get("sceneId") != scene_id]
        if len(data["clickAreas"]) == before:
            err(f"No click area for scene {scene_id}")
            return
        client.put("/api/panorama", data)
        out({"removed_scene_id": scene_id}, True)
    except APIError as e:
        err(str(e))


@panorama.command("set")
@click.argument("json_file", required=False)
@click.option("--stdin", is_flag=True)
@pass_client
def panorama_set(client, json_file, stdin):
    """Replace the entire panorama document from a JSON file or stdin."""
    if stdin:
        raw = sys.stdin.read()
    elif json_file:
        with open(json_file, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        err("Provide a JSON file path or --stdin")
        return
    try:
        body = json.loads(raw)
        result = client.put("/api/panorama", body)
        out(result or {"ok": True}, True)
    except json.JSONDecodeError as e:
        err(f"Invalid JSON: {e}")
    except APIError as e:
        err(str(e))


# ===========================================================================
# PRESETS
# ===========================================================================

@cli.group()
def presets():
    """Manage saved presets (scenes and panorama)."""


@presets.command("list")
@pass_client
def presets_list(client):
    """List all available presets."""
    try:
        data = client.get("/api/presets")
        out(data, True)
    except APIError as e:
        err(str(e))


@presets.command("load")
@click.argument("name")
@pass_client
def presets_load(client, name):
    """Load a preset by name (makes it the active dataset)."""
    try:
        result = client.post(f"/api/presets/{name}/load")
        out(result or {"loaded": name}, True)
    except APIError as e:
        err(str(e))


@presets.command("save")
@click.argument("name")
@pass_client
def presets_save(client, name):
    """Save the current state as a named preset."""
    try:
        result = client.post(f"/api/presets/{name}/save")
        out(result or {"saved": name}, True)
    except APIError as e:
        err(str(e))


# ===========================================================================
# LIBRARY / UPLOAD
# ===========================================================================

@cli.group()
def library():
    """Browse and upload images."""


@library.command("list")
@pass_client
def library_list(client):
    """List all uploaded images in /uploads/."""
    try:
        data = client.get("/api/library")
        out(data, True)
    except APIError as e:
        err(str(e))


@cli.command("upload")
@click.argument("file_path")
@pass_client
def upload(client, file_path):
    """Upload an image file. Returns the server path to use as src."""
    try:
        result = client.upload_file(file_path)
        out(result, True)
    except FileNotFoundError:
        err(f"File not found: {file_path}")
    except APIError as e:
        err(str(e))


# ===========================================================================
# BULK OPERATIONS
# ===========================================================================

@cli.command("apply-json")
@click.argument("json_file", required=False)
@click.option("--stdin", is_flag=True, help="Read from stdin.")
@pass_client
def apply_json(client, json_file, stdin):
    """Apply a bulk operation document.

    The JSON should have one or more top-level keys:
    - "scenes": full scenes document to PUT
    - "panorama": full panorama document to PUT
    - "preset_save": name to save current state as
    - "preset_load": name to load

    Useful for agents that want to apply a complete timeline in one call.
    """
    if stdin:
        raw = sys.stdin.read()
    elif json_file:
        with open(json_file, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        err("Provide a JSON file path or --stdin")
        return
    try:
        doc = json.loads(raw)
        results = {}
        if "preset_load" in doc:
            client.post(f"/api/presets/{doc['preset_load']}/load")
            results["preset_load"] = doc["preset_load"]
        if "scenes" in doc:
            client.put("/api/scenes", doc["scenes"])
            results["scenes"] = "updated"
        if "panorama" in doc:
            client.put("/api/panorama", doc["panorama"])
            results["panorama"] = "updated"
        if "preset_save" in doc:
            client.post(f"/api/presets/{doc['preset_save']}/save")
            results["preset_save"] = doc["preset_save"]
        out(results, True)
    except json.JSONDecodeError as e:
        err(f"Invalid JSON: {e}")
    except APIError as e:
        err(str(e))


# ===========================================================================
# IMAGE — search, fetch, cutout
# ===========================================================================

@cli.group()
def image():
    """Search free image APIs, download images, remove backgrounds."""


@image.command("search")
@click.option("--query", "-q", required=True, help="Search query (in English for best results).")
@click.option("--source", default="pexels", show_default=True,
              type=click.Choice(["pexels", "pixabay"]), help="Image API to use.")
@click.option("--per-page", default=10, show_default=True, type=int, help="Max results (1–40).")
@pass_client
def image_search(client, query, source, per_page):
    """Search free stock images.

    Returns a list of results with `id`, `url`, `thumb`, `description`, `author`.
    Pass a `url` to `image fetch` to download the image.

    Requires server env var: PEXELS_API_KEY or PIXABAY_API_KEY.

    Example:
        uuk-timeline image search -q "angel wings" --source pexels
    """
    try:
        data = client.get(f"/api/image-search?q={query}&source={source}&per_page={per_page}")
        out(data)
    except APIError as e:
        err(str(e))


@image.command("fetch")
@click.option("--url", "-u", required=True, help="Direct image URL to download.")
@click.option("--name", default="", help="Optional base filename (without extension).")
@pass_client
def image_fetch(client, url, name):
    """Download a remote image into the uploads folder.

    Returns the server path (`/uploads/...`) ready to use as `src` in a scene element.

    Example:
        uuk-timeline image fetch --url "https://images.pexels.com/photos/.../photo.jpeg"
    """
    try:
        body = {"url": url}
        if name:
            body["filename"] = name
        result = client.post("/api/image-fetch", body)
        out(result)
    except APIError as e:
        err(str(e))


@image.command("cutout")
@click.option("--src", required=True, help="Server path of uploaded image, e.g. /uploads/file.jpg")
@click.option("--model", default="u2net", show_default=True,
              type=click.Choice(["u2net", "u2net_human_seg", "isnet-general-use", "silueta"]),
              help="AI model. Use u2net_human_seg for people, isnet for sharp edges.")
@click.option("--point", "points", multiple=True, metavar="X,Y[,LABEL]",
              help="Foreground point hint (label 1=keep, 0=remove). Repeat for multiple points. "
                   "Activates SAM model automatically.")
@click.option("--rect", default="", metavar="X1,Y1,X2,Y2",
              help="Bounding box to constrain object selection.")
@pass_client
def image_cutout(client, src, model, points, rect):
    """Remove background from an uploaded image using AI.

    Returns the server path of the new WebP with transparency.

    Example:
        uuk-timeline image cutout --src /uploads/1234_angel.jpg --model u2net
        uuk-timeline image cutout --src /uploads/1234_person.jpg --model u2net_human_seg
        uuk-timeline image cutout --src /uploads/1234_scene.jpg --point 450,300 --point 200,100,0
    """
    try:
        body = {
            "src":    src,
            "model":  model,
            "points": ";".join(points),
            "rect":   rect,
        }
        result = client.post("/api/remove-bg", body)
        out(result)
    except APIError as e:
        err(str(e))


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
