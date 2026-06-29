from __future__ import annotations

import asyncio

from app.database import AsyncSessionLocal
from app.repository import backfill_word_form_aliases


async def main() -> None:
    async with AsyncSessionLocal() as session:
        count = await backfill_word_form_aliases(session)
    print(f"Backfilled aliases for {count} word forms.")


if __name__ == "__main__":
    asyncio.run(main())
