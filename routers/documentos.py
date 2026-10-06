import logging
import hashlib
import shutil
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from typing import Optional

# Importações do Sebastian integradas com as minhas
from config import config, BASE_DIR
from modelos import DocumentoEvento
from utils import ler_json, buscar_por_id, salvar_json

logger = logging.getLogger("CofreEventos")

# Configurações de pastas (misturando a base do Sebastian com a minha necessidade de arquivos físicos)
pasta_metadata = config["sistema"]["armazenamento"]["metadata"]
ARQUIVO_JSON = BASE_DIR / pasta_metadata / "documentos.json"

PASTA_ARQUIVOS = BASE_DIR / "storage" / "arquivos"
PASTA_ARQUIVOS.mkdir(parents=True, exist_ok=True)

router = APIRouter(
    prefix="/documentos",
    tags=["documentos"],
)

# ==============================================================================
# ROTA DO ARQUIVISTA - Upload de Documentos
# ==============================================================================
@router.post("/upload/", status_code=status.HTTP_201_CREATED)
async def upload_documento(
    arquivo: UploadFile = File(...),
    evento: str = Form(...),
    participante: str = Form(...),
    local: str = Form(...),
    categoria: str = Form(...),
    categoria_evento: str = Form(...),
    data_evento: str = Form(...)
):
    """
    Recebe o arquivo físico e registra os metadados no sistema.
    """
    caminho_arquivo = PASTA_ARQUIVOS / arquivo.filename
    try:
        with open(caminho_arquivo, "wb") as buffer:
            shutil.copyfileobj(arquivo.file, buffer)
    except Exception as erro:
        logger.error(f"Erro ao salvar arquivo físico {arquivo.filename}: {erro}")
        raise HTTPException(status_code=500, detail="Falha ao salvar o arquivo no servidor.")

    # --- INÍCIO DA ADIÇÃO DO HASH ---
    # Calcula o Hash SHA-256 lendo o arquivo em pequenos blocos
    sha256_hash = hashlib.sha256()
    with open(caminho_arquivo, "rb") as arquivo_binario:
        for chunk in iter(lambda: arquivo_binario.read(4096), b""):
            sha256_hash.update(chunk)
    hash_calculado = sha256_hash.hexdigest()
    # --- FIM DA ADIÇÃO ---

    tamanho_bytes = caminho_arquivo.stat().st_size

    # Monta o modelo compatível com os filtros do Sebastian
    novo_documento = DocumentoEvento(
        nome_arquivo=arquivo.filename,
        extensao=caminho_arquivo.suffix,
        tamanho=tamanho_bytes,
        hash_sha256=hash_calculado,
        evento=evento,
        participante_ou_responsavel=participante,
        local=local,
        categoria=categoria,
        categoria_evento=categoria_evento,
        data_evento=data_evento
    )

    try:
        dados = ler_json(ARQUIVO_JSON)
        novo_id = 1 if len(dados) == 0 else dados[-1]["id"] + 1
        novo_documento.id = novo_id
        
        dados.append(novo_documento.model_dump())
        salvar_json(ARQUIVO_JSON, dados)
        
        logger.info(f"UPLOAD concluído: {arquivo.filename} (Evento: {evento})")
        return {"mensagem": "Arquivo arquivado com sucesso", "documento": novo_documento}
        
    except Exception as erro:
        logger.error(f"Erro ao registrar metadados: {erro}")
        if caminho_arquivo.exists():
            caminho_arquivo.unlink()
        raise HTTPException(status_code=500, detail="Erro ao registrar no banco de dados.")

# ==============================================================================
# ROTAS DO NAVEGADOR (PARTE DO SEBASTIAN) - Filtros e Buscas
# ==============================================================================

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
    evento: Optional[str] = None,
    participante: Optional[str] = None,
    local: Optional[str] = None,
    categoria_evento: Optional[str] = None,
    data_evento: Optional[str] = None
):
    """
    Retorna a lista de documentos, permitindo filtragem combinada.
    """
    documentos = ler_json(ARQUIVO_JSON)
    resultados = []

    for doc in documentos: 
        match = True

        if categoria and not comparar_texto(doc.get("categoria"), categoria):
            match = False
        if extensao and normalizar_extensao(doc.get("extensao")) != normalizar_extensao(extensao):
            match = False
        if evento and not comparar_texto(doc.get("evento"), evento):
            match = False
        if participante and not comparar_texto(doc.get("participante_ou_responsavel"), participante):
            match = False
        if local and not comparar_texto(doc.get("local"), local):
            match = False
        if categoria_evento and not comparar_texto(doc.get("categoria_evento"), categoria_evento):
            match = False
        if data_evento and not str(doc.get("data_evento", "")).startswith(data_evento):
            match = False

        if match:
            resultados.append(doc)

    filtros = {
        "categoria": categoria,
        "extensao": extensao,
        "evento": evento,
        "participante": participante,
        "local": local,
        "categoria_evento": categoria_evento,
        "data_evento": data_evento,
    }
    filtros_usados = {chave: valor for chave, valor in filtros.items() if valor}

    logger.info(f"CONSULTA_LISTAGEM filtros={filtros_usados} retornados={len(resultados)}")
    return resultados

@router.get("/estatisticas")
def obter_estatisticas():
    """
    Calcula e retorna estatísticas gerais do Cofre.
    """
    documentos = ler_json(ARQUIVO_JSON)
    total_documentos = len(documentos)
    total_tamanho = sum(doc.get("tamanho", 0) for doc in documentos)

    por_extensao = {}
    por_categoria = {}
    por_evento = {}
    por_local = {}
    por_categoria_evento = {}

    for doc in documentos:
        ext = normalizar_extensao(doc.get("extensao")) or "desconhecida"
        cat = doc.get("categoria", "desconhecida")
        evento = doc.get("evento", "desconhecido")
        local = doc.get("local", "desconhecido")
        cat_evento = doc.get("categoria_evento", "desconhecida")

        por_extensao[ext] = por_extensao.get(ext, 0) + 1
        por_categoria[cat] = por_categoria.get(cat, 0) + 1
        por_evento[evento] = por_evento.get(evento, 0) + 1
        por_local[local] = por_local.get(local, 0) + 1
        por_categoria_evento[cat_evento] = por_categoria_evento.get(cat_evento, 0) + 1

    logger.info(f"ESTATISTICAS total_documentos={total_documentos}")

    return {
        "total_documentos": total_documentos,
        "espaco_utilizado_bytes": total_tamanho,
        "por_extensao": por_extensao,
        "por_categoria": por_categoria,
        "por_evento": por_evento,
        "por_local": por_local,
        "por_categoria_evento": por_categoria_evento
    }

@router.get("/{id_documento}", response_model=DocumentoEvento)
def obter_documento(id_documento: int):
    """
    Busca um documento específico através do seu ID.
    """
    documento = buscar_por_id(ARQUIVO_JSON, id_documento)

    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento {id_documento} não encontrado",
        )

    logger.info(f"CONSULTA_ID id={id_documento}")
    return documento