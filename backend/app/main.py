from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.projects import router as projects_router
from app.api.contribution import router as contribution_router

app = FastAPI(title="CodeAtlas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(contribution_router)


@app.get("/health")
def health():
    return {"status": "ok"}
