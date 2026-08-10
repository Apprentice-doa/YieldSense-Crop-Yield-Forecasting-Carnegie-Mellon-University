"""Main application entry point."""

import uvicorn
from fastapi import FastAPI

from .controller import router

app = FastAPI(
    title="Qucoon AI API",
    description="AI/ML API service",
    version="1.0.0"
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)