/**
 * deck-track — Cloudflare Worker for the Debexpert sales deck.
 * Receives view/download events from the deck's email gate and notifies Slack.
 *
 * Secrets (set via `wrangler secret put`):
 *   SLACK_WEBHOOK_URL — Slack incoming webhook for the #deck-views channel
 *
 * POST /track  { deck, email, event: "view"|"download"|"progress", progress?, manager? }
 */

const ALLOWED_ORIGINS = [
  "https://nastyapavlin.github.io",
  "http://localhost:8734",
];
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const SLUG_RE = /^[a-z0-9-_]{1,80}$/;

function cors(origin) {
  const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors(origin) });
    }
    const url = new URL(request.url);
    if (request.method === "GET") {
      return new Response("deck-track ok", { headers: cors(origin) });
    }
    if (request.method !== "POST" || url.pathname !== "/track") {
      return new Response("not found", { status: 404, headers: cors(origin) });
    }

    let body;
    try {
      body = await request.json();
    } catch {
      return json({ ok: false, error: "bad json" }, 400, origin);
    }

    const deck = String(body.deck || "").toLowerCase();
    const email = String(body.email || "").trim().toLowerCase();
    const event = String(body.event || "view");
    const progress = Number(body.progress) || 0;
    const manager = String(body.manager || "").slice(0, 80);

    if (!SLUG_RE.test(deck)) return json({ ok: false, error: "bad deck" }, 400, origin);
    if (!EMAIL_RE.test(email)) return json({ ok: false, error: "bad email" }, 400, origin);
    if (!["view", "download", "progress"].includes(event))
      return json({ ok: false, error: "bad event" }, 400, origin);

    const deckUrl = `https://nastyapavlin.github.io/interactive-presentation/deck/?client=${deck}`;
    const icon = { view: "👀", download: "📥", progress: "📊" }[event];
    const what = {
      view: "opened the presentation",
      download: "downloaded the PDF",
      progress: `viewed ${progress} slides`,
    }[event];

    const text =
      `${icon} *${email}* ${what}\n` +
      `Deck: <${deckUrl}|${deck}>` +
      (manager ? ` · Manager: ${manager}` : "") +
      ` · ${new Date().toISOString().replace("T", " ").slice(0, 16)} UTC`;

    if (env.SLACK_WEBHOOK_URL) {
      const r = await fetch(env.SLACK_WEBHOOK_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!r.ok) return json({ ok: false, error: "slack " + r.status }, 502, origin);
    }
    return json({ ok: true }, 200, origin);
  },
};

function json(obj, status, origin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors(origin) },
  });
}
