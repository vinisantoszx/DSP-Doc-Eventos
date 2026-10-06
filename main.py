from routers.documentos import router as documentos_router
import logging
import logging.config
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import config, BASE_DIR

# 1. Configurando o caminho e carregando o log
for handler in config.get("handlers", {}).values():
    if "filename" in handler:
        handler["filename"] = str((BASE_DIR / handler["filename"]).resolve())
        Path(handler["filename"]).parent.mkdir(parents=True, exist_ok=True)

logging.config.dictConfig(config)
logger = logging.getLogger("CofreEventos")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("INICIALIZACAO Sistema inicializado com sucesso.")
    yield
    logger.info("ENCERRAMENTO Sistema encerrado.")

# 2. Inicializando a API do Cofre
app = FastAPI(
    title="Cofre Digital - Eventos",
    version="1.0.0",
    description="API para armazenamento e gestão de documentos de eventos.",
    lifespan=lifespan
)

app.include_router(documentos_router)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Captura exceções HTTP e registra-as no ficheiro de log antes de responder.
    """
    mensagem_log = f"HTTP_{exc.status_code} rota={request.url.path} detalhe={exc.detail}"

    if exc.status_code >= 500 or exc.status_code == 404:
        logger.error(mensagem_log)
    else:
        logger.warning(mensagem_log)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Captura dados inválidos na requisição, registra como WARNING e devolve um 422.
    """
    logger.warning(f"VALIDACAO_FALHOU rota={request.url.path}")
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """
    Captura JSON inválido ou corrompido, registra como ERROR e devolve um 500 claro.
    """
    logger.error(f"JSON_INVALIDO rota={request.url.path} detalhe={str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Arquivo de metadados inválido ou corrompido."},
    )

@app.exception_handler(OSError)
async def os_error_handler(request: Request, exc: OSError):
    """
    Captura falhas de leitura ou escrita em disco, registra como ERROR e devolve um 500 claro.
    """
    logger.error(f"ERRO_LEITURA_ESCRITA rota={request.url.path} detalhe={str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro de leitura ou escrita nos arquivos do sistema."},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Captura qualquer erro não tratado no código, registra como ERROR e devolve um 500 limpo.
    """
    logger.error(f"ERRO_INTERNO rota={request.url.path} detalhe={str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno inesperado no servidor."},
    )

@app.get("/")
def home():
    return {"mensagem": "Cofre Digital de Eventos operando."}