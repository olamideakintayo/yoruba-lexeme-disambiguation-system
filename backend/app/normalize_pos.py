from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Sense
from app.repository import normalize_pos


async def main() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Sense))
        senses = result.scalars().all()
        changed = 0
        for sense in senses:
            normalized = normalize_pos(sense.part_of_speech)
            if normalized != sense.part_of_speech:
                sense.part_of_speech = normalized
                changed += 1
        await session.commit()
    print(f"Normalized part-of-speech labels for {changed} senses.")


if __name__ == "__main__":
    asyncio.run(main())
