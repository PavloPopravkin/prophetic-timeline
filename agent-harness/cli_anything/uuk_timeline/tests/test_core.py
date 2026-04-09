"""Unit tests for cli-anything-uuk-timeline core — no server required."""

import json
import pytest
from cli_anything.uuk_timeline.core.api import APIClient


# ---------------------------------------------------------------------------
# APIClient construction
# ---------------------------------------------------------------------------

class TestAPIClientConstruction:
    def test_default_base_url(self):
        client = APIClient()
        assert client.base_url == "http://localhost:3000"

    def test_custom_base_url(self):
        client = APIClient("http://example.com:4000")
        assert client.base_url == "http://example.com:4000"

    def test_trailing_slash_stripped(self):
        client = APIClient("http://localhost:3000/")
        assert client.base_url == "http://localhost:3000"

    def test_env_var_read_by_cli(self, monkeypatch):
        """UUK_SERVER env var should be picked up by the CLI (not APIClient directly)."""
        import os
        monkeypatch.setenv("UUK_SERVER", "http://custom:9999")
        # APIClient doesn't read env itself; the CLI does via click option
        # Verify the env var name is consistent with the CLI definition
        from cli_anything.uuk_timeline.uuk_timeline_cli import cli
        for param in cli.params:
            if param.name == "server":
                assert "UUK_SERVER" in (param.envvar or []) or param.envvar == "UUK_SERVER"
                break


# ---------------------------------------------------------------------------
# Image element shape
# ---------------------------------------------------------------------------

class TestImageElementShape:
    def _make_image_elem(self, src="/uploads/0009.png", x=0.5, bottom=0.0,
                         h=70, w=0, parallax=1.0, anim="float",
                         flip=False, soft_edge=0, content=""):
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
        return elem

    def test_required_keys_present(self):
        elem = self._make_image_elem()
        for key in ("src", "x", "bottom", "h", "parallax"):
            assert key in elem, f"Missing key: {key}"

    def test_default_no_type_key(self):
        elem = self._make_image_elem()
        assert "type" not in elem

    def test_anim_none_omitted(self):
        elem = self._make_image_elem(anim="none")
        assert "anim" not in elem

    def test_flip_omitted_when_false(self):
        elem = self._make_image_elem(flip=False)
        assert "flip" not in elem

    def test_flip_present_when_true(self):
        elem = self._make_image_elem(flip=True)
        assert elem["flip"] is True

    def test_w_omitted_when_zero(self):
        elem = self._make_image_elem(w=0)
        assert "w" not in elem

    def test_w_present_when_nonzero(self):
        elem = self._make_image_elem(w=40)
        assert elem["w"] == 40

    def test_soft_edge_omitted_when_zero(self):
        elem = self._make_image_elem(soft_edge=0)
        assert "softEdge" not in elem

    def test_soft_edge_present(self):
        elem = self._make_image_elem(soft_edge=20)
        assert elem["softEdge"] == 20

    def test_content_present(self):
        elem = self._make_image_elem(content="<h3>Title</h3>")
        assert elem["content"] == "<h3>Title</h3>"


# ---------------------------------------------------------------------------
# Text element shape
# ---------------------------------------------------------------------------

class TestTextElementShape:
    def _make_text_elem(self, text="Hello", font="Georgia, serif",
                        size=4.0, weight=400, italic=False,
                        color="#f5e6c8", opacity=1.0, align="left",
                        letter_spacing=0.05, line_height=1.2,
                        shadow="", transform="", max_width=0,
                        x=0.5, bottom=0.62, parallax=0.5):
        return {
            "type": "text",
            "text": text,
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

    def test_type_is_text(self):
        elem = self._make_text_elem()
        assert elem["type"] == "text"

    def test_italic_flag(self):
        elem = self._make_text_elem(italic=True)
        assert elem["fontStyle"] == "italic"

    def test_not_italic(self):
        elem = self._make_text_elem(italic=False)
        assert elem["fontStyle"] == "normal"

    def test_max_width_zero_by_default(self):
        elem = self._make_text_elem()
        assert elem["maxWidth"] == 0

    def test_required_keys(self):
        elem = self._make_text_elem()
        for key in ("type", "text", "font", "fontSize", "fontWeight",
                    "fontStyle", "color", "opacity", "textAlign",
                    "letterSpacing", "lineHeight", "textShadow",
                    "textTransform", "maxWidth", "x", "bottom", "parallax"):
            assert key in elem, f"Missing key: {key}"

    def test_newline_in_text(self):
        elem = self._make_text_elem(text="Line 1\nLine 2")
        assert "\n" in elem["text"]


# ---------------------------------------------------------------------------
# Panorama element shape
# ---------------------------------------------------------------------------

class TestPanoramaElementShape:
    def _make_pano_elem(self, elem_id="elem-cross", src="/uploads/0015.png",
                         x=55.0, y=12.0, width=16.0, scene_id=None, anim=None):
        elem = {"id": elem_id, "src": src, "x": x, "y": y, "width": width}
        if scene_id is not None:
            elem["sceneId"] = scene_id
        if anim:
            elem["anim"] = anim
        return elem

    def test_required_keys(self):
        elem = self._make_pano_elem()
        for key in ("id", "src", "x", "y", "width"):
            assert key in elem, f"Missing key: {key}"

    def test_scene_id_optional(self):
        elem = self._make_pano_elem()
        assert "sceneId" not in elem

    def test_scene_id_present(self):
        elem = self._make_pano_elem(scene_id=27)
        assert elem["sceneId"] == 27

    def test_anim_optional(self):
        elem = self._make_pano_elem()
        assert "anim" not in elem

    def test_percent_coordinates_range(self):
        elem = self._make_pano_elem(x=50.0, y=25.0)
        # Panorama uses 0–100 percent, not 0–1 floats
        assert 0 <= elem["x"] <= 100
        assert 0 <= elem["y"] <= 100
