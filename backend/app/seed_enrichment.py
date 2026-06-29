from __future__ import annotations

import asyncio
from pathlib import Path

from app.database import AsyncSessionLocal
from app.repository import import_jsonl


async def main() -> None:
    path = Path(__file__).resolve().parent.parent / "data" / "online_yoruba_enrichment.jsonl"
    if not path.exists():
        raise SystemExit("Missing backend/data/online_yoruba_enrichment.jsonl.")
    async with AsyncSessionLocal() as session:
        count = await import_jsonl(session, path, "Online Yoruba Enrichment")
    print(f"Seeded {count} online enrichment entries.")


if __name__ == "__main__":
    asyncio.run(main())
