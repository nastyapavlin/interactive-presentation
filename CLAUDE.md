# Debexpert Interactive Sales Deck

This repo hosts a personalized sales presentation (GitHub Pages) plus the agent
tooling that generates per-client configs. A manager asks Claude (via Slack or
any session) to "prepare a deck for <client>" — the agent researches the client,
builds `deck/clients/<slug>.json`, pushes, and replies with the deck link.

**Live URL pattern:** `https://nastyapavlin.github.io/test/deck/?client=<slug>`

## When asked to prepare a deck for a client

Follow `agent/INSTRUCTIONS.md` — the complete playbook. Summary:
1. Research the client on the web (site, state, segment, likely pain points)
   and current industry stats for their segment.
2. Data: use fresh snapshots committed in `deck/data/buyers-latest.json` and
   `deck/data/pricing-latest.json`. Regenerate them only if you can run
   `python3 agent/buyers_from_powerbi.py --round` (needs local Power BI auth) and
   `python3 agent/pricing_from_sheet.py --segment <seg>` (public sheet, always works).
3. Copy `deck/clients/_template.json` → `deck/clients/<slug>.json`, fill it in
   (see `demo.json` for a complete example). English only.
4. Validate JSON, commit, push to `main` — GitHub Pages redeploys automatically
   (~1 min). Verify the live URL returns the new config.
5. Reply with the link + 2-line summary of the challenge hypotheses you chose.

## Hard rules

- This repo is PUBLIC. Never commit exact internal platform figures — buyers
  data must come from the `--round` mode or the committed rounded snapshot.
  Never commit secrets; `agent/.env` and `agent/.pbi_token.json` are git-ignored.
- Deck content is English; keep the confident, specific tone of `demo.json`.
- Don't invent platform statistics — only snapshot data. No number → omit block.

## Repo map

- `deck/index.html` — the presentation SPA (10 slides, reads `?client=<slug>`)
- `deck/clients/` — per-client configs (`_template.json` = schema, `demo.json` = example)
- `deck/data/` — rounded data snapshots (buyers from Power BI, pricing from Google Sheet)
- `agent/` — playbook + data scripts (`INSTRUCTIONS.md`, `buyers_from_powerbi.py`,
  `pricing_from_sheet.py`, `pbi_auth.py`, DAX in `queries/`)
- `docs/TZ.md` — full technical specification (Russian)
- `index.html` (root) — separate BHPH landing page, unrelated to the deck
