# Power BI: one-time setup for the deck agent

The agent pulls buyer counts (by type, by state) straight from the Power BI dataset
via the REST API at deck-generation time. One-time setup by a Power BI / Azure admin:

## 1. Register a service principal (Azure AD)
1. Azure Portal → Microsoft Entra ID → App registrations → **New registration**
   (name e.g. `deck-agent`, single tenant, no redirect URI).
2. Copy **Application (client) ID** and **Directory (tenant) ID**.
3. Certificates & secrets → **New client secret** → copy the secret **value** immediately.

## 2. Allow service principals in Power BI
1. Power BI Admin portal → Tenant settings → Developer settings →
   **Service principals can use Fabric APIs** → Enable (scope to a security group
   containing `deck-agent` — recommended).

## 3. Grant dataset access
1. Create an Entra **security group**, add the `deck-agent` app to it.
2. In the Power BI **workspace** that hosts the buyers dataset:
   Manage access → add the group (or the app) as **Viewer** (Member if Viewer
   is blocked for executeQueries by tenant policy).
3. Dataset id: open the dataset in the browser — the URL looks like
   `.../groups/<workspace-id>/datasets/<dataset-id>/...` — copy `<dataset-id>`.

## 4. Configure the agent
Create `agent/.env` (this file is git-ignored — NEVER commit it):

```
PBI_TENANT_ID=...
PBI_CLIENT_ID=...
PBI_CLIENT_SECRET=...
PBI_DATASET_ID=...
```

## 5. Adapt the DAX to the model
Edit `agent/queries/buyers_by_type.dax` and `buyers_by_state.dax`, replacing the
placeholder table/column names with the real ones from the dataset
(the same fields the current Power BI report uses for buyer type and state).

## 6. Test
```
python3 agent/buyers_from_powerbi.py
```
Expected: JSON with `byType` (list of {type, count}) and `byState` ({"TX": 87, ...}).
The agent pastes this straight into `data.buyers` of a client config.

## Limits & notes
- executeQueries API: max 100k rows / 15 MB per query — our aggregates are tiny.
- The secret expires (default 6–24 months) — put a reminder to rotate it.
- The service principal has read-only Viewer access; it cannot modify reports.
