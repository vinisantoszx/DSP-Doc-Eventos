from pathlib import Path
import yaml
import logging
from fastapi import APIRouter, HTTPException, status

from modelos import DocumentoEvento
from utils import ler_json, buscar_por_id

logger = logging.getLogger("CofreEventos")

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_CONFIG = BASE_DIR / "config.yaml"

with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

pasta_metadata = config["sistema"]["armazenamento"]["metadata"]
ARQUIVO_JSON = BASE_DIR / pasta_metadata / "documentos.json"

router = APIRouter(
    prefix="/documentos",
    tags=["documentos"],
)

@router.get("", response_model=list[DocumentoEvento])
def listar_documentos():
    """
    Retorna a lista com todos os documentos de eventos cadastrados.
    """
    documentos = ler_json(ARQUIVO_JSON)
    logger.info(f"Listagem de documentos {len(documentos)} registro(s) retornado(s).")
    return documentos

@router.get("/{id_documento}", response_model=DocumentoEvento)
def obter_documento(id_documento: int):
    """
    Busca um documento específico através do seu ID.
    """
    documento = buscar_por_id(ARQUIVO_JSON, id_documento)

    if not documento:
        logger.warning(f"Documento não encontrado: ID {id_documento}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado",
        )

    logger.info(f"Documento encontrado: ID {id_documento}")
    return documento