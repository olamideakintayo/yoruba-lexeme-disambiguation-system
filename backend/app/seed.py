from __future__ import annotations

import asyncio
from pathlib import Path

from app.database import AsyncSessionLocal
from app.repository import import_jsonl


async def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    enrichment_path = data_dir / "online_yoruba_enrichment.jsonl"
    dictionary_path = data_dir / "yoruba_english_dictionary.jsonl"
    if not dictionary_path.exists():
        raise SystemExit(
            "Missing backend/data/yoruba_english_dictionary.jsonl. Run "
            "`python -m app.import_yoruba_pdf` after creating an OCR/text-layer PDF."
        )
    async with AsyncSessionLocal() as session:
        enrichment_count = 0
        if enrichment_path.exists():
            enrichment_count = await import_jsonl(session, enrichment_path, "Online Yoruba Enrichment")
        dictionary_count = await import_jsonl(session, dictionary_path, "Dictionary of the Yoruba Language")
    print(
        f"Seeded {enrichment_count} online enrichment entries and "
        f"{dictionary_count} Yoruba-English dictionary entries."
    )


if __name__ == "__main__":
    asyncio.run(main())
