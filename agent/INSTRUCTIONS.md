# Agent instructions: generate a personalized sales deck

You are preparing a personalized Debexpert sales presentation for a client meeting.
Input from the manager (via Slack or chat): client company name, plus optionally state,
segment, known pain points, portfolio parameters, meeting time.

## Steps

1. **Research the client (web).**
   - Find the client's website; identify: what they do, segment (BHPH dealer, consumer
     lender, medical, MCA, ...), state and city, approximate scale (locations, volume).
   - Search news/reviews/legal mentions for signals of problems (liquidity, collections,
     growth, regulation).
2. **Industry analytics for the challenge hypotheses.**
   - Pull 1–3 fresh industry facts relevant to the client's segment (delinquency trends,
     cost of funds, regulatory pressure) with named sources — these go to
     `client.industryInsights` and inform `client.challenges`.
   - Formulate 3–4 challenge hypotheses: what likely hurts THIS client. Merge in any pain
     points the manager provided (those take priority and go first).
3. **Solutions.** For each challenge pick a matching Debexpert solution
   (auction competition, ~14-day close, $0 seller fees, 500+ verified buyers, NDA-protected
   data room, recourse/non-recourse flexibility, sell-the-tail servicing relief).
   Write them into `solutions` with `challengeRef` pointing at the challenge index.
4. **Data snapshots.**
   - Buyers by type and by state: run the queries in `agent/queries/` against the
     warehouse (or the agreed export). Until warehouse access is configured, reuse the
     latest committed snapshot and keep its `asOf`.
   - Pricing: run `python3 agent/pricing_from_sheet.py --segment <client-segment>`.
     It reads the team's auctions Google Sheet
     (sheet id `1mAsVUm1UnhKypInNvRn-YT-RM9qyz7wQiMVaXLHIYV4`, columns:
     Auction Number | Performing/Non-performing | Debt Type | Total Balance | Offer (%) | Offer (Price))
     and aggregates min–max Offer (%) per (Debt Type, Performance). Merge the result with
     `agent/pricing_defaults.json`: sheet rows override defaults (match by
     assetClass+performance), defaults fill in asset classes the sheet doesn't cover yet.
     Ensure at least one row has `"clientSegment": true`.
5. **Write the config** to `deck/clients/<client-slug>.json` following
   `deck/clients/_template.json`. Slug: lowercase company name, hyphens, no punctuation.
   Set `meta.generatedAt` (now, UTC) and `meta.manager` (the requesting manager).
6. **Validate**: JSON parses; every `challengeRef` exists; state code is valid;
   pricing has at least one `clientSegment: true` row.
7. **Deploy**: commit and push to the repository (GitHub Pages serves it automatically).
8. **Reply to the manager** with the deck link:
   `https://<pages-domain>/deck/?client=<client-slug>` and a 2-line summary of the
   challenge hypotheses you chose (so the manager can correct them before the meeting).

## Style rules

- Deck language: English. Tone: confident, specific, no filler.
- Challenges must read as informed hypotheses about THIS client, not generic complaints.
- Never invent platform statistics: buyer counts and prices come only from the data
  snapshots. If a number is unavailable, omit the block rather than guess.
