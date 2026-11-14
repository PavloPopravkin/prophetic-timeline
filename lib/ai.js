// AI calls for the timeline admin, without Azure (Pavel 03.11.2026: Azure nowhere).
// Order: Antigravity pool (OpenAI-compatible) -> Cloudflare Workers AI. Same chain as sda-bot lib/image-gen.js.
// Env: POOL_BASE_URL, POOL_API_KEY, optional POOL_IMAGE_MODELS / POOL_VISION_MODELS (comma lists);
//      CLOUDFLARE_AI_TOKEN, CLOUDFLARE_AI_ACCOUNTS (comma list), optional CF_IMAGE_MODEL.
// Model ids come from the pool catalog (cached for a day), env lists override it.
'use strict';

const DAY_MS = 24 * 3600 * 1000;
const POOL_IMAGE_TIMEOUT_MS = 180000;
const POOL_TEXT_TIMEOUT_MS = 30000;
const CF_TIMEOUT_MS = 60000;
let catalog = { at: 0, ids: [] };
let cfRr = 0;

async function fetchJson(url, init, timeoutMs) {
  const ctrl = new AbortController();
  const tm = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(url, { ...init, signal: ctrl.signal });
    const text = await r.text();
    let data = null;
    try { data = JSON.parse(text); } catch {}
    if (!r.ok || !data) throw new Error(`HTTP ${r.status}: ${(data?.error?.message || data?.errors?.[0]?.message || text).slice(0, 160)}`);
    return data;
  } finally {
    clearTimeout(tm);
  }
}

const listFromEnv = (name) => (process.env[name] || '').split(',').map(s => s.trim()).filter(Boolean);
const poolBase = () => (process.env.POOL_BASE_URL || '').replace(/\/$/, '');
const poolHeaders = () => ({ 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.POOL_API_KEY || ''}` });

async function poolCatalog() {
  if (catalog.ids.length && Date.now() - catalog.at < DAY_MS) return catalog.ids;
  const data = await fetchJson(`${poolBase()}/models`, { headers: poolHeaders() }, 15000);
  catalog = { at: Date.now(), ids: (data.data || []).map(m => m.id) };
  return catalog.ids;
}

async function imageModels() {
  const fixed = listFromEnv('POOL_IMAGE_MODELS');
  if (fixed.length) return fixed;
  return (await poolCatalog()).filter(id => /^gpt-image/.test(id)).sort().reverse();
}

async function visionModels() {
  const fixed = listFromEnv('POOL_VISION_MODELS');
  if (fixed.length) return fixed;
  const flash = (await poolCatalog()).filter(id => /^gemini.*flash/.test(id) && !/image/.test(id));
  return [...flash.filter(id => /lite/.test(id)), ...flash.filter(id => !/lite/.test(id))];
}

async function poolImage(prompt, size, model) {
  const data = await fetchJson(`${poolBase()}/images/generations`, {
    method: 'POST', headers: poolHeaders(),
    body: JSON.stringify({ model, prompt, n: 1, size }),
  }, POOL_IMAGE_TIMEOUT_MS);
  const item = data?.data?.[0];
  if (item?.b64_json) return Buffer.from(item.b64_json, 'base64');
  if (item?.url) return Buffer.from(await (await fetch(item.url)).arrayBuffer());
  throw new Error('no image in response');
}

async function cloudflareImage(prompt, model, account) {
  const data = await fetchJson(`https://api.cloudflare.com/client/v4/accounts/${account}/ai/run/${model}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.CLOUDFLARE_AI_TOKEN}` },
    body: JSON.stringify({ prompt: prompt.slice(0, 2048), steps: 4 }),
  }, CF_TIMEOUT_MS);
  const b64 = data?.result?.image;
  if (!b64) throw new Error('no image in response');
  return Buffer.from(b64, 'base64');
}

// -> { buffer, provider }; throws with every step's error when the whole chain fails.
async function generateImage(prompt, size = '1024x1024') {
  const errors = [];
  if (poolBase()) {
    let models = [];
    try { models = await imageModels(); } catch (e) { errors.push(`pool catalog: ${e.message}`); }
    for (const m of models) {
      try { return { buffer: await poolImage(prompt, size, m), provider: `pool/${m}` }; }
      catch (e) { errors.push(`pool/${m}: ${e.message}`); }
    }
  }
  const accounts = listFromEnv('CLOUDFLARE_AI_ACCOUNTS');
  if (process.env.CLOUDFLARE_AI_TOKEN && accounts.length) {
    const model = process.env.CF_IMAGE_MODEL || '@cf/black-forest-labs/flux-1-schnell';
    for (let i = 0; i < accounts.length; i++) {
      const acc = accounts[(cfRr + i) % accounts.length];
      try {
        const buffer = await cloudflareImage(prompt, model, acc);
        cfRr = (cfRr + i + 1) % accounts.length;
        return { buffer, provider: `cf/${model.split('/').pop()}` };
      } catch (e) { errors.push(`cf/${acc.slice(0, 6)}: ${e.message}`); }
    }
  }
  throw new Error(errors.length ? errors.join(' | ') : 'no image provider configured (POOL_BASE_URL or CLOUDFLARE_AI_*)');
}

// Short filename-like caption for an uploaded image (data URL). Returns '' when every model fails.
async function nameImage(imageDataUrl) {
  if (!poolBase()) return '';
  let models = [];
  try { models = await visionModels(); } catch { return ''; }
  for (const model of models) {
    try {
      const data = await fetchJson(`${poolBase()}/chat/completions`, {
        method: 'POST', headers: poolHeaders(),
        body: JSON.stringify({
          model, max_tokens: 60,
          messages: [{ role: 'user', content: [
            { type: 'text', text: 'Describe this image in 3-5 English words suitable as a filename. Only output the words, lowercase, separated by underscores. No punctuation. Examples: angel_in_light, warrior_with_sword, nativity_scene_star.' },
            { type: 'image_url', image_url: { url: imageDataUrl } },
          ] }],
        }),
      }, POOL_TEXT_TIMEOUT_MS);
      const text = (data?.choices?.[0]?.message?.content || '').trim();
      if (text) return text;
    } catch {}
  }
  return '';
}

module.exports = { generateImage, nameImage };
