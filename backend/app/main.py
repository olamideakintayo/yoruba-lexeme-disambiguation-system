from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.keyboard import CONTROL_KEYS, TONE_KEYS, YORUBA_ALPHABET
from app.normalization import normalize_lookup
from app.repository import (
    YORUBA_ONLY_ERROR,
    create_custom_entry,
    delete_custom_entry,
    get_lexeme,
    import_jsonl,
    list_custom_entries,
    search_tone_variants,
    validate_custom_word,
)
from app.schemas import (
    CustomEntryCreate,
    CustomEntryRead,
    KeyboardResponse,
    LexemeRead,
    SearchResponse,
    ToneVariantResult,
    WordValidationRequest,
    WordValidationResponse,
)

settings = get_settings()

app = FastAPI(
    title="Yoruba Lexeme Disambiguation API",
    description="Dictionary-backed search for Yoruba forms, tones, meanings, and suggestions.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(
        {
            settings.frontend_origin,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        }
    ),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_admin_token(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token.")


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "service": "yoruba-lexeme-api"}


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
    _: None = Depends(require_admin_token),
) -> dict[str, int]:
    count = await import_jsonl(session, __import__("pathlib").Path(path))
    return {"imported": count}


@app.post("/api/admin/validate-word", response_model=WordValidationResponse)
async def validate_word(
    payload: WordValidationRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin_token),
) -> WordValidationResponse:
    return WordValidationResponse.model_validate(await validate_custom_word(session, payload.word))


@app.get("/api/admin/custom-entries", response_model=list[CustomEntryRead])
async def custom_entries(
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin_token),
) -> list[CustomEntryRead]:
    return [CustomEntryRead.model_validate(entry) for entry in await list_custom_entries(session)]


@app.post("/api/admin/custom-entries", response_model=CustomEntryRead)
async def add_custom_entry(
    payload: CustomEntryCreate,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin_token),
) -> CustomEntryRead:
    try:
        entry = await create_custom_entry(session, payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return CustomEntryRead.model_validate(entry)


@app.delete("/api/admin/custom-entries/{lexeme_id}")
async def remove_custom_entry(
    lexeme_id: str,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_admin_token),
) -> dict[str, bool]:
    try:
        deleted = await delete_custom_entry(session, lexeme_id)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Custom entry not found.")
    return {"deleted": True}
