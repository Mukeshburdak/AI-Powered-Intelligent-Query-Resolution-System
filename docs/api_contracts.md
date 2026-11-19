# API Contracts (starter)

- `GET /health` — health check.
- `POST /api/upload` — multipart file upload (`.txt`, `.pdf`, `.docx`); extracts text and reports chunk count.
- `POST /api/query` — JSON body: `{"question": "…", "conversation_id": null}`. Returns a baseline response until retrieval is implemented.
- `GET /api/history/{conversation_id}` — placeholder history response.
- `POST /api/feedback` — JSON body with `query_id`, `rating` (1–5), optional `comment`.
- `GET /api/analytics/summary` — placeholder analytics summary.
