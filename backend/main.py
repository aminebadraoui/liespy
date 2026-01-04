from fastapi import FastAPI
from backend.core.config import settings
from backend.api.routes import router as api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

@app.get("/")
async def root():
    return {"message": "LieSpy API is running", "docs": "/docs"}

app.include_router(api_router, prefix=settings.API_V1_STR)
