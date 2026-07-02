from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.keyboard import CONTROL_KEYS, TONE_KEYS, YORUBA_ALPHABET
from app.normalization import normalize_lookup
from app.repository import YORUBA_ONLY_ERROR, get_lexeme, import_jsonl, search_tone_variants
from app.schemas import KeyboardResponse, LexemeRead, SearchResponse, ToneVariantResult

settings = get_settings()

app = FastAPI(
    title="Yoruba Lexeme Disambiguation API",
    description="Dictionary-backed search for Yoruba forms, tones, meanings, and suggestions.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/keyboard", response_model=KeyboardResponse)
async def keyboard() -> KeyboardResponse:
    return KeyboardResponse(alphabet=YORUBA_ALPHABET, tones=TONE_KEYS, controls=CONTROL_KEYS)


@app.get("/api/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=160),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    results, suggestions = await search_tone_variants(session, q)
    if not results:
        raise HTTPException(status_code=400, detail=YORUBA_ONLY_ERROR)
    return SearchResponse(
        query=q,
        normalized_query=normalize_lookup(q),
        results=[ToneVariantResult.model_validate(item) for item in results],
        suggestions=suggestions,
    )


@app.get("/api/suggestions")
async def suggestions(
    q: str = Query(..., min_length=1, max_length=160),
    session: AsyncSession = Depends(get_session),
) -> dict[str, list[str]]:
    _, values = await search_tone_variants(session, q, limit=8)
    return {"suggestions": values}


@app.get("/api/lexemes/{lexeme_id}", response_model=LexemeRead)
async def lexeme_detail(
    lexeme_id: str,
    session: AsyncSession = Depends(get_session),
) -> LexemeRead:
    lexeme = await get_lexeme(session, lexeme_id)
    if lexeme is None:
        raise HTTPException(status_code=404, detail="Lexeme not found")
    return LexemeRead.model_validate(lexeme)


@app.post("/api/admin/import-dictionary")
async def import_dictionary(
    path: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    count = await import_jsonl(session, __import__("pathlib").Path(path))
    return {"imported": count}
