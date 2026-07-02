from __future__ import annotations

import asyncio
import os
import sys

import uvicorn


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    is_render = os.getenv("RENDER") == "true"
    host = os.getenv("HOST", "0.0.0.0" if is_render else "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    default_reload = "0" if is_render else "1"
    reload = os.getenv("RELOAD", default_reload) not in {"0", "false", "False"}

    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
