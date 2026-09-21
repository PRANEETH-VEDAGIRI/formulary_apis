"""
Formulary Extraction APIs — FastAPI entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_pool, close_pool
from app.routes import router, auth_router, register_table_routes
from config import API_TITLE, API_VERSION

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("formulary_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", API_TITLE, API_VERSION)
    init_pool()
    register_table_routes(app)
    yield
    close_pool()
    logger.info("Shutdown complete")


app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "version": API_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
