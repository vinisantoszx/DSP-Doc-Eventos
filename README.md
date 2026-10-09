# Cofre Digital - Documentação de Eventos

Projeto desenvolvido para a disciplina de Desenvolvimento de Software para Persistência. O **Cofre Digital** é uma API RESTFul construída com **FastAPI** para o gerenciamento, armazenamento e auditoria de documentos físicos atrelados a um domínio de **Organização de Eventos**.

## Funcionalidades Principais

O sistema foi estruturado simulando rigorosamente as responsabilidades de três papéis fundamentais (Fases do Trabalho):

### 1. O Arquivista (Armazenamento)
* **Upload de Documentos:** Suporta múltiplos formatos (binários e textuais).
* **Gestão de Metadados:** Cada arquivo é enriquecido com um conjunto completo de metadados exigidos: nome original, evento relacionado, data, categoria, tipo MIME, etc.
* **Segurança e Prevenção:** Implementação de escrita atômica segura e um `Lock` (`threading.Lock`) durante operações críticas no banco `JSON` local para evitar corrupções em caso de múltiplos uploads paralelos ou quedas inesperadas do servidor.
* **CRUD Completo:** Além do upload, o módulo permite o download de arquivos binários, atualização de metadados específicos e exclusão real e simultânea do metadado e do arquivo físico.

### 2. O Navegador (Buscas e Filtros)
* **Mecanismo de Busca Flexível:** Permite filtragem combinando opções como `categoria`, `extensao`, `evento`, `data_evento`, entre outros.
* **Buscas Tolerantes a Falhas:** Validações tolerantes a formatação (maiúsculas/minúsculas) e capacidade de efetuar buscas parciais nas strings de datas (exemplo: procurar apenas pelo mês e ano `08/2027`).
* **Estatísticas Globais:** Fornece o resumo completo da ocupação de armazenamento físico e fragmentações analíticas por eventos e categorias.

### 3. O Auditor (Segurança e Auditoria)
* **Verificação de Integridade:** Geração de assinatura dinâmica através de leitura em blocos do arquivo binário, otimizando o consumo de memória RAM no servidor. O auditor recalcula e expõe desvios e corrupções, baseando-se no algoritmo de hash parametrizado.
* **Exportação CSV:** Converte o catálogo atual de metadados em JSON para Planilhas CSV estruturadas instantaneamente.
* **Exportação de Domínio (XML):** Extrai todo o ecossistema e documentos de um *Único Evento* selecionado para um formato hierárquico XML robusto via `xml.etree`.
* **Backups Automáticos:** Rotas exclusivas de empacotamento que geram cópias compactadas (`.zip`) de todo o diretório de armazenamento.

## Stack Tecnológica
* **Python**
* **FastAPI** 
* **Uvicorn**
* **Pydantic**
* **PyYAML** 

## Como Instalar e Executar

1. **Instale as dependências:**
   ```bash
   pip install fastapi uvicorn python-multipart pydantic pyyaml
   ```

2. **Inicie o servidor local ASGI:**
   ```bash
   python -m uvicorn main:app --reload
   ```

3. **Acesse e interaja com a API (Swagger):**
   Abra seu navegador no link [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Toda a documentação e os testes práticos de manipulação de arquivos podem ser feitos por essa interface interativa.

## Arquitetura Baseada em Arquivos de Configuração
O código-fonte desacopla os caminhos absolutos e as regras de limite. Todas as propriedades (pastas destino, limites flexíveis de arquivo e tipo de algoritmo Hash) são herdadas de forma declarativa do arquivo raiz `config.yaml`. Quando a API inicia, os diretórios necessários são construídos baseando-se estritamente nestes parâmetros globais.

---
*Tema 11: Documentação de Eventos (Trabalho Prático - Persistência)*
