from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

def obter_data_atual() -> str:
    # Retorna a data e hora no padrão brasileiro
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

class DocumentoEvento(BaseModel):
    id: Optional[int] = None
    nome_arquivo: str = Field(..., description="Nome original do arquivo")
    extensao: str = Field(..., description="Extensão do arquivo (ex: .pdf, .docx)")
    tamanho_kb: float = Field(..., description="Tamanho do arquivo em Kilobytes")
    
    # Metadados do Evento exigidos para organização
    nome_evento: str = Field(..., description="Nome do evento relacionado ao documento")
    data_evento: str = Field(..., description="Data em que o evento ocorreu")
    local_evento: str = Field(..., description="Local da realização do evento")
    responsavel: str = Field(..., description="Membro da equipe responsável pelo registro")
    
    # Campos automáticos e de auditoria
    data_upload: str = Field(default_factory=obter_data_atual)
    hash_sha256: Optional[str] = Field(default=None, description="Assinatura de integridade do arquivo")