from routes.documentos import router as documentos_router
import logging
import logging.config
import yaml
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# 1. Configurando o caminho e carregando o log
BASE_DIR = Path(__file__).resolve().parent
LOGGING_FILE = BASE_DIR / "config.yaml"

with open(LOGGING_FILE, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

logging.config.dictConfig(config)
logger = logging.getLogger("CofreEventos")

# 2. Inicializando a API do Cofre
app = FastAPI(
    title="Cofre Digital - Eventos",
    version="1.0.0",
    description="API para armazenamento e gestão de documentos de eventos."
)

app.include_router(documentos_router)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Captura exceções HTTP e registra-as no ficheiro de log antes de responder.
    """
    mensagem_log = f"[{exc.status_code}] {exc.detail} - Rota: {request.url.path}"

    if exc.status_code >= 500:
        logger.error(mensagem_log)
    else:
        logger.warning(mensagem_log)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Captura qualquer erro não tratado no código, registra como ERROR e devolve um 500 limpo.
    """
    logger.error(f"[500] Erro interno inesperado ao acessar {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno inesperado no servidor."},
    )

@app.on_event("startup")
def startup():
    logger.info("Sistema inicializado com sucesso.")

@app.get("/")
def home():
    return {"mensagem": "Cofre Digital de Eventos operando."}