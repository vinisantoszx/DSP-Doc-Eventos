#utilspy

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("CofreEventos")

def garantir_arquivo(arquivo: Path) -> None:
    """
    Garante que a pasta e o ficheiro JSON existem. Se não existirem, cria-os.
    """
    arquivo.parent.mkdir(parents=True, exist_ok=True)

    if not arquivo.exists():
        with open(arquivo, "w", encoding="utf-8") as file:
            json.dump([], file, ensure_ascii=False, indent=4)
        logger.info(f"Arquivo JSON criado automaticamente: {arquivo.name}")

def ler_json(arquivo: Path) -> list[dict[str, Any]]:
    """
    Lê e devolve os dados do ficheiro JSON.
    """
    garantir_arquivo(arquivo)
    
    try:
        with open(arquivo, "r", encoding="utf-8") as file:
            return json.load(file)
    
    except json.JSONDecodeError as erro:
        logger.error(f"JSON inválido em {arquivo.name}: {erro}")
        raise ValueError(f"O arquivo {arquivo.name} contém JSON inválido") from erro

def escrever_json(arquivo: Path, dados: list[dict[str, Any]]) -> None:
    """
    Substitui o conteúdo do ficheiro JSON pelos novos dados.
    """
    garantir_arquivo(arquivo)
    
    with open(arquivo, 'w', encoding="utf-8") as file:
        json.dump(dados, file, ensure_ascii=False, indent=4)
    
    logger.debug(f"Arquivo {arquivo.name} atualizado com {len(dados)} registos")

def buscar_por_id(arquivo: Path, registro_id: int) -> dict[str, Any] | None:
    """
    Busca um registro pelo ID dentro do ficheiro JSON.
    """
    dados = ler_json(arquivo)
    
    for item in dados:
        if item["id"] == registro_id:
            return item
    return None