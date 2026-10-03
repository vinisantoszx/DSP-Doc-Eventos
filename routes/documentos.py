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

@router.get("/estatisticas")
def obter_estatisticas():
    """
    Calcula e retorna estatísticas geraisdo Cofre.
    """
    documentos = ler_json(ARQUIVO_JSON)
    total_documentos = len(documentos)
    total_tamanho = sum(doc.get("tamanho", 0) for doc in documentos)

    por_extensao = {}
    por_categoria = {}
    por_evento = {}

    for doc in documentos:
        ext = doc.get("extensao", "desconhecida")
        cat = doc.get("categoria", "desconhecida")
        evento = doc.get("evento", "desconhecido")

        por_extensao[ext] = por_extensao.get(ext, 0) + 1
        por_categoria[cat] = por_categoria.get(cat, 0) + 1
        por_evento[evento] = por_evento.get(evento, 0) + 1

    logger.info("Estatísticas do sistema consultadas.")

    return {
        "total_documentos": total_documentos,
        "total_tamanho_bytes": total_tamanho,
        "por_extensao": por_extensao,
        "por_categoria": por_categoria,
        "por_evento": por_evento
    }

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