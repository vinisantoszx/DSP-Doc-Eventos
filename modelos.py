from pydantic import BaseModel

class DocumentoEvento(BaseModel):
    #req 4
    id: int
    nome_original: str
    nome_armazenado: str
    extensao: str
    tipo_mime: str
    tamanho: int
    categoria: str
    descricao: str
    data_upload: str
    sha256: str

    #req 11
    evento: str
    participante_ou_responsavel: str
    categoria_evento: str
    data_evento: str
    local: str
