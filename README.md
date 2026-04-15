# FeedOptima

FeedOptima is an AI-enabled livestock feed ration optimization platform for Indian farmers.

## Quick Preview

To see a working demo:

1. **Start Backend**: Double-click `start_backend.bat` or run:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start Frontend**: Double-click `start_frontend.bat` or run:
   ```bash
   cd frontend
   python -m http.server 3000
   ```

3. **Open Browser**: Go to `http://localhost:3000` to use the web interface

## Backend

The backend lives in `backend/` and provides:
- Rule-based ration optimization for cattle, buffalo, goat, sheep, and poultry
- Public-source scraping support for TNAU feed ingredient names
- Modular nutrition requirement and feed ingredient data

## Getting started

1. Create a virtual environment in `backend/`
2. Install dependencies from `backend/requirements.txt`
3. Run the API with:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /health`
- `POST /ration/optimize`
- `GET /scrape/tnau`
- `GET /scrape/market-prices`
- `GET /catalog`
- `POST /catalog/seed`
- `POST /catalog/ingredient`
- `POST /catalog/prices`
- `POST /catalog/sync-market-prices`

## Notes

- The backend is intentionally simple and cloud-ready; it is not tied to Supabase.
- Use `DATABASE_URL` in `.env` for future PostgreSQL support.
- Use the scraper endpoint to seed local feed catalogs from public sources.
