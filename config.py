from pathlib import Path
import hashlib
import shutil
import yaml

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_CONFIG = BASE_DIR / "config.yaml"

NIVEIS_LOG = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def obter_chave(cfg: dict, caminho: str):
    atual = cfg
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            raise SystemExit(f"config.yaml sem a chave {caminho}")
        atual = atual[parte]
    return atual


def validar_config(cfg: dict) -> None:
    if not isinstance(cfg, dict):
        raise SystemExit("config.yaml inválido: o conteúdo deve ser um conjunto de chaves")

    for chave in (
        "sistema.armazenamento.documentos",
        "sistema.armazenamento.metadata",
        "sistema.armazenamento.backups",
        "handlers.file.filename",
    ):
        valor = obter_chave(cfg, chave)
        if not isinstance(valor, str) or not valor.strip():
            raise SystemExit(f"config.yaml: {chave} deve ser um texto não vazio")

    limite = obter_chave(cfg, "sistema.upload.tamanho_maximo_mb")
    if isinstance(limite, bool) or not isinstance(limite, (int, float)) or limite <= 0:
        raise SystemExit("config.yaml: sistema.upload.tamanho_maximo_mb deve ser um número maior que zero")

    algoritmo = obter_chave(cfg, "sistema.seguranca.algoritmo_hash")
    try:
        hashlib.new(str(algoritmo)).hexdigest()
    except (ValueError, TypeError):
        raise SystemExit(f"config.yaml: algoritmo_hash '{algoritmo}' não é suportado")

    formato = obter_chave(cfg, "sistema.backup.formato")
    formatos = [nome for nome, _ in shutil.get_archive_formats()]
    if formato not in formatos:
        raise SystemExit(f"config.yaml: backup.formato '{formato}' inválido. Use um destes: {', '.join(formatos)}")

    nivel = str(obter_chave(cfg, "loggers.CofreEventos.level")).upper()
    if nivel not in NIVEIS_LOG:
        raise SystemExit(f"config.yaml: nível de log '{nivel}' inválido. Use um destes: {', '.join(NIVEIS_LOG)}")
    cfg["loggers"]["CofreEventos"]["level"] = nivel


def carregar_config(caminho: Path = ARQUIVO_CONFIG) -> dict:
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        raise SystemExit(f"config.yaml não encontrado em {caminho}")
    except yaml.YAMLError as e:
        raise SystemExit(f"config.yaml inválido: {e}")

    validar_config(cfg)

    return cfg


config = carregar_config()