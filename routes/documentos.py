from pathlib import Path
import yaml
import logging
from fastapi import APIRouter, HTTPException, status
from typing import Optional

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
def listar_documentos(
    categoria: Optional[str] = None,
    evento: Optional[str] = None,
    participante: Optional[str] = None
):
    """
    Retorna a lista de documentos, permitindo filtragem combinada.
    """
    documentos = ler_json(ARQUIVO_JSON)
    resultados = []

    for doc in documentos: 
        match = True

        if categoria and doc.get("categoria") != categoria:
            match = False
        if evento and doc.get("evento") != evento:
            match = False
        if participante and doc.get("participante_ou_responsavel") != participante:
            match = False

        if match:
            resultados.append(doc)

    logger.info(f"Listagem filtrada: {len(resultados)} registro(s) retornado(s).")
    return resultados

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