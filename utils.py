import json
from pathlib import Path
from typing import Any
import logging

# Usa o logger que já configuramos no main.py
logger = logging.getLogger("CofreEventos")

# Caminho absoluto para evitar erros entre Windows e Linux
BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_JSON = BASE_DIR / "storage" / "metadata" / "documentos.json"

def verificar_banco_json(caminho: Path):
    # Cria as pastas storage e metadata caso não existam
    caminho.parent.mkdir(parents=True, exist_ok=True)
    
    # Se for a primeira vez rodando, cria o arquivo com uma lista vazia
    if not caminho.exists():
        with open(caminho, "w", encoding="utf-8") as arquivo:
            json.dump([], arquivo, ensure_ascii=False, indent=4)
        logger.info(f"Arquivo criado: {caminho.name}")

def ler_json() -> list[dict[str, Any]]:
    # Lê os dados do arquivo e converte para uma lista do Python
    verificar_banco_json(ARQUIVO_JSON)
    
    try:
        with open(ARQUIVO_JSON, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except json.JSONDecodeError as erro:
        logger.error(f"Erro ao ler o arquivo {ARQUIVO_JSON.name}: {erro}")
        raise ValueError(f"O banco de dados {ARQUIVO_JSON.name} está corrompido.") from erro

def salvar_json(lista_documentos: list[dict[str, Any]]):
    # Sobrescreve o arquivo JSON atual com a lista atualizada
    verificar_banco_json(ARQUIVO_JSON)
    
    with open(ARQUIVO_JSON, "w", encoding="utf-8") as arquivo:
        json.dump(lista_documentos, arquivo, ensure_ascii=False, indent=4)
        
    logger.debug(f"Salvo com sucesso. Total de registros: {len(lista_documentos)}")