import logging
from fastapi import APIRouter, HTTPException, status
from typing import Optional
 
from config import config, BASE_DIR
from modelos import DocumentoEvento
from utils import ler_json, buscar_por_id
 
logger = logging.getLogger("CofreEventos")
 
pasta_metadata = config["sistema"]["armazenamento"]["metadata"]
ARQUIVO_JSON = BASE_DIR / pasta_metadata / "documentos.json"
 
router = APIRouter(
    prefix="/documentos",
    tags=["documentos"],
)

def comparar_texto(valor_doc, filtro: str) -> bool:
    """
    Compara dois textos ignorando maiúsculas, minúsculas e espaços nas pontas.
    """
    return str(valor_doc or "").strip().casefold() == filtro.strip().casefold()

def normalizar_extensao(valor) -> str:
    """
    Remove o ponto inicial e padroniza a extensão (".PDF" e "pdf" viram "pdf").
    """
    return str(valor or "").lstrip(".").casefold()

@router.get("", response_model=list[DocumentoEvento])
def listar_documentos(
    categoria: Optional[str] = None,
    extensao: Optional[str] = None,
    evento: Optional[int] = None,
    participante: Optional[int] = None,
    local: Optional[str] = None,
    categoria_evento: Optional[str] = None,
    data_evento: Optional[str] = None,
):
    """
    Retorna a lista de documentos, permitindo filtragem combinada.
    """
    documentos = ler_json(ARQUIVO_JSON)
    resultados = []
