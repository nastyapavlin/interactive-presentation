# deck-track worker

Cloudflare Worker that receives email-gate events from the deck and posts
notifications to Slack. Free tier is plenty (100k requests/day).

## One-time deploy

1. `npm install -g wrangler` (or `npx wrangler`)
2. `wrangler login` — opens the browser, log in to the Cloudflare account
3. From this folder: `wrangler deploy`
   → prints the worker URL, e.g. `https://deck-track.<subdomain>.workers.dev`
4. Create a Slack incoming webhook: Slack → Apps → "Incoming Webhooks" →
   Add to Slack → choose channel `#deck-views` → copy the webhook URL.
5. `wrangler secret put SLACK_WEBHOOK_URL` — paste the webhook when prompted.
6. Put the worker URL into `deck/index.html` (`TRACK_URL` constant, keep the
   `/track` suffix) and push.

## Test

curl -s -X POST https://deck-track.<subdomain>.workers.dev/track \
  -H 'Content-Type: application/json' \
  -d '{"deck":"demo","email":"test@example.com","event":"view"}'

Expect `{"ok":true}` and a message in #deck-views.
