"""
E2E tests for cli-anything-uuk-timeline.

Requires the uuk-timeline server running at http://localhost:3000
(or UUK_SERVER env var). Tests are skipped if the server is unreachable.

Run:
    pytest cli_anything/uuk_timeline/tests/test_full_e2e.py -v -s

Force installed command:
    CLI_ANYTHING_FORCE_INSTALLED=1 pytest ... -v -s
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error

import pytest

from cli_anything.uuk_timeline.core import APIClient, APIError


SERVER = os.environ.get("UUK_SERVER", "http://localhost:3000")


def _server_reachable():
    try:
        urllib.request.urlopen(SERVER + "/api/scenes", timeout=3)
        return True
    except Exception:
        return False


def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev."""
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.uuk_timeline.uuk_timeline_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


requires_server = pytest.mark.skipif(
    not _server_reachable(),
    reason="uuk-timeline server not running at " + SERVER
)


@pytest.fixture
def client():
    return APIClient(SERVER)


@pytest.fixture
def original_scenes(client):
    """Save and restore scenes around a test."""
    original = client.get("/api/scenes")
    yield original
    client.put("/api/scenes", original)


@pytest.fixture
def original_panorama(client):
    """Save and restore panorama around a test."""
    original = client.get("/api/panorama")
    yield original
    client.put("/api/panorama", original)


# ===========================================================================
# Scenes API
# ===========================================================================

@requires_server
class TestScenesAPI:
    def test_get_scenes_structure(self, client):
        data = client.get("/api/scenes")
        assert "scenes" in data
        assert isinstance(data["scenes"], list)
        assert len(data["scenes"]) > 0
        first = data["scenes"][0]
        assert "id" in first
        assert "title" in first

    def test_scenes_round_trip(self, client, original_scenes):
        original = client.get("/api/scenes")
        client.put("/api/scenes", original)
        after = client.get("/api/scenes")
        assert len(after["scenes"]) == len(original["scenes"])

    def test_scene_add_increments_id(self, client, original_scenes):
        data = client.get("/api/scenes")
        max_id = max(s["id"] for s in data["scenes"])
        new_scene = {
            "id": max_id + 1,
            "title": "Test Scene ADD",
            "subtitle": "",
            "date": "",
            "year": "Test",
            "bg": "/uploads/вариации_2K_202603191339-2.jpg",
            "night": False,
            "elements": [],
        }
        data["scenes"].append(new_scene)
        client.put("/api/scenes", data)

        after = client.get("/api/scenes")
        ids = [s["id"] for s in after["scenes"]]
        assert max_id + 1 in ids

    def test_scene_delete_removes_only_target(self, client, original_scenes):
        data = client.get("/api/scenes")
        original_count = len(data["scenes"])
        # Add a temp scene
        temp_id = max(s["id"] for s in data["scenes"]) + 1
        data["scenes"].append({
            "id": temp_id, "title": "TEMP", "subtitle": "", "date": "",
            "year": "TEMP", "bg": "", "night": False, "elements": []
        })
        client.put("/api/scenes", data)

        # Delete it
        data2 = client.get("/api/scenes")
        data2["scenes"] = [s for s in data2["scenes"] if s["id"] != temp_id]
        client.put("/api/scenes", data2)

        after = client.get("/api/scenes")
        assert len(after["scenes"]) == original_count
        assert all(s["id"] != temp_id for s in after["scenes"])

    def test_scene_update_modifies_fields(self, client, original_scenes):
        data = client.get("/api/scenes")
        first_id = data["scenes"][0]["id"]
        original_title = data["scenes"][0]["title"]

        data["scenes"][0]["title"] = "UPDATED TITLE"
        client.put("/api/scenes", data)

        after = client.get("/api/scenes")
        updated = next(s for s in after["scenes"] if s["id"] == first_id)
        assert updated["title"] == "UPDATED TITLE"


# ===========================================================================
# Element operations
# ===========================================================================

@requires_server
class TestElementOperations:
    def test_add_image_element(self, client, original_scenes):
        data = client.get("/api/scenes")
        scene = data["scenes"][0]
        scene_id = scene["id"]
        original_len = len(scene.get("elements", []))

        new_elem = {"src": "/uploads/0001.png", "x": 0.5, "bottom": 0.0,
                    "h": 70, "parallax": 1.0, "anim": "float"}
        scene["elements"] = scene.get("elements", []) + [new_elem]
        client.put("/api/scenes", data)

        after = client.get("/api/scenes")
        s = next(s for s in after["scenes"] if s["id"] == scene_id)
        assert len(s["elements"]) == original_len + 1
        assert s["elements"][-1]["src"] == "/uploads/0001.png"

    def test_add_text_element(self, client, original_scenes):
        data = client.get("/api/scenes")
        scene = data["scenes"][0]
        scene_id = scene["id"]
        original_len = len(scene.get("elements", []))

        text_elem = {
            "type": "text", "text": "Test Text", "font": "Georgia, serif",
            "fontSize": 4, "fontWeight": 400, "fontStyle": "normal",
            "color": "#ffffff", "opacity": 1, "textAlign": "left",
            "letterSpacing": 0.05, "lineHeight": 1.2,
            "textShadow": "", "textTransform": "", "maxWidth": 0,
            "x": 0.5, "bottom": 0.6, "parallax": 0.5
        }
        scene["elements"] = scene.get("elements", []) + [text_elem]
        client.put("/api/scenes", data)

        after = client.get("/api/scenes")
        s = next(s for s in after["scenes"] if s["id"] == scene_id)
        assert s["elements"][-1]["type"] == "text"
        assert s["elements"][-1]["text"] == "Test Text"

    def test_element_update_merges(self, client, original_scenes):
        data = client.get("/api/scenes")
        scene = data["scenes"][0]
        scene_id = scene["id"]
        scene.setdefault("elements", [])
        scene["elements"].append({"src": "/uploads/0002.png", "x": 0.3, "h": 60, "bottom": 0.0, "parallax": 1.0})
        client.put("/api/scenes", data)

        data2 = client.get("/api/scenes")
        s = next(s for s in data2["scenes"] if s["id"] == scene_id)
        idx = len(s["elements"]) - 1
        s["elements"][idx]["x"] = 0.7
        client.put("/api/scenes", data2)

        after = client.get("/api/scenes")
        s = next(s for s in after["scenes"] if s["id"] == scene_id)
        assert s["elements"][idx]["x"] == 0.7
        assert s["elements"][idx]["h"] == 60  # unchanged


# ===========================================================================
# Panorama API
# ===========================================================================

@requires_server
class TestPanoramaAPI:
    def test_get_panorama_structure(self, client):
        data = client.get("/api/panorama")
        assert "elements" in data
        assert "clickAreas" in data
        assert isinstance(data["elements"], list)
        assert isinstance(data["clickAreas"], list)

    def test_set_background(self, client, original_panorama):
        new_bg = "/uploads/вариации_2K_202603191339-3.jpg"
        data = client.get("/api/panorama")
        data["background"] = new_bg
        client.put("/api/panorama", data)

        after = client.get("/api/panorama")
        assert after["background"] == new_bg

    def test_add_panorama_element(self, client, original_panorama):
        data = client.get("/api/panorama")
        original_count = len(data["elements"])
        new_elem = {"id": "test-elem-xyz", "src": "/uploads/0001.png",
                    "x": 50, "y": 50, "width": 10}
        data["elements"].append(new_elem)
        client.put("/api/panorama", data)

        after = client.get("/api/panorama")
        assert len(after["elements"]) == original_count + 1
        assert any(e["id"] == "test-elem-xyz" for e in after["elements"])

    def test_remove_panorama_element(self, client, original_panorama):
        data = client.get("/api/panorama")
        data["elements"].append({"id": "test-elem-to-remove", "src": "/uploads/0001.png",
                                  "x": 10, "y": 10, "width": 5})
        client.put("/api/panorama", data)

        data2 = client.get("/api/panorama")
        data2["elements"] = [e for e in data2["elements"] if e["id"] != "test-elem-to-remove"]
        client.put("/api/panorama", data2)

        after = client.get("/api/panorama")
        assert all(e["id"] != "test-elem-to-remove" for e in after["elements"])

    def test_add_clickarea(self, client, original_panorama):
        data = client.get("/api/panorama")
        original_count = len(data["clickAreas"])
        area = {"sceneId": 9999, "x": 5, "y": 5, "width": 10, "height": 10}
        data["clickAreas"].append(area)
        client.put("/api/panorama", data)

        after = client.get("/api/panorama")
        assert len(after["clickAreas"]) == original_count + 1
        assert any(a["sceneId"] == 9999 for a in after["clickAreas"])

    def test_remove_clickarea(self, client, original_panorama):
        data = client.get("/api/panorama")
        data["clickAreas"].append({"sceneId": 8888, "x": 1, "y": 1, "width": 5, "height": 5})
        client.put("/api/panorama", data)

        data2 = client.get("/api/panorama")
        data2["clickAreas"] = [a for a in data2["clickAreas"] if a["sceneId"] != 8888]
        client.put("/api/panorama", data2)

        after = client.get("/api/panorama")
        assert all(a["sceneId"] != 8888 for a in after["clickAreas"])


# ===========================================================================
# CLI subprocess tests
# ===========================================================================

CLI_BASE = _resolve_cli("uuk-timeline")


def _run(args, input_data=None, check=True):
    return subprocess.run(
        CLI_BASE + args,
        capture_output=True, text=True,
        input=input_data,
        check=check,
    )


class TestCLISubprocess:
    def test_help(self):
        result = _run(["--help"])
        assert result.returncode == 0
        assert "COMMAND" in result.stdout

    def test_scene_help(self):
        result = _run(["scene", "--help"])
        assert result.returncode == 0
        assert "add" in result.stdout

    def test_element_help(self):
        result = _run(["element", "--help"])
        assert result.returncode == 0
        assert "add-image" in result.stdout

    def test_panorama_help(self):
        result = _run(["panorama", "--help"])
        assert result.returncode == 0
        assert "get" in result.stdout

    @requires_server
    def test_scenes_list_returns_json_array(self):
        result = _run(["scenes", "list"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "title" in data[0]

    @requires_server
    def test_scene_add_and_delete(self):
        # Save original
        orig = json.loads(_run(["scenes", "get"]).stdout)

        try:
            # Add scene
            result = _run([
                "scene", "add",
                "--title", "CLI Test Scene",
                "--year", "CLITest",
                "--no-night",
            ])
            assert result.returncode == 0
            new_scene = json.loads(result.stdout)
            assert new_scene["title"] == "CLI Test Scene"
            new_id = new_scene["id"]
            print(f"\n  Created scene id={new_id}")

            # Verify it exists
            scenes = json.loads(_run(["scenes", "list"]).stdout)
            assert any(s["id"] == new_id for s in scenes)

            # Delete it
            del_result = _run(["scene", "delete", str(new_id)])
            assert del_result.returncode == 0
            deleted = json.loads(del_result.stdout)
            assert deleted["deleted"] == new_id

        finally:
            # Always restore
            _run(["scenes", "set", "--stdin"], input_data=json.dumps(orig))

    @requires_server
    def test_panorama_get(self):
        result = _run(["panorama", "get"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "elements" in data
        assert "clickAreas" in data

    @requires_server
    def test_apply_json_bulk(self):
        orig_scenes = json.loads(_run(["scenes", "get"]).stdout)
        orig_panorama = json.loads(_run(["panorama", "get"]).stdout)

        try:
            bulk = {
                "scenes": {
                    "name": "Bulk Test",
                    "scenes": orig_scenes["scenes"][:2]  # just first 2 scenes
                }
            }
            result = _run(["apply-json", "--stdin"], input_data=json.dumps(bulk))
            assert result.returncode == 0
            applied = json.loads(result.stdout)
            assert applied.get("scenes") == "updated"

            current = json.loads(_run(["scenes", "get"]).stdout)
            assert current["name"] == "Bulk Test"
            assert len(current["scenes"]) == 2

        finally:
            _run(["scenes", "set", "--stdin"], input_data=json.dumps(orig_scenes))
            _run(["panorama", "set", "--stdin"], input_data=json.dumps(orig_panorama))
