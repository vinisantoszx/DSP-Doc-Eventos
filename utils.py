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

def ler_json(caminho: Path = ARQUIVO_JSON) -> list[dict[str, Any]]:
    # Lê os dados do arquivo e converte para uma lista do Python
    verificar_banco_json(caminho)
    
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except json.JSONDecodeError as erro:
        logger.error(f"Erro ao ler o arquivo {caminho.name}: {erro}")
        raise ValueError(f"O banco de dados {caminho.name} está corrompido.") from erro

def salvar_json(caminho: Path, lista_documentos: list[dict[str, Any]]):
    # Sobrescreve o arquivo JSON atual com a lista atualizada
    verificar_banco_json(caminho)
    
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(lista_documentos, arquivo, ensure_ascii=False, indent=4)
        
    logger.debug(f"Salvo com sucesso. Total de registros: {len(lista_documentos)}")

def buscar_por_id(caminho: Path, registro_id: int) -> dict[str, Any] | None:
    # Função para a rota de Seba funcionar
    dados = ler_json(caminho)
    for item in dados:
        if item.get("id") == registro_id:
            return item
    return None