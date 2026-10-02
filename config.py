from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_CONFIG = BASE_DIR / "config.yaml"


def carregar_config(caminho: Path = ARQUIVO_CONFIG) -> dict:
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        raise SystemExit(f"config.yaml não encontrado em {caminho}")
    except yaml.YAMLError as e:
        raise SystemExit(f"config.yaml inválido: {e}")

    try:
        cfg["sistema"]["armazenamento"]["metadata"]
    except (KeyError, TypeError):
        raise SystemExit("config.yaml sem a chave sistema.armazenamento.metadata")

    return cfg


config = carregar_config()