# Yoruba Lexeme Disambiguation System

A single-page Yoruba lexeme disambiguation application with:

- React + TypeScript frontend
- Three.js animation through React Three Fiber
- FastAPI backend using SQLAlchemy async with psycopg
- PostgreSQL database
- Dictionary import pipeline for a local Yoruba-English PDF source

## Quick Start

```powershell
docker compose up -d db
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
python -m app.server
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173  
Backend API: http://localhost:8000/docs
PostgreSQL: localhost:55432

## Deployment

Recommended deployment:

- FastAPI backend on Render
- PostgreSQL on Render managed Postgres
- React frontend on Vercel
- Vercel calling the Render HTTPS backend URL

See [deploy/render.md](deploy/render.md) for the Render + Vercel setup.

## Dictionary Import

The primary dictionary source is `backend/data/dictionary-of-the-yoruba-language.pdf`.
The importer targets Part II, the Yoruba-English section, and writes normalized entries to
`backend/data/yoruba_english_dictionary.jsonl`.

Convert the PDF to JSONL:

```powershell
cd backend
python -m app.import_yoruba_pdf
```

If the PDF has no usable text layer, run OCR first or provide page boundaries after OCR:

```powershell
python -m app.import_yoruba_pdf --start-page 120 --end-page 457
```

The included PDF copy is a Google-scanned image PDF on this machine, so direct text
extraction may fail until OCR is performed. On Windows, the project can OCR Part II
with the built-in Windows OCR engine:

```powershell
python -m app.import_yoruba_pdf --ocr
```

If another OCR tool produces a UTF-8 text file for the Yoruba-English section, import
that text directly:

```powershell
python -m app.import_yoruba_pdf --text-file path\to\yoruba-english-ocr.txt
```

Seed PostgreSQL from the generated JSONL:

```powershell
python -m app.seed
python -m app.backfill_aliases
```

The legacy sample file remains available as a small test fixture in
`backend/data/sample_yoruba_dictionary.jsonl`.

`app.backfill_aliases` is non-destructive. It preserves the OCR-imported dictionary
entries and adds extra lookup keys for common OCR substitutions such as `Q`, `Ö`,
`å`, `$`, and `#` so search is more forgiving.

## Search Behavior

- Exact marked Yoruba matches rank first.
- Unmarked queries return all matching tonal/orthographic forms.
- Fuzzy suggestions use PostgreSQL trigram similarity when available.
- The app keeps Yoruba diacritics visible in results while using normalized keys for lookup.
