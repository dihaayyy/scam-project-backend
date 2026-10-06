from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.detections.router import router as detection_router
from src.config import settings


app = FastAPI(title="Scam Project API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(detection_router)

@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}