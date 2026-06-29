from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.database import AsyncSessionLocal
from app.repository import import_jsonl


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import Yoruba dictionary JSONL data.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--source-name", default="Kaikki/Wiktextract")
    args = parser.parse_args()

    async with AsyncSessionLocal() as session:
        count = await import_jsonl(session, args.path, args.source_name)
    print(f"Imported {count} dictionary entries.")


if __name__ == "__main__":
    asyncio.run(main())
