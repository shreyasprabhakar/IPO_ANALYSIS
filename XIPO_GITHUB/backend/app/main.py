from fastapi import FastAPI
from app.routes.health import router as health_router
from app.routes.sebi import router as sebi_router
from app.routes.download import router as download_router
from app.routes.extract import router as extract_router
from app.routes.chunk import router as chunk_router
from app.routes.faiss_build import router as faiss_build_router
from app.routes.rag import router as rag_router
from app.routes.financials import router as financials_router
from app.routes.healthscore import router as healthscore_router
from app.routes.report import router as report_router
from app.routes.analyze import router as analyze_router

app = FastAPI(title="XIPO Backend API")

app.include_router(health_router, prefix="/api")
app.include_router(sebi_router, prefix="/api")
app.include_router(download_router, prefix="/api")
app.include_router(extract_router, prefix="/api")
app.include_router(chunk_router, prefix="/api")
app.include_router(faiss_build_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(financials_router, prefix="/api")
app.include_router(healthscore_router, prefix="/api")
app.include_router(report_router, prefix="/api")
app.include_router(analyze_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "XIPO backend running"}
