const express  = require('express');
const multer   = require('multer');
const fs       = require('fs');
const path     = require('path');
const https    = require('https');
const http     = require('http');
const { spawn } = require('child_process');
const ai       = require('./lib/ai');

// Load .env if present (no dotenv dependency needed)
try {
  fs.readFileSync(path.join(__dirname, '.env'), 'utf8')
    .split('\n').forEach(line => {
      const m = line.match(/^([A-Z_]+)\s*=\s*(.+)$/);
      if (m && !process.env[m[1]]) process.env[m[1]] = m[2].trim();
    });
} catch (_) {}

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
const THUMBS_DIR  = path.join(ROOT, 'thumbs');

if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR);
if (!fs.existsSync(THUMBS_DIR))  fs.mkdirSync(THUMBS_DIR);

// ── Middleware ──────────────────────────────────────────────
app.use(express.json({ limit: '20mb' }));
app.use(express.static(ROOT));
app.use('/uploads', express.static(UPLOADS_DIR));
app.use('/thumbs',  express.static(THUMBS_DIR));

// ── Thumbnail generation (Pillow) ───────────────────────────
const THUMB_PY = `
import sys, os
from PIL import Image
src, dst, size = sys.argv[1], sys.argv[2], int(sys.argv[3])
try:
    img = Image.open(src)
    img.thumbnail((size, size * 4), Image.LANCZOS)
    img.save(dst, 'WEBP', quality=72, method=4)
except Exception as e:
    sys.exit(1)
`;

function thumbName(filePath) {
  return filePath.replace(/[^a-zA-Z0-9._-]/g, '_') + '.webp';
}

function makeThumb(absPath, cb) {
  const tName = thumbName(absPath);
  const tPath = path.join(THUMBS_DIR, tName);
  if (fs.existsSync(tPath)) return cb(null, '/thumbs/' + tName);
  const proc = spawn('python3', ['-c', THUMB_PY, absPath, tPath, '140']);
  proc.on('close', code => cb(code === 0 ? null : new Error('thumb failed'), '/thumbs/' + tName));
}

// Pre-generate missing thumbnails in background after startup
function pregenAllThumbs() {
  const LIBRARY_ROOT = path.join(ROOT, 'christmas-nativity-vector-illustrations');
  const files = [];
  function walk(dir) {
    try { fs.readdirSync(dir).forEach(e => {
      const full = path.join(dir, e);
      if (fs.statSync(full).isDirectory()) walk(full);
      else if (e.toLowerCase().endsWith('.png') && full.includes('/PNG/')) files.push(full);
    }); } catch {}
  }
  walk(LIBRARY_ROOT);
  try { fs.readdirSync(UPLOADS_DIR).filter(f => /\.(png|jpg|jpeg|webp)$/i.test(f)) // skip svg
    .forEach(f => files.push(path.join(UPLOADS_DIR, f))); } catch {}

  let i = 0;
  function next() {
    if (i >= files.length) return;
    const f = files[i++];
    const tPath = path.join(THUMBS_DIR, thumbName(f));
    if (fs.existsSync(tPath)) { next(); return; }
    makeThumb(f, () => next());
  }
  // Run 4 workers in parallel
  for (let w = 0; w < 4; w++) next();
}
setTimeout(pregenAllThumbs, 3000);

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
// Default project shown at root URL (no ?p= param)
const HOME_PROJECT = process.env.HOME_PROJECT || 'spiritual';

app.get('/api/scenes', (_req, res) => {
  try {
    res.json(JSON.parse(fs.readFileSync(SCENES_FILE, 'utf8')));
  } catch {
    res.json({ scenes: [] });
  }
});

// Public config (home project name etc.)
app.get('/api/config', (_req, res) => {
  res.json({ homeProject: HOME_PROJECT });
});

// Read-only: scenes for a specific preset (doesn't change active)
app.get('/api/scenes/:name', (req, res) => {
  const name = req.params.name.replace(/[^a-z0-9_-]/gi, '');
  const file = path.join(ROOT, `scenes.${name}.json`);
  try {
    res.json(JSON.parse(fs.readFileSync(file, 'utf8')));
  } catch {
    res.status(404).json({ error: 'Project not found', name });
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

// Read-only: panorama for a specific preset
app.get('/api/panorama/:name', (req, res) => {
  const name = req.params.name.replace(/[^a-z0-9_-]/gi, '');
  const file = path.join(ROOT, `panorama.${name}.json`);
  try {
    res.json(JSON.parse(fs.readFileSync(file, 'utf8')));
  } catch {
    // Fall back to active panorama
    try {
      res.json(JSON.parse(fs.readFileSync(PANORAMA_FILE, 'utf8')));
    } catch {
      res.json({ name: '', background: '', elements: [], clickAreas: [] });
    }
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
      .filter(f => /\.(png|jpg|jpeg|gif|webp|svg)$/i.test(f))
      .map(f => ({ name: f, path: '/uploads/' + f, category: 'Загруженные', subcat: '' }));
    results.push(...uploads);
  } catch {}

  // Attach thumb paths (use pre-generated if available)
  const withThumbs = results.map(item => {
    const absPath = path.join(ROOT, item.path.replace(/^\//, ''));
    const tFile   = thumbName(absPath);
    const thumb   = fs.existsSync(path.join(THUMBS_DIR, tFile)) ? '/thumbs/' + tFile : null;
    return { ...item, thumb };
  });

  res.json(withThumbs);
});

// ── API: presets (scenes.*.json files) ──────────────────────
// Helper: generate a URL-safe slug from a string
function toSlug(str) {
  return str.toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    || 'project';
}

app.get('/api/presets', (_req, res) => {
  const files = fs.readdirSync(ROOT)
    .filter(f => /^scenes\..+\.json$/.test(f))
    .map(f => {
      const name = f.replace(/^scenes\./, '').replace(/\.json$/, '');
      let title = name, sceneCount = 0, thumb = null, slug = name;
      try {
        const data = JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'));
        if (data.name) title = data.name;
        if (data.slug) slug = data.slug;
        if (Array.isArray(data.scenes)) {
          sceneCount = data.scenes.length;
          const firstBg = data.scenes.find(s => s.bg && !s.bg_video);
          if (firstBg) thumb = firstBg.bg;
        }
      } catch {}
      return { name, file: f, title, sceneCount, thumb, slug };
    });
  res.json(files);
});

// Resolve a public slug → preset name (checks slug field, then preset name)
app.get('/api/resolve-slug/:slug', (req, res) => {
  const slug = req.params.slug.replace(/[^a-z0-9_-]/gi, '-').toLowerCase();
  const files = fs.readdirSync(ROOT).filter(f => /^scenes\..+\.json$/.test(f));
  for (const f of files) {
    try {
      const data = JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'));
      const name = f.replace(/^scenes\./, '').replace(/\.json$/, '');
      const fileSlug = data.slug || name;
      if (fileSlug === slug || name === slug) {
        return res.json({ preset: name, slug: fileSlug, title: data.name || name });
      }
    } catch {}
  }
  res.status(404).json({ error: 'Not found', slug });
});

// Set a custom slug for a preset
app.post('/api/presets/:name/set-slug', basicAuth, (req, res) => {
  const safeName = req.params.name.replace(/[^a-z0-9_-]/gi, '_').toLowerCase();
  const raw = (req.body.slug || '').trim();
  const slug = raw ? toSlug(raw) : safeName;
  const file = path.join(ROOT, `scenes.${safeName}.json`);
  try {
    const data = JSON.parse(fs.readFileSync(file, 'utf8'));
    data.slug = slug;
    fs.writeFileSync(file, JSON.stringify(data, null, 2));
    res.json({ ok: true, slug });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/presets/:name/load', basicAuth, (req, res) => {
  const scenesFile = path.join(ROOT, `scenes.${req.params.name}.json`);
  if (!fs.existsSync(scenesFile)) return res.status(404).json({ error: 'Not found' });
  try {
    // Auto-save the previous project before switching (if provided)
    const prev = (req.body && req.body.prev || '').replace(/[^a-z0-9_-]/gi, '_').toLowerCase();
    if (prev && prev !== req.params.name) {
      const prevScenes = path.join(ROOT, `scenes.${prev}.json`);
      const prevPano   = path.join(ROOT, `panorama.${prev}.json`);
      if (fs.existsSync(SCENES_FILE))   fs.copyFileSync(SCENES_FILE,   prevScenes);
      if (fs.existsSync(PANORAMA_FILE)) fs.copyFileSync(PANORAMA_FILE, prevPano);
    }
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

// Save only panorama to a named preset file (called after editing panorama in admin)
app.post('/api/presets/:name/save-panorama', basicAuth, (req, res) => {
  const safeName = req.params.name.replace(/[^a-z0-9_-]/gi, '_').toLowerCase();
  const destFile = path.join(ROOT, `panorama.${safeName}.json`);
  try {
    fs.copyFileSync(PANORAMA_FILE, destFile);
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/presets/:name/create', basicAuth, (req, res) => {
  const safeName = req.params.name.replace(/[^a-z0-9_-]/gi, '_').toLowerCase();
  if (!safeName) return res.status(400).json({ error: 'Invalid name' });
  const scenesFile = path.join(ROOT, `scenes.${safeName}.json`);
  try {
    // Copy current scenes.json as the new preset (or create blank)
    if (fs.existsSync(SCENES_FILE)) {
      fs.copyFileSync(SCENES_FILE, scenesFile);
    } else {
      fs.writeFileSync(scenesFile, JSON.stringify({ name: req.params.name, scenes: [] }));
    }
    if (fs.existsSync(PANORAMA_FILE)) {
      fs.copyFileSync(PANORAMA_FILE, path.join(ROOT, `panorama.${safeName}.json`));
    }
    res.json({ ok: true, name: safeName });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/presets/:name', basicAuth, (req, res) => {
  const safeName = req.params.name.replace(/[^a-z0-9_-]/gi, '_').toLowerCase();
  try {
    const sf = path.join(ROOT, `scenes.${safeName}.json`);
    const pf = path.join(ROOT, `panorama.${safeName}.json`);
    if (fs.existsSync(sf)) fs.unlinkSync(sf);
    if (fs.existsSync(pf)) fs.unlinkSync(pf);
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ── Public project URLs (/p/:slug) ──────────────────────────
app.get('/p/:slug', (_req, res) => {
  res.sendFile(path.join(ROOT, 'index.html'));
});

// ── Admin panel ─────────────────────────────────────────────
// /admin → project picker; /admin/editor → editor
app.get('/admin', basicAuth, (_req, res) => {
  res.sendFile(path.join(ROOT, 'projects.html'));
});
app.get('/admin/editor', basicAuth, (_req, res) => {
  res.sendFile(path.join(ROOT, 'admin.html'));
});

// ── API: remove background (AI) ────────────────────────────
app.post('/api/remove-bg', basicAuth, (req, res) => {
  const { src, model = 'u2net', points, rect } = req.body;
  if (!src) return res.status(400).json({ error: 'src required' });

  const inputPath = path.join(ROOT, src.replace(/^\//, ''));
  if (!fs.existsSync(inputPath)) return res.status(404).json({ error: 'File not found: ' + src });

  const base    = path.basename(inputPath, path.extname(inputPath)).replace(/_no_bg.*$/, '');
  const outName = base + '_no_bg_' + Date.now() + '.webp';
  const outPath = path.join(UPLOADS_DIR, outName);

  const args = [path.join(ROOT, 'remove_bg.py'), inputPath, '--output', outPath, '--model', model];
  if (points) points.split(';').filter(Boolean).forEach(p => args.push('--point', p.trim()));
  if (rect)   args.push('--rect', rect.trim());

  let stderr = '';
  const proc = spawn('python3', args, { cwd: ROOT });
  proc.stderr.on('data', d => { stderr += d; });
  proc.on('close', code => {
    if (code !== 0 || !fs.existsSync(outPath))
      return res.status(500).json({ error: stderr.split('\n').filter(Boolean).pop() || 'Failed' });
    res.json({ ok: true, path: '/uploads/' + outName });
  });
});

// ── API: image search (Pexels / Pixabay proxy) ─────────────
app.get('/api/image-search', (_req, res) => {
  const q      = (_req.query.q || '').trim();
  const source = (_req.query.source || 'pexels').toLowerCase();
  const limit  = Math.min(parseInt(_req.query.limit) || 80, 80);
  const page   = Math.max(parseInt(_req.query.page)  || 1, 1);
  if (!q) return res.status(400).json({ error: 'q required' });

  if (source === 'pixabay') {
    const key = process.env.PIXABAY_API_KEY;
    if (!key) return res.status(503).json({ error: 'PIXABAY_API_KEY not set' });
    const imgType = ['all','photo','illustration','vector'].includes(_req.query.image_type) ? _req.query.image_type : 'all';
    const url = `https://pixabay.com/api/?key=${key}&q=${encodeURIComponent(q)}&image_type=${imgType}&per_page=${limit}&page=${page}&safesearch=true`;
    _httpsGet(url, {}, (err, data) => {
      if (err) return res.status(502).json({ error: err });
      const hits = (data.hits || []).map(h => ({
        id: h.id, src: h.largeImageURL, url: h.largeImageURL, thumb: h.webformatURL,
        width: h.imageWidth, height: h.imageHeight,
        description: h.tags, author: h.user, source: 'pixabay', page_url: h.pageURL,
      }));
      res.json({ source: 'pixabay', query: q, results: hits });
    });

  } else {
    const key = process.env.PEXELS_API_KEY;
    if (!key) return res.status(503).json({ error: 'PEXELS_API_KEY not set' });
    const url = `https://api.pexels.com/v1/search?query=${encodeURIComponent(q)}&per_page=${limit}&page=${page}`;
    _httpsGet(url, { Authorization: key }, (err, data) => {
      if (err) return res.status(502).json({ error: err });
      const photos = (data.photos || []).map(p => ({
        id: p.id, url: p.src.large2x || p.src.large || p.src.original,
        thumb: p.src.medium, width: p.width, height: p.height,
        description: p.alt || '', author: p.photographer,
        source: 'pexels', page_url: p.url,
      }));
      res.json({ source: 'pexels', query: q, results: photos });
    });
  }
});

function _httpsGet(url, headers, cb) {
  const mod = url.startsWith('https') ? https : http;
  const opts = Object.assign(require('url').parse(url), { headers });
  let raw = '';
  mod.get(opts, r => {
    r.on('data', c => raw += c);
    r.on('end', () => {
      try { cb(null, JSON.parse(raw)); }
      catch(e) { cb('Invalid JSON from upstream'); }
    });
  }).on('error', e => cb(e.message));
}

// ── API: fetch remote image → uploads ──────────────────────
app.post('/api/image-fetch', basicAuth, async (req, res) => {
  const { url, filename } = req.body;
  if (!url) return res.status(400).json({ error: 'url required' });

  const ext  = (url.split('?')[0].match(/\.(jpg|jpeg|png|webp|gif)$/i) || ['', '.jpg'])[1].toLowerCase();
  const safe = (filename || path.basename(url.split('?')[0])).replace(/[^\w.\-]/g, '_').replace(/\.[^.]+$/, '');
  const outName = Date.now() + '_' + safe + ext;
  const outPath = path.join(UPLOADS_DIR, outName);

  const mod = url.startsWith('https') ? https : http;
  const file = fs.createWriteStream(outPath);

  const doFetch = (fetchUrl, redirects = 0) => {
    if (redirects > 5) { file.destroy(); return res.status(502).json({ error: 'Too many redirects' }); }
    const parsedUrl = require('url').parse(fetchUrl);
    const fetchMod  = fetchUrl.startsWith('https') ? https : http;
    fetchMod.get(parsedUrl, r => {
      if (r.statusCode >= 300 && r.statusCode < 400 && r.headers.location) {
        return doFetch(r.headers.location, redirects + 1);
      }
      if (r.statusCode !== 200) {
        file.destroy();
        return res.status(502).json({ error: `Upstream returned ${r.statusCode}` });
      }
      r.pipe(file);
      file.on('finish', () => {
        file.close();
        res.json({ ok: true, path: '/uploads/' + outName });
      });
    }).on('error', e => {
      file.destroy();
      fs.unlink(outPath, () => {});
      res.status(502).json({ error: e.message });
    });
  };
  doFetch(url);
});

// ── API: name image (vision via Antigravity pool, no Azure) ─
app.post('/api/name-image', basicAuth, async (req, res) => {
  const { imageBase64 } = req.body;
  if (!imageBase64) return res.status(400).json({ error: 'No image' });
  let raw = '';
  try { raw = await ai.nameImage(imageBase64); } catch (_) {}
  const name = raw.replace(/[^a-z0-9_]/gi, '_').replace(/_+/g, '_').replace(/^_|_$/g, '').toLowerCase() || 'edited_image';
  res.json({ name });
});

// ── API: AI image generation (pool -> Cloudflare, no Azure) ─
app.post('/api/generate-image', basicAuth, async (req, res) => {
  const { prompt, size = '1024x1024' } = req.body;
  if (!prompt) return res.status(400).json({ error: 'prompt required' });
  try {
    const { buffer, provider } = await ai.generateImage(prompt, size);
    const ext = buffer[0] === 0xff && buffer[1] === 0xd8 ? 'jpg' : 'png';
    const filename = `ai_${Date.now()}.${ext}`;
    fs.writeFileSync(path.join(UPLOADS_DIR, filename), buffer);
    res.json({ url: `/uploads/${filename}`, filename, provider });
  } catch (e) {
    res.status(502).json({ error: String(e.message || e).slice(0, 300) });
  }
});

// ── API: delete uploaded file ────────────────────────────
app.post('/api/delete-upload', basicAuth, (req, res) => {
  const { path: filePath } = req.body;
  if (!filePath) return res.status(400).json({ error: 'path required' });
  // Only allow deleting from /uploads/
  const safeName = path.basename(filePath);
  const absPath = path.join(UPLOADS_DIR, safeName);
  if (!absPath.startsWith(UPLOADS_DIR + path.sep) && absPath !== UPLOADS_DIR) {
    return res.status(400).json({ error: 'invalid path' });
  }
  try {
    if (fs.existsSync(absPath)) fs.unlinkSync(absPath);
    // Also remove thumb if exists
    const tFile = path.join(THUMBS_DIR, thumbName(absPath));
    if (fs.existsSync(tFile)) fs.unlinkSync(tFile);
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// ── API: save recolored SVG ─────────────────────────────
app.post('/api/save-svg', basicAuth, (req, res) => {
  const { content, originalPath } = req.body;
  if (!content) return res.status(400).json({ error: 'content required' });
  const base = path.basename((originalPath || 'image').replace(/\.[^.]+$/, ''));
  const filename = base + '_recolored_' + Date.now() + '.svg';
  const filepath = path.join(UPLOADS_DIR, filename);
  try {
    fs.writeFileSync(filepath, content, 'utf8');
    res.json({ path: '/uploads/' + filename });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.listen(PORT, process.env.BIND || '0.0.0.0', () => {
  console.log(`\n✦  Таймлайн:  http://localhost:${PORT}`);
  console.log(`✦  Админка:   http://localhost:${PORT}/admin\n`);
});
