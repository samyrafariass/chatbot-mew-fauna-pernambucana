import shutil
import os
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from carrega_base import carregar_pdf, carregar_json

DIRETORIO_BASE = Path(__file__).resolve().parent
CAMINHO_BANCO = str(DIRETORIO_BASE / "bd")
MODELO_EMBEDDING = "embeddinggemma"

#=====================================================
# CRIANDO O BANCO COM DOCUMENTO EM PEQUENAS PARTES
#=====================================================

def criar_bd():
    # carregar_documentos
    documentos_pdf = carregar_pdf()
    documentos_json = carregar_json()

    # verificar documentos em branco
    documentos_pdf = [
        doc for doc in documentos_pdf
        if doc.page_content.strip()
    ]

    documentos_json = [
        doc for doc in documentos_json
        if doc.page_content.strip()
    ]

    # Fichas completas preservam a espécie e seus campos no mesmo registro.
    fichas = [d for d in documentos_pdf if d.metadata.get("categoria") == "ficha_animal"]
    artigos = [d for d in documentos_pdf if d.metadata.get("categoria") != "ficha_animal"]
    chunks_pdf = dividir_chunks(artigos) + fichas

    # Manter cada espécie do JSON como documento independente
    chunks = chunks_pdf + documentos_json

    print("\n" + "=" * 60)
    print("\nResumo da preparação:")
    print(f"Documentos PDF: {len(documentos_pdf)}")
    print(f"Chunks PDF: {len(chunks_pdf)}")
    print(f"Documentos JSON: {len(documentos_json)}")
    print(f"Total para vetorização: {len(chunks)}")
    print("\n" + "=" * 60)

    if not chunks:
        print("Nenhum documento encontrado. Banco não criado.")
        return

    return vetorizar_chunks([Document(page_content=d.page_content, metadata=d.metadata) for d in chunks])

#============================================
# DIVIDINDO O DOCUMENTO EM PEQUENAS PARTES
#============================================

def dividir_chunks(documentos):

    separador_documentos = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        length_function=len,
        add_start_index=True
    )
    chunks = separador_documentos.split_documents(documentos)

    print("\n" + "=" * 60)
    print(f"Quantidade de documentos PDF: {len(documentos)}")
    print(f"Quantidade de chunks PDF: {len(chunks)}")
    print("\n" + "=" * 60)

    return chunks


#===========================
# VETORIZANDO OS CHUNKS
#===========================

def vetorizar_chunks(chunks):

    # Recriar o banco para evitar documentos antigos e duplicados
    if os.path.exists(CAMINHO_BANCO):
        shutil.rmtree(CAMINHO_BANCO)

    db = Chroma.from_documents(chunks, OllamaEmbeddings(model=MODELO_EMBEDDING), persist_directory=CAMINHO_BANCO)
    print("Banco de dados criado!")

    return db

#=======================================
# CRIANDO O BANCO
#=======================================

if __name__ == "__main__":
    criar_bd()
