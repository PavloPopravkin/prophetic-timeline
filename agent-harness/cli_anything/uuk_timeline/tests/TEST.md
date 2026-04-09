# Test Plan — cli-anything-uuk-timeline

## Test Inventory

| File | Tests planned | Purpose |
|------|--------------|---------|
| `test_core.py` | 12 | Unit tests for API client and data helpers (no server) |
| `test_full_e2e.py` | 16 | E2E tests against live server + CLI subprocess tests |

---

## Unit Test Plan (`test_core.py`)

Tests run without a server. They validate data-manipulation logic in isolation.

### APIClient construction
- Correct base URL stored
- Trailing slash stripped

### JSON serialization helpers
- Image element dict has required keys
- Text element dict has `type: "text"`
- Default values are correct (x=0.5, bottom=0.0, h=70, parallax=1.0)

### Panorama element dict
- Required keys: id, src, x, y, width
- Optional: sceneId, anim

### Click argument parsing
- scene add: all options map to correct keys
- element add-text: --italic becomes `fontStyle: "italic"`
- element add-image: --anim none → no `anim` key in output

---

## E2E Test Plan (`test_full_e2e.py`)

**Requires server running at `http://localhost:3000`.**

### Scenes API
- GET /api/scenes returns object with `scenes` array
- PUT /api/scenes round-trips correctly
- scene add increments id correctly
- scene delete removes only the target scene
- scene update modifies only specified fields

### Element operations
- add-image appends element with correct shape
- add-text appends element with `type: "text"`
- element update merges fields (does not overwrite unrelated fields)
- element delete removes correct index

### Panorama API
- GET /api/panorama returns object with `elements` and `clickAreas`
- set-background updates only background field
- add-element appends correctly
- remove-element removes by id
- add-clickarea appends area
- remove-clickarea removes by sceneId

### CLI subprocess (installed command)
- `uuk-timeline --help` exits 0
- `uuk-timeline scenes list` returns valid JSON array
- `uuk-timeline scene add ...` returns new scene JSON
- `uuk-timeline apply-json --stdin` applies bulk document

---

## Test Results

## Results (2026-04-07)

```
============================= test session starts ==============================
platform darwin -- Python 3.10.11, pytest-7.2.2
collected 47 items

test_core.py::TestAPIClientConstruction::test_default_base_url PASSED
test_core.py::TestAPIClientConstruction::test_custom_base_url PASSED
test_core.py::TestAPIClientConstruction::test_trailing_slash_stripped PASSED
test_core.py::TestAPIClientConstruction::test_env_var_read_by_cli PASSED
test_core.py::TestImageElementShape::test_required_keys_present PASSED
test_core.py::TestImageElementShape::test_default_no_type_key PASSED
test_core.py::TestImageElementShape::test_anim_none_omitted PASSED
test_core.py::TestImageElementShape::test_flip_omitted_when_false PASSED
test_core.py::TestImageElementShape::test_flip_present_when_true PASSED
test_core.py::TestImageElementShape::test_w_omitted_when_zero PASSED
test_core.py::TestImageElementShape::test_w_present_when_nonzero PASSED
test_core.py::TestImageElementShape::test_soft_edge_omitted_when_zero PASSED
test_core.py::TestImageElementShape::test_soft_edge_present PASSED
test_core.py::TestImageElementShape::test_content_present PASSED
test_core.py::TestTextElementShape::test_type_is_text PASSED
test_core.py::TestTextElementShape::test_italic_flag PASSED
test_core.py::TestTextElementShape::test_not_italic PASSED
test_core.py::TestTextElementShape::test_max_width_zero_by_default PASSED
test_core.py::TestTextElementShape::test_required_keys PASSED
test_core.py::TestTextElementShape::test_newline_in_text PASSED
test_core.py::TestPanoramaElementShape::test_required_keys PASSED
test_core.py::TestPanoramaElementShape::test_scene_id_optional PASSED
test_core.py::TestPanoramaElementShape::test_scene_id_present PASSED
test_core.py::TestPanoramaElementShape::test_anim_optional PASSED
test_core.py::TestPanoramaElementShape::test_percent_coordinates_range PASSED
test_full_e2e.py::TestScenesAPI::test_get_scenes_structure PASSED
test_full_e2e.py::TestScenesAPI::test_scenes_round_trip PASSED
test_full_e2e.py::TestScenesAPI::test_scene_add_increments_id PASSED
test_full_e2e.py::TestScenesAPI::test_scene_delete_removes_only_target PASSED
test_full_e2e.py::TestScenesAPI::test_scene_update_modifies_fields PASSED
test_full_e2e.py::TestElementOperations::test_add_image_element PASSED
test_full_e2e.py::TestElementOperations::test_add_text_element PASSED
test_full_e2e.py::TestElementOperations::test_element_update_merges PASSED
test_full_e2e.py::TestPanoramaAPI::test_get_panorama_structure PASSED
test_full_e2e.py::TestPanoramaAPI::test_set_background PASSED
test_full_e2e.py::TestPanoramaAPI::test_add_panorama_element PASSED
test_full_e2e.py::TestPanoramaAPI::test_remove_panorama_element PASSED
test_full_e2e.py::TestPanoramaAPI::test_add_clickarea PASSED
test_full_e2e.py::TestPanoramaAPI::test_remove_clickarea PASSED
test_full_e2e.py::TestCLISubprocess::test_help PASSED
test_full_e2e.py::TestCLISubprocess::test_scene_help PASSED
test_full_e2e.py::TestCLISubprocess::test_element_help PASSED
test_full_e2e.py::TestCLISubprocess::test_panorama_help PASSED
test_full_e2e.py::TestCLISubprocess::test_scenes_list_returns_json_array PASSED
test_full_e2e.py::TestCLISubprocess::test_scene_add_and_delete PASSED
test_full_e2e.py::TestCLISubprocess::test_panorama_get PASSED
test_full_e2e.py::TestCLISubprocess::test_apply_json_bulk PASSED

============================== 47 passed in 2.09s ==============================
```

**Summary:** 47 tests, 100% pass rate, 2.09s
- 25 unit tests (no server)
- 22 E2E tests (live server + subprocess) — server was running at http://localhost:3000
- `_resolve_cli` used installed command: `/Users/pavlopopravkin/miniconda3/bin/uuk-timeline`
