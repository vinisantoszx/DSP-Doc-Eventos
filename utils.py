#utilspy

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger("CofreEventos")

trava = threading.RLock()

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
    with trava:
        garantir_arquivo(arquivo)

        try:
            with open(arquivo, "r", encoding="utf-8") as file:
                dados = json.load(file)

        except json.JSONDecodeError as erro:
            logger.error(f"JSON inválido em {arquivo.name}: {erro}")
            raise ValueError(f"O arquivo {arquivo.name} contém JSON inválido") from erro

    if not isinstance(dados, list):
        logger.error(f"JSON inválido em {arquivo.name}: o conteúdo deve ser uma lista")
        raise ValueError(f"O arquivo {arquivo.name} deve conter uma lista de documentos")

    return dados

def salvar_json(arquivo: Path, dados: list[dict[str, Any]]) -> None:
    """
    Substitui o conteúdo do ficheiro JSON pelos novos dados.
    """
    with trava:
        garantir_arquivo(arquivo)

        temporario = arquivo.with_suffix(".tmp")
        with open(temporario, 'w', encoding="utf-8") as file:
            json.dump(dados, file, ensure_ascii=False, indent=4)
        os.replace(temporario, arquivo)

    logger.debug(f"Arquivo {arquivo.name} atualizado com {len(dados)} registos")

escrever_json = salvar_json

def buscar_por_id(arquivo: Path, registro_id: int) -> dict[str, Any] | None:
    """
    Busca um registro pelo ID dentro do ficheiro JSON.
    """
    dados = ler_json(arquivo)

    for item in dados:
        if item.get("id") == registro_id:
            return item
    return None