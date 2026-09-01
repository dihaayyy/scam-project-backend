from fastapi import FastAPI

from src.auth.router import router as auth_router
from src.detections.router import router as detection_router


app = FastAPI(title="Scam Project API")

app.include_router(auth_router)
app.include_router(detection_router)