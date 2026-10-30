"""
Legacy mock webhook. Do not run this as the production server.

The canonical HTTP service is the repository root:

    uvicorn backend.app:app --port 8000
"""
raise SystemExit(
    "backend.main is a retired mock. Run `uvicorn backend.app:app --port 8000` instead. "
    "See CONTRACT.md."
)
