from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.projects import router as projects_router
from app.api.contribution import router as contribution_router

app = FastAPI(title="CodeAtlas API")

# Lista de orígenes permitidos
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://atlas-code-neon.vercel.app",  # Tu dominio exacto de Vercel
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # O usa ["*"] para permitir cualquier origen durante las pruebas
    allow_credentials=True,
    allow_methods=["*"],    # Permite POST, GET, OPTIONS, etc.
    allow_headers=["*"],    # Permite Content-Type, Authorization, etc.
)

app.include_router(projects_router)
app.include_router(contribution_router)


@app.get("/health")
def health():
    return {"status": "ok"}