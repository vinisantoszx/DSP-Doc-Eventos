import csv
import hashlib
import io
import logging
import re
import shutil
import tempfile
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from config import config, BASE_DIR
from modelos import DocumentoEvento
from utils import ler_json, buscar_por_id

logger = logging.getLogger("CofreEventos")

# Router sem prefixo: as rotas seguem os caminhos pedidos no enunciado
router = APIRouter(tags=["auditoria"])

ARMAZENAMENTO = config["sistema"]["armazenamento"]
ARQUIVO_JSON = BASE_DIR / ARMAZENAMENTO["metadata"] / "documentos.json"
PASTA_ARQUIVOS = BASE_DIR / ARMAZENAMENTO["documentos"]
PASTA_BACKUPS = BASE_DIR / ARMAZENAMENTO["backups"]
ALGORITMO_HASH = config["sistema"]["seguranca"]["algoritmo_hash"]
FORMATO_BACKUP = config["sistema"]["backup"]["formato"]

# Evita que dois backups simultâneos escolham o mesmo nome
backup_lock = threading.Lock()


def calcular_hash(caminho: Path) -> str:
    """
    Calcula o hash do arquivo lendo em blocos, sem carregar tudo na memória.
    """
    hash_obj = hashlib.new(ALGORITMO_HASH)
    with open(caminho, "rb") as arquivo_binario:
        for chunk in iter(lambda: arquivo_binario.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


# ==============================================================================
# ROTAS DO AUDITOR - Segurança, Backups e Exportações
# ==============================================================================


# F9: Integridade de um Documento
@router.get("/documentos/{id_documento}/integridade", summary="Verificar integridade do documento")
def verificar_integridade(id_documento: int):
    """
    Recalcula o hash do arquivo físico e compara com o hash registrado no JSON.
    """
    documento = buscar_por_id(ARQUIVO_JSON, id_documento)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    hash_original = documento.get("sha256")
    caminho_arquivo = PASTA_ARQUIVOS / documento.get("nome_armazenado", "")

    hash_atual = calcular_hash(caminho_arquivo) if caminho_arquivo.is_file() else None
    integro = hash_atual is not None and hash_atual == hash_original

    if integro:
        logger.info(f"INTEGRIDADE_OK id={id_documento}")
    elif hash_atual is None:
        logger.warning(f"INTEGRIDADE_FALHOU: Doc {id_documento} - arquivo físico ausente.")
    else:
        logger.warning(f"INTEGRIDADE_FALHOU: Doc {id_documento} - hash incorreto.")

    return {
        "id": id_documento,
        "nome": documento.get("nome_original"),
        "hash_original": hash_original,
        "hash_atual": hash_atual,
        "integro": integro,
    }


# F10: Relatório de Integridade Geral
@router.get("/integridade", summary="Relatório Geral de Integridade")
def relatorio_integridade_geral():
    """
    Verifica todos os documentos: conta os íntegros e os alterados
    e lista separadamente os arquivos não localizados.
    """
    documentos = ler_json(ARQUIVO_JSON)

    total_integros = 0
    alterados = []
    nao_localizados = []

    for doc in documentos:
        id_doc = doc.get("id")
        nome = doc.get("nome_original")
        caminho_arquivo = PASTA_ARQUIVOS / doc.get("nome_armazenado", "")

        if not caminho_arquivo.is_file():
            nao_localizados.append({"id": id_doc, "nome": nome})
            logger.warning(f"INTEGRIDADE_FALHOU: Doc {id_doc} ({nome}) - Ausente.")
        elif calcular_hash(caminho_arquivo) == doc.get("sha256"):
            total_integros += 1
        else:
            alterados.append({"id": id_doc, "nome": nome})
            logger.warning(f"INTEGRIDADE_FALHOU: Doc {id_doc} ({nome}) - Hash incorreto.")

    logger.info(
        f"INTEGRIDADE_GERAL verificados={len(documentos)} integros={total_integros} "
        f"alterados={len(alterados)} nao_localizados={len(nao_localizados)}"
    )
    return {
        "total_verificados": len(documentos),
        "total_integros": total_integros,
        "total_alterados": len(alterados),
        "alterados": alterados,
        "total_nao_localizados": len(nao_localizados),
        "nao_localizados": nao_localizados,
    }


# F14: Criar Backup
@router.post("/backup", summary="Gerar backup do sistema", status_code=201)
def gerar_backup():
    """
    Empacota as pastas de documentos e metadados definidas no config.yaml,
    usando o formato do YAML. Nunca sobrescreve um backup existente.
    """
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)

    with backup_lock:
        base = f"backup_cofre_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        contador = 1
        nome_base = base
        while any(PASTA_BACKUPS.glob(f"{nome_base}.*")):
            contador += 1
            nome_base = f"{base}_{contador}"

        with tempfile.TemporaryDirectory() as tmp:
            staging = Path(tmp) / "staging"
            staging.mkdir()
            for chave in ("documentos", "metadata"):
                origem = BASE_DIR / ARMAZENAMENTO[chave]
                if origem.exists():
                    shutil.copytree(origem, staging / origem.name)

            temporario = shutil.make_archive(str(Path(tmp) / nome_base), FORMATO_BACKUP, str(staging))
            destino = PASTA_BACKUPS / Path(temporario).name
            shutil.move(temporario, destino)

    logger.info(f"BACKUP_CRIADO: {destino.name}")
    return {"mensagem": "Backup gerado com sucesso.", "arquivo": destino.name, "tamanho": destino.stat().st_size}


# F15: Listar Backups
@router.get("/backups", summary="Listar backups disponíveis")
def listar_backups():
    """
    Lista os backups da pasta definida no config.yaml.
    """
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)

    backups = [
        {"arquivo": item.name, "tamanho": item.stat().st_size}
        for item in sorted(PASTA_BACKUPS.iterdir())
        if item.is_file() and item.name != ".gitkeep"
    ]
    logger.info(f"BACKUPS_LISTADOS total={len(backups)}")
    return backups


# F13: Exportação CSV
@router.get("/exportar/csv", summary="Exportar catálogo para CSV")
def exportar_csv():
    """
    Gera um arquivo .csv com o catálogo atual (somente o cabeçalho se estiver vazio).
    """
    documentos = ler_json(ARQUIVO_JSON)

    # Colunas fixas pelo modelo, para que registros com campos diferentes não quebrem a exportação
    cabecalhos = list(DocumentoEvento.model_fields.keys())

    saida = io.StringIO()
    saida.write("\ufeff")  # BOM para o Excel reconhecer os acentos
    escritor = csv.DictWriter(saida, fieldnames=cabecalhos, delimiter=",", extrasaction="ignore")
    escritor.writeheader()
    for doc in documentos:
        escritor.writerow(doc)

    logger.info(f"EXPORTACAO_CSV registros={len(documentos)}")
    resposta = StreamingResponse(iter([saida.getvalue()]), media_type="text/csv; charset=utf-8")
    resposta.headers["Content-Disposition"] = "attachment; filename=catalogo_documentos.csv"
    return resposta


# F16: Exportação XML por Evento (Tema 11)
@router.get("/documentos/auditoria/exportar/xml/{nome_evento}", summary="Exportar documentos do evento em XML")
def exportar_xml_evento(nome_evento: str):
    """
    Endpoint principal do domínio: Gera um arquivo XML de todos os documentos de um evento específico.
    """
    documentos = ler_json(ARQUIVO_JSON)

    # Filtra apenas documentos que pertencem ao evento procurado (ignorando cases)
    docs_evento = [doc for doc in documentos if str(doc.get("evento", "")).strip().casefold() == nome_evento.strip().casefold()]

    if not docs_evento:
        raise HTTPException(status_code=404, detail=f"Nenhum documento encontrado para o evento '{nome_evento}'.")

    root = ET.Element("Evento", nome=nome_evento)
    docs_element = ET.SubElement(root, "Documentos", total=str(len(docs_evento)))

    for doc in docs_evento:
        doc_xml = ET.SubElement(docs_element, "Documento", id=str(doc.get("id")))
        for chave, valor in doc.items():
            if chave != "id":
                campo = ET.SubElement(doc_xml, chave.capitalize().replace(" ", "_"))
                campo.text = str(valor)

    xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    resposta = Response(content=xml_str, media_type="application/xml")
    # Nome seguro para o cabeçalho HTTP (sem barras e com suporte a UTF-8)
    nome_seguro = re.sub(r'[\\/:*?"<>|\r\n\s]+', "_", nome_evento.strip()) or "evento"
    resposta.headers["Content-Disposition"] = (
        f"attachment; filename=\"evento.xml\"; filename*=UTF-8''evento_{quote(nome_seguro)}.xml"
    )
    logger.info(f"EXPORTACAO_XML evento={nome_evento} documentos={len(docs_evento)}")
    return resposta
