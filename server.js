const express = require('express');
const multer  = require('multer');
const fs      = require('fs');
const path    = require('path');

const app  = express();
const PORT = process.env.PORT || 3000;
const ROOT = __dirname;

const ADMIN_USER = process.env.ADMIN_USER || 'timelineAdmin';
const ADMIN_PASS = process.env.ADMIN_PASS || 'hwbUNWHqR9N4mT';

function basicAuth(req, res, next) {
  const header = req.headers['authorization'];
  if (!header || !header.startsWith('Basic ')) {
    res.set('WWW-Authenticate', 'Basic realm="Timeline Admin"');
    return res.status(401).send('Unauthorized');
  }
  const [user, pass] = Buffer.from(header.slice(6), 'base64').toString().split(':');
  if (user === ADMIN_USER && pass === ADMIN_PASS) return next();
  res.set('WWW-Authenticate', 'Basic realm="Timeline Admin"');
  return res.status(401).send('Unauthorized');
}
const SCENES_FILE = path.join(ROOT, 'scenes.json');
const PANORAMA_FILE = path.join(ROOT, 'panorama.json');
const UPLOADS_DIR = path.join(ROOT, 'uploads');

if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR);

// ── Middleware ──────────────────────────────────────────────
app.use(express.json({ limit: '20mb' }));
app.use(express.static(ROOT));
app.use('/uploads', express.static(UPLOADS_DIR));

// ── Multer (file uploads) ───────────────────────────────────
const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOADS_DIR),
  filename:    (_req, file, cb) => {
    const safe = file.originalname.replace(/[^\w.\-]/g, '_');
    cb(null, Date.now() + '_' + safe);
  },
});
const upload = multer({ storage, limits: { fileSize: 20 * 1024 * 1024 } });

// ── API: scenes ─────────────────────────────────────────────
app.get('/api/scenes', (_req, res) => {
  try {
    res.json(JSON.parse(fs.readFileSync(SCENES_FILE, 'utf8')));
  } catch {
    res.json({ scenes: [] });
  }
});

app.put('/api/scenes', basicAuth, (req, res) => {
  try {
    fs.writeFileSync(SCENES_FILE, JSON.stringify(req.body, null, 2), 'utf8');
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ── API: panorama ───────────────────────────────────────────
app.get('/api/panorama', (_req, res) => {
  try {
    res.json(JSON.parse(fs.readFileSync(PANORAMA_FILE, 'utf8')));
  } catch {
    res.json({ name: '', background: '', elements: [], clickAreas: [] });
  }
});

app.put('/api/panorama', basicAuth, (req, res) => {
  try {
    fs.writeFileSync(PANORAMA_FILE, JSON.stringify(req.body, null, 2), 'utf8');
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ── API: upload image ───────────────────────────────────────
app.post('/api/upload', basicAuth, upload.single('file'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file' });
  res.json({ path: '/uploads/' + req.file.filename, name: req.file.originalname });
});

// ── API: browse library ─────────────────────────────────────
app.get('/api/library', (_req, res) => {
  const LIBRARY_ROOT = path.join(ROOT, 'christmas-nativity-vector-illustrations');
  const results = [];

  function walk(dir, relBase) {
    let entries;
    try { entries = fs.readdirSync(dir); } catch { return; }
    for (const entry of entries) {
      const full    = path.join(dir, entry);
      const relPath = relBase ? relBase + '/' + entry : entry;
      const stat    = fs.statSync(full);
      if (stat.isDirectory()) {
        walk(full, relPath);
      } else if (
        entry.toLowerCase().endsWith('.png') &&
        relPath.includes('/PNG/')
      ) {
        // category = top-level folder name
        const parts    = relPath.split('/');
        const category = parts[0];
        const subcat   = parts.length > 2 ? parts[1] : '';
        results.push({
          name:     entry,
          path:     'christmas-nativity-vector-illustrations/' + relPath,
          category,
          subcat,
        });
      }
    }
  }

  walk(LIBRARY_ROOT, '');

  // Also include uploaded files
  try {
    const uploads = fs.readdirSync(UPLOADS_DIR)
      .filter(f => /\.(png|jpg|jpeg|gif|webp)$/i.test(f))
      .map(f => ({ name: f, path: '/uploads/' + f, category: 'Загруженные', subcat: '' }));
    results.push(...uploads);
  } catch {}

  res.json(results);
});

// ── API: presets (scenes.*.json files) ──────────────────────
app.get('/api/presets', (_req, res) => {
  const files = fs.readdirSync(ROOT)
    .filter(f => /^scenes\..+\.json$/.test(f))
    .map(f => {
      const name = f.replace(/^scenes\./, '').replace(/\.json$/, '');
      let title = name;
      try {
        const data = JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'));
        if (data.name) title = data.name;
      } catch {}
      return { name, file: f, title };
    });
  res.json(files);
});

app.post('/api/presets/:name/load', basicAuth, (req, res) => {
  const scenesFile = path.join(ROOT, `scenes.${req.params.name}.json`);
  if (!fs.existsSync(scenesFile)) return res.status(404).json({ error: 'Not found' });
  try {
    fs.copyFileSync(scenesFile, SCENES_FILE);
    // Also load matching panorama preset if it exists
    const panoFile = path.join(ROOT, `panorama.${req.params.name}.json`);
    if (fs.existsSync(panoFile)) fs.copyFileSync(panoFile, PANORAMA_FILE);
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/presets/:name/save', basicAuth, (req, res) => {
  const scenesFile = path.join(ROOT, `scenes.${req.params.name}.json`);
  try {
    fs.copyFileSync(SCENES_FILE, scenesFile);
    // Also save current panorama as matching preset
    fs.copyFileSync(PANORAMA_FILE, path.join(ROOT, `panorama.${req.params.name}.json`));
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ── Admin panel shortcut ────────────────────────────────────
app.get('/admin', basicAuth, (_req, res) => {
  res.sendFile(path.join(ROOT, 'admin.html'));
});

app.listen(PORT, () => {
  console.log(`\n✦  Таймлайн:  http://localhost:${PORT}`);
  console.log(`✦  Админка:   http://localhost:${PORT}/admin\n`);
});
