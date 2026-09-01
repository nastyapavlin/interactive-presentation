# Agent playbook: generate a personalized sales deck

Input from the manager (Slack or chat): client company name, plus optionally
state, segment, known pain points, portfolio parameters, meeting time.
Output: a deployed deck at `deck/?client=<slug>` and a short reply in Slack.

## Steps

1. **Research the client (web).**
   - Find the client's website; identify: what they do, segment (BHPH dealer,
     consumer lender, medical, MCA, ...), state and city, approximate scale.
   - Search news/reviews/legal mentions for signals of problems (liquidity,
     collections load, growth, regulation).
2. **Industry analytics for the challenge hypotheses.**
   - Pull 1–3 fresh industry facts for the client's segment (delinquency trends,
     cost of funds, regulatory pressure) with named sources → `client.industryInsights`.
   - Formulate 3–4 challenge hypotheses for THIS client. Manager-provided pain
     points take priority and go first.
3. **Solutions.** For each challenge pick a matching Debexpert solution
   (auction competition, ~14-day close, $0 seller fees, thousands of registered
   buyers, NDA-protected data room, recourse/non-recourse flexibility,
   sell-the-tail servicing relief). Write `solutions[]` with `challengeRef`.
4. **Data snapshots.**
   - Default: use the committed snapshots — `deck/data/buyers-latest.json` → config
     `data.buyers`, `deck/data/pricing-latest.json` merged with
     `agent/pricing_defaults.json` → `data.pricing` (snapshot rows override defaults
     by assetClass+performance; defaults fill missing classes; ensure ≥1 row has
     `clientSegment: true` for the client's segment).
   - Refresh snapshots when you can:
     `python3 agent/pricing_from_sheet.py --segment <seg> > deck/data/pricing-latest.json`
     (public Google Sheet, works everywhere);
     `python3 agent/buyers_from_powerbi.py --round > deck/data/buyers-latest.json`
     (needs Power BI auth: cached user token or `agent/.env` service principal —
     see `agent/POWERBI_SETUP.md`). PUBLIC REPO ⇒ ALWAYS `--round`.
5. **Write the config** `deck/clients/<slug>.json` following `_template.json`
   (`demo.json` = complete example). Slug: lowercase company name, hyphens.
   Set `meta.generatedAt` (now, UTC) and `meta.manager` (the requesting manager;
   default: Anastasia Pavlova, (302) 703-9387, a.pavlova@debexpert.com).
6. **Validate**: JSON parses; every `challengeRef` exists; `client.state` is a
   valid 2-letter code; pricing has a `clientSegment: true` row.
7. **Deploy**: commit and push to `main`. GitHub Pages redeploys in ~1 minute.
   Verify: `deck/clients/<slug>.json` on the live site returns the new config.
8. **Reply to the manager** (template):
   > Deck ready: https://nastyapavlin.github.io/interactive-presentation/deck/?client=<slug>
   > Challenge hypotheses: 1) …, 2) …, 3) … — correct me before the meeting if I
   > misread the client. Slides 1–2 are personalized; buyers/pricing are the
   > latest platform snapshots (as of <asOf>).

## Style rules

- Deck language: English. Tone: confident, specific, no filler.
- Challenges must read as informed hypotheses about THIS client, not generic
  complaints.
- Never invent platform statistics: buyer counts and prices only from snapshots.
  If a number is unavailable, omit the block rather than guess.
- Repo is PUBLIC: only rounded figures, never secrets, never client CRM data
  beyond what the manager explicitly provided for the deck.
