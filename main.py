import logging
import logging.config
import yaml
from pathlib import Path
from fastapi import FastAPI

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

@app.on_event("startup")
def startup():
    logger.info("Sistema inicializado com sucesso.")

@app.get("/")
def home():
    return {"mensagem": "Cofre Digital de Eventos operando."}