import logging
import hashlib
import mimetypes
import shutil
import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime
from fastapi.responses import FileResponse, StreamingResponse, Response
from modelos import DocumentoEvento, DocumentoAtualizacao
from pathlib import Path
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from typing import Optional

# Importações do Sebastian integradas com as minhas
from config import config, BASE_DIR
from modelos import DocumentoEvento
from utils import ler_json, buscar_por_id, salvar_json

logger = logging.getLogger("CofreEventos")

# Configurações de pastas (misturando a base do Sebastian com a minha de arquivos físicos)
pasta_metadata = config["sistema"]["armazenamento"]["metadata"]
ARQUIVO_JSON = BASE_DIR / pasta_metadata / "documentos.json"

PASTA_ARQUIVOS = BASE_DIR / config["sistema"]["armazenamento"]["documentos"]
PASTA_ARQUIVOS.mkdir(parents=True, exist_ok=True)

TAMANHO_MAXIMO_BYTES = config["sistema"]["upload"]["tamanho_maximo_mb"] * 1024 * 1024
ALGORITMO_HASH = config["sistema"]["seguranca"]["algoritmo_hash"]

router = APIRouter(
    prefix="/documentos",
    tags=["documentos"],
)

# ==============================================================================
# ROTA CHRYSTIAN - Upload de Documentos
# ==============================================================================
@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_documento(
    arquivo: UploadFile = File(...),
    evento: str = Form(...),
    participante: str = Form(...),
    local: str = Form(...),
    categoria: str = Form(...),
    categoria_evento: str = Form(...),
    data_evento: str = Form(...),
    descricao: str = Form("")
):
    """
    Recebe o arquivo físico e registra os metadados no sistema.
    """
    if not arquivo.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo foi enviado.")
        
    if arquivo.size and arquivo.size > TAMANHO_MAXIMO_BYTES:
        raise HTTPException(
            status_code=400, 
            detail=f"Arquivo excede o limite de {config['sistema']['upload']['tamanho_maximo_mb']}MB."
        )

    nome_original = Path(arquivo.filename).name
    dados = ler_json(ARQUIVO_JSON)
    novo_id = max((d.get("id", 0) for d in dados), default=0) + 1
    nome_armazenado = f"{novo_id}_{nome_original}"
    caminho_arquivo = PASTA_ARQUIVOS / nome_armazenado
    try:
        with open(caminho_arquivo, "wb") as buffer:
            shutil.copyfileobj(arquivo.file, buffer)
    except Exception as erro:
        logger.error(f"Erro ao salvar arquivo físico {arquivo.filename}: {erro}")
        raise HTTPException(status_code=500, detail="Falha ao salvar o arquivo no servidor.")

    # --- INÍCIO DA ADIÇÃO DO HASH ---
    # Calcula o Hash lendo o arquivo em pequenos blocos
    hash_obj = hashlib.new(ALGORITMO_HASH)
    with open(caminho_arquivo, "rb") as arquivo_binario:
        for chunk in iter(lambda: arquivo_binario.read(4096), b""):
            hash_obj.update(chunk)
    hash_calculado = hash_obj.hexdigest()
    # --- FIM DA ADIÇÃO ---

    tamanho_bytes = caminho_arquivo.stat().st_size
    tipo_mime = mimetypes.guess_type(nome_original)[0] or "application/octet-stream"

    # Monta o modelo compatível com os filtros do Sebastian
    novo_documento = DocumentoEvento(
        id=novo_id,
        nome_original=nome_original,
        nome_armazenado=nome_armazenado,
        extensao=caminho_arquivo.suffix,
        tipo_mime=tipo_mime,
        tamanho=tamanho_bytes,
        categoria=categoria,
        descricao=descricao,
        sha256=hash_calculado,
        evento=evento,
        participante_ou_responsavel=participante,
        local=local,
        categoria_evento=categoria_evento,
        data_evento=data_evento,
    )

    try:
        dados.append(novo_documento.model_dump())
        salvar_json(ARQUIVO_JSON, dados)
        
        logger.info(f"UPLOAD concluído: {arquivo.filename} (Evento: {evento})")
        return {"mensagem": "Arquivo arquivado com sucesso", "documento": novo_documento}
        
    except Exception as erro:
        logger.error(f"Erro ao registrar metadados: {erro}")
        if caminho_arquivo.exists():
            caminho_arquivo.unlink()
        raise HTTPException(status_code=500, detail="Erro ao registrar no banco de dados.")

@router.get("/{id_documento}/download", summary="Download do Arquivo")
def baixar_documento(id_documento: int):
    """
    Recupera o arquivo original armazenado pelo sistema.
    Trabalha com arquivos binários para evitar alterações no conteúdo.
    """
    # 1. Pede ao utils.py para achar os dados do arquivo pelo ID
    documento = buscar_por_id(ARQUIVO_JSON, id_documento)
    
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento {id_documento} não encontrado no banco de dados."
        )

    # 2. Monta o caminho de onde o arquivo físico deveria estar
    caminho_arquivo = PASTA_ARQUIVOS / documento["nome_armazenado"]
    
    # 3. Verifica se o arquivo físico realmente existe na pasta
    if not caminho_arquivo.exists():
        logger.error(f"Arquivo físico perdido: {caminho_arquivo}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="O arquivo físico não foi localizado no servidor."
        )
    
    logger.info(f"DOWNLOAD concluído: {documento['nome_original']} (ID: {id_documento})")
    
    # 4. Devolve o arquivo binário intacto para o usuário
    return FileResponse(
        path=caminho_arquivo, 
        filename=documento["nome_original"],
        media_type=documento.get("tipo_mime", "application/octet-stream")
    )

@router.put("/{id_documento}", summary="Atualização de metadados")
def atualizar_documento(id_documento: int, dados_atualizacao: DocumentoAtualizacao):
    """
    Atualiza os metadados de um documento existente.
    Não altera o ficheiro físico armazenado.
    """
    dados = ler_json(ARQUIVO_JSON)
    documento_encontrado = False
    
    # Procura o documento pelo ID e atualiza apenas os campos enviados
    for doc in dados:
        if doc.get("id") == id_documento:
            documento_encontrado = True
            
            # Converte o molde recebido para um dicionário, ignorando valores vazios (None)
            campos_para_atualizar = dados_atualizacao.model_dump(exclude_none=True)
            
            # Atualiza os dados no documento original
            for chave, valor in campos_para_atualizar.items():
                doc[chave] = valor
                
            break
            
    if not documento_encontrado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento {id_documento} não encontrado."
        )
        
    # Guarda as alterações de volta no ficheiro JSON
    salvar_json(ARQUIVO_JSON, dados)
    logger.info(f"ATUALIZAÇÃO concluída: Metadados do ID {id_documento} alterados.")
    
    return {"mensagem": "Metadados atualizados com sucesso", "id_documento": id_documento}

@router.delete("/{id_documento}", summary="Exclusão de Documento")
def excluir_documento(id_documento: int):
    """
    Remove definitivamente o registro do banco JSON e o arquivo físico correspondente.
    """
    dados = ler_json(ARQUIVO_JSON)
    documento_para_excluir = None
    
    for doc in dados:
        if doc.get("id") == id_documento:
            documento_para_excluir = doc
            break
            
    if not documento_para_excluir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento {id_documento} não encontrado."
        )
        
    # Remove o arquivo físico
    caminho_arquivo = PASTA_ARQUIVOS / documento_para_excluir["nome_armazenado"]
    if caminho_arquivo.exists():
        caminho_arquivo.unlink()
        logger.info(f"EXCLUSÃO: Arquivo físico {caminho_arquivo.name} apagado.")
        
    # Remove do JSON e salva
    dados.remove(documento_para_excluir)
    salvar_json(ARQUIVO_JSON, dados)
    
    logger.info(f"EXCLUSÃO concluída: Documento {id_documento} apagado do sistema.")
    return {"mensagem": "Documento e arquivo físico excluídos com sucesso", "id_documento": id_documento}

# ==============================================================================
# ROTA SEBASTIAN - Filtros e Buscas
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
        if data_evento and data_evento not in str(doc.get("data_evento", "")):
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



# ==============================================================================
# ROTAS VINÍCIUS - Segurança, Backups e Exportações
# ==============================================================================


# F10: Relatório de Integridade Geral
@router.get("/auditoria/integridade", summary="Relatório Geral de Integridade")
def relatorio_integridade_geral():
    """
    Verifica a integridade de todos os documentos registrados no banco comparando com os arquivos físicos.
    Retorna um relatório geral.
    """
    documentos = ler_json(ARQUIVO_JSON)
    if not documentos:
        return {"total_verificados": 0, "total_integros": 0, "total_corrompidos": 0, "corrompidos_detalhes": []}
        
    integros = []
    corrompidos = []
    
    for doc in documentos:
        id_doc = doc.get("id")
        nome = doc.get("nome_original")
        
        caminho_arquivo = PASTA_ARQUIVOS / doc.get("nome_armazenado", "")
        if not caminho_arquivo.exists():
            corrompidos.append({"id": id_doc, "nome": nome, "motivo": "Arquivo físico ausente"})
            logger.warning(f"INTEGRIDADE_FALHOU: Doc {id_doc} ({nome}) - Ausente.")
            continue
            
        hash_obj = hashlib.new(ALGORITMO_HASH)
        with open(caminho_arquivo, "rb") as arquivo_binario:
            for chunk in iter(lambda: arquivo_binario.read(4096), b""):
                hash_obj.update(chunk)
        hash_calculado = hash_obj.hexdigest()
        
        if hash_calculado == doc.get("sha256"):
            integros.append({"id": id_doc, "nome": nome})
        else:
            corrompidos.append({"id": id_doc, "nome": nome, "motivo": "Hash incompatível (Corrompido)"})
            logger.warning(f"INTEGRIDADE_FALHOU: Doc {id_doc} ({nome}) - Hash incorreto.")
            
    return {
        "total_verificados": len(documentos),
        "total_integros": len(integros),
        "total_corrompidos": len(corrompidos),
        "corrompidos_detalhes": corrompidos
    }

# F10: Relatório de Integridade Geral
@router.get("/auditoria/integridade", summary="Relatório Geral de Integridade")
def relatorio_integridade_geral():
    """
    Verifica a integridade de todos os documentos registrados no banco comparando com os arquivos físicos.
    Retorna um relatório geral.
    """
    documentos = ler_json(ARQUIVO_JSON)
    if not documentos:
        return {"total_verificados": 0, "total_integros": 0, "total_corrompidos": 0, "corrompidos_detalhes": []}
        
    integros = []
    corrompidos = []
    
    for doc in documentos:
        id_doc = doc.get("id")
        nome = doc.get("nome_original")
        
        caminho_arquivo = PASTA_ARQUIVOS / doc.get("nome_armazenado", "")
        if not caminho_arquivo.exists():
            corrompidos.append({"id": id_doc, "nome": nome, "motivo": "Arquivo físico ausente"})
            logger.warning(f"INTEGRIDADE_FALHOU: Doc {id_doc} ({nome}) - Ausente.")
            continue
            
        hash_obj = hashlib.new(ALGORITMO_HASH)
        with open(caminho_arquivo, "rb") as arquivo_binario:
            for chunk in iter(lambda: arquivo_binario.read(4096), b""):
                hash_obj.update(chunk)
        hash_calculado = hash_obj.hexdigest()
        
        if hash_calculado == doc.get("sha256"):
            integros.append({"id": id_doc, "nome": nome})
        else:
            corrompidos.append({"id": id_doc, "nome": nome, "motivo": "Hash incompatível (Corrompido)"})
            logger.warning(f"INTEGRIDADE_FALHOU: Doc {id_doc} ({nome}) - Hash incorreto.")
            
    return {
        "total_verificados": len(documentos),
        "total_integros": len(integros),
        "total_corrompidos": len(corrompidos),
        "corrompidos_detalhes": corrompidos
    }

# F14 e F15: Criar e Listar Backups
@router.post("/auditoria/backups", summary="Gerar backup do sistema")
def gerar_backup():
    """
    Empacota toda a pasta storage (arquivos, jsons e logs) num arquivo ZIP.
    """
    PASTA_BACKUPS = BASE_DIR / config["sistema"]["armazenamento"]["backups"]
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    
    data_atual = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_backup = f"backup_cofre_{data_atual}"
    caminho_backup = PASTA_BACKUPS / nome_backup
    
    pasta_storage = BASE_DIR / "storage"
    shutil.make_archive(str(caminho_backup), 'zip', str(pasta_storage))
    
    logger.info(f"BACKUP_CRIADO: {nome_backup}.zip")
    return {"mensagem": "Backup gerado com sucesso.", "arquivo": f"{nome_backup}.zip"}

@router.get("/auditoria/backups", summary="Listar backups disponíveis")
def listar_backups():
    """
    Lista todos os arquivos .zip disponíveis na pasta de backups.
    """
    PASTA_BACKUPS = BASE_DIR / config["sistema"]["armazenamento"]["backups"]
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    
    backups = []
    for arquivo in PASTA_BACKUPS.glob("*.zip"):
        backups.append({
            "nome": arquivo.name,
            "tamanho_bytes": arquivo.stat().st_size,
            "data_criacao": datetime.fromtimestamp(arquivo.stat().st_ctime).strftime("%d/%m/%Y %H:%M:%S")
        })
        
    return {"total": len(backups), "backups": backups}

# F13: Exportação CSV
@router.get("/auditoria/exportar/csv", summary="Exportar catálogo para CSV")
def exportar_csv():
    """
    Gera um arquivo .csv contendo todo o catálogo do JSON atual.
    """
    documentos = ler_json(ARQUIVO_JSON)
    if not documentos:
        raise HTTPException(status_code=404, detail="Nenhum documento para exportar.")
        
    cabecalhos = list(documentos[0].keys())
    
    saida = io.StringIO()
    escritor = csv.DictWriter(saida, fieldnames=cabecalhos, delimiter=";")
    escritor.writeheader()
    for doc in documentos:
        escritor.writerow(doc)
        
    saida.seek(0)
    
    resposta = StreamingResponse(iter([saida.getvalue()]), media_type="text/csv")
    resposta.headers["Content-Disposition"] = "attachment; filename=catalogo_documentos.csv"
    return resposta

# F16: Exportação XML por Evento (Tema 11)
@router.get("/auditoria/exportar/xml/{nome_evento}", summary="Exportar documentos do evento em XML")
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
    nome_arquivo = f"evento_{nome_evento.replace(' ', '_')}.xml"
    resposta.headers["Content-Disposition"] = f"attachment; filename={nome_arquivo}"
    return resposta

# F9: Integridade de um Documento
@router.get("/{id_documento}/integridade", summary="Verificar integridade do documento")
def verificar_integridade(id_documento: int):
    """
    Recalcula o SHA do arquivo físico e compara com o JSON.
    (Colocado no final para evitar conflito com /auditoria/integridade)
    """
    documento = buscar_por_id(ARQUIVO_JSON, id_documento)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    
    caminho_arquivo = PASTA_ARQUIVOS / documento["nome_armazenado"]
    if not caminho_arquivo.exists():
        return {"status": "corrompido", "motivo": "Arquivo físico ausente no diretório."}
        
    hash_obj = hashlib.new(ALGORITMO_HASH)
    with open(caminho_arquivo, "rb") as arquivo_binario:
        for chunk in iter(lambda: arquivo_binario.read(4096), b""):
            hash_obj.update(chunk)
    hash_calculado = hash_obj.hexdigest()
    
    hash_esperado = documento.get("sha256")
    
    if hash_calculado == hash_esperado:
        return {"status": "integro", "mensagem": "O arquivo está intacto e não foi alterado."}
    else:
        logger.warning(f"INTEGRIDADE_FALHOU: Doc {id_documento} corrompido.")
        return {"status": "corrompido", "motivo": "O hash físico não confere com o registrado no banco."}

@router.get("/{id_documento}", response_model=DocumentoEvento)
def obter_documento(id_documento: int):
    """
    Busca um documento específico através do seu ID.
    (Colocado no final para não conflitar com rotas de texto longo como /auditoria)
    """
    documento = buscar_por_id(ARQUIVO_JSON, id_documento)

    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documento {id_documento} não encontrado",
        )

    logger.info(f"CONSULTA_ID id={id_documento}")
    return documento