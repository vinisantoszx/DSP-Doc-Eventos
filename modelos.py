from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

def obter_data_atual() -> str:
    # Retorna a data e hora no padrão brasileiro
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

class DocumentoEvento(BaseModel):
    id: Optional[int] = None
    nome_original: str = Field(..., description="Nome original do arquivo")
    nome_armazenado: str = Field(..., description="Nome salvo no disco")
    extensao: str = Field(..., description="Extensão do arquivo (ex: .pdf)")
    tipo_mime: str = Field(..., description="Mime type do arquivo")
    tamanho: int = Field(..., description="Tamanho do arquivo em bytes")
    categoria: str = Field(..., description="Categoria do documento (ex: certificado, recibo)")
    descricao: str = Field(..., description="Descrição do documento")
    
    # Metadados do Evento (Alinhados com os filtros do Navegador)
    evento: str = Field(..., description="Nome do evento")
    participante_ou_responsavel: str = Field(..., description="Membro da equipe ou participante")
    local: str = Field(..., description="Local da realização do evento")
    categoria_evento: str = Field(..., description="Categoria do evento (ex: oficina, palestra)")
    data_evento: str = Field(..., description="Data em que o evento ocorreu")
    
    # Campos automáticos e de auditoria
    data_upload: str = Field(default_factory=obter_data_atual)
    sha256: Optional[str] = Field(default=None, description="Assinatura de integridade")

class DocumentoAtualizacao(BaseModel):
    descricao: Optional[str] = Field(default=None, description="Nova descrição do documento")
    evento: Optional[str] = Field(default=None, description="Novo nome do evento")
    participante_ou_responsavel: Optional[str] = Field(default=None, description="Novo responsável")
    local: Optional[str] = Field(default=None, description="Novo local")
    categoria: Optional[str] = Field(default=None, description="Nova categoria do documento")
    categoria_evento: Optional[str] = Field(default=None, description="Nova categoria do evento")
    data_evento: Optional[str] = Field(default=None, description="Nova data do evento")
