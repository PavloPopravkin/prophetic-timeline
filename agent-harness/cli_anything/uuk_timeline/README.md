# cli-anything-uuk-timeline

CLI harness for the **uuk-timeline** Prophetic Timeline web application.
Allows AI agents to create and manage timelines and panoramas via REST API.

## Prerequisites

The uuk-timeline server must be running:

```bash
cd /Users/pavlopopravkin/www/uuk-timeline
npm start
# Server available at http://localhost:3000
```

## Installation

```bash
pip install -e /Users/pavlopopravkin/www/uuk-timeline/agent-harness/
```

Verify:
```bash
uuk-timeline --help
```

## Basic Usage

```bash
# List scenes
uuk-timeline scenes list

# Add a scene
uuk-timeline scene add --title "Рождество" --year "Рожд." --night

# Add image element to scene 0
uuk-timeline element add-image 0 \
  --src "/uploads/0012.png" --x 0.5 --h 75 --parallax 1.2

# Add text element to scene 0
uuk-timeline element add-text 0 \
  --text "Рождество Христово" \
  --font "'Cormorant Garamond', serif" \
  --size 6 --italic --color "#f0d880"

# View panorama
uuk-timeline panorama get

# Apply a complete JSON document
cat my-timeline.json | uuk-timeline apply-json --stdin
```

## Running Tests

```bash
cd /Users/pavlopopravkin/www/uuk-timeline/agent-harness
# Server must be running for E2E tests
pytest cli_anything/uuk_timeline/tests/ -v -s
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `UUK_SERVER` | `http://localhost:3000` | Override server URL |
| `CLI_ANYTHING_FORCE_INSTALLED` | — | Set to `1` to require installed command in tests |

## Full Documentation

- **SKILL.md**: `cli_anything/uuk_timeline/skills/SKILL.md`
- **SOP**: `UUK-TIMELINE.md`
- **AGENT_INSTRUCTIONS.md**: `/Users/pavlopopravkin/www/uuk-timeline/AGENT_INSTRUCTIONS.md`
