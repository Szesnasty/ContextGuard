"""Run the API: `python -m contextguard` (dev convenience).

Production/`make` uses uvicorn directly with the factory.
"""

from __future__ import annotations


def main() -> None:
    import uvicorn

    uvicorn.run(
        "contextguard.api.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
