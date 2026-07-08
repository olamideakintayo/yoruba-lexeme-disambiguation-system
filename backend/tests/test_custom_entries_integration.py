import os
from uuid import uuid4

import pytest

from app.database import AsyncSessionLocal
from app.repository import create_custom_entry, delete_custom_entry, search_tone_variants


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="Set RUN_DB_INTEGRATION=1 to run PostgreSQL-backed integration tests.",
)


@pytest.mark.asyncio
async def test_custom_entry_manual_tone_pattern_survives_search() -> None:
    marker = f"integration tone check {uuid4()}"
    created_id = None

    async with AsyncSessionLocal() as session:
        try:
            created = await create_custom_entry(
                session,
                {
                    "word": "\u00f3w\u00f3",
                    "meaning": marker,
                    "tone_pattern": "high-low",
                    "part_of_speech": "noun",
                    "allow_override": True,
                },
            )
            created_id = created["id"]

            assert created["tone_pattern"] == "high-low"
            assert created["tone_label"] == "high-low"

            results, _ = await search_tone_variants(session, "owo")
            custom_result = next(
                item
                for item in results
                if item["source"] == "Custom User Entries" and marker in item["meanings"]
            )

            assert custom_result["word"] == "\u00f3w\u00f3"
            assert custom_result["tone_pattern"] == "high-low"
            assert custom_result["tone_label"] == "high-low"
        finally:
            if created_id is not None:
                await delete_custom_entry(session, created_id)
