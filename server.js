const express  = require('express');
const multer   = require('multer');
const fs       = require('fs');
const path     = require('path');
const https    = require('https');
const http     = require('http');
const { spawn } = require('child_process');

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

// ── API: name image with Azure OpenAI vision ────────────────
app.post('/api/name-image', basicAuth, async (req, res) => {
  const { imageBase64 } = req.body;
  if (!imageBase64) return res.status(400).json({ error: 'No image' });

  const AZURE_KEY      = process.env.AZURE_API_KEY;
  const AZURE_BASE     = process.env.AZURE_BASE_URL;
  const AZURE_MODEL    = process.env.AZURE_MODEL;

  const payload = JSON.stringify({
    model: AZURE_MODEL,
    messages: [{
      role: 'user',
      content: [
        { type: 'text', text: 'Describe this image in 3-5 English words suitable as a filename. Only output the words, lowercase, separated by underscores. No punctuation. Examples: angel_in_light, warrior_with_sword, nativity_scene_star.' },
        { type: 'image_url', image_url: { url: imageBase64 } }
      ]
    }],
    max_tokens: 30
  });

  try {
    const url = new URL(AZURE_BASE + '/chat/completions');
    const result = await new Promise((resolve, reject) => {
      const options = {
        hostname: url.hostname,
        path:     url.pathname + url.search,
        method:   'POST',
        headers:  {
          'Content-Type':   'application/json',
          'api-key':        AZURE_KEY,
          'Authorization':  'Bearer ' + AZURE_KEY,
          'Content-Length': Buffer.byteLength(payload),
        },
      };
      const r = https.request(options, resp => {
        let body = '';
        resp.on('data', c => body += c);
        resp.on('end', () => resolve({ status: resp.statusCode, body }));
      });
      r.on('error', reject);
      r.write(payload);
      r.end();
    });
    const data = JSON.parse(result.body);
    const raw  = (data.choices?.[0]?.message?.content || '').trim();
    const name = raw.replace(/[^a-z0-9_]/gi, '_').replace(/_+/g, '_').replace(/^_|_$/g, '').toLowerCase() || 'edited_image';
    res.json({ name });
  } catch (e) {
    res.json({ name: 'edited_image' });
  }
});

// ── API: AI Image Generation (MAI-Image-2 via Azure) ────────
app.post('/api/generate-image', basicAuth, async (req, res) => {
  const { prompt, size = '1024x1024', n = 1 } = req.body;
  if (!prompt) return res.status(400).json({ error: 'prompt required' });

  const apiKey = process.env.AZURE_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'AZURE_API_KEY not set' });

  const body = JSON.stringify({ prompt, size, n, style: 'vivid', quality: 'standard' });

  const options = {
    hostname: 'dmytropopravkin-0944-resource.cognitiveservices.azure.com',
    path: '/openai/deployments/MAI-Image-2/images/generations?api-version=2025-04-01-preview',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'api-key': apiKey,
      'Content-Length': Buffer.byteLength(body),
    },
  };

  const request = https.request(options, (response) => {
    let data = '';
    response.on('data', chunk => data += chunk);
    response.on('end', () => {
      try {
        const json = JSON.parse(data);
        if (json.error) return res.status(502).json({ error: json.error.message });

        const item = json.data?.[0];
        if (!item) return res.status(502).json({ error: 'No image in response' });

        if (item.b64_json) {
          // Save to uploads and return URL
          const filename = `ai_${Date.now()}.png`;
          const filepath = path.join(UPLOADS_DIR, filename);
          fs.writeFileSync(filepath, Buffer.from(item.b64_json, 'base64'));
          res.json({ url: `/uploads/${filename}`, filename });
        } else if (item.url) {
          res.json({ url: item.url });
        } else {
          res.status(502).json({ error: 'Unknown response format', raw: json });
        }
      } catch (e) {
        res.status(502).json({ error: 'Parse error', raw: data.slice(0, 200) });
      }
    });
  });

  request.on('error', e => res.status(502).json({ error: e.message }));
  request.write(body);
  request.end();
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

app.listen(PORT, () => {
  console.log(`\n✦  Таймлайн:  http://localhost:${PORT}`);
  console.log(`✦  Админка:   http://localhost:${PORT}/admin\n`);
});
