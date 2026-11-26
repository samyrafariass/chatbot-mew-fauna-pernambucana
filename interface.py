import streamlit as st
import time
import json
from datetime import datetime
from pathlib import Path
from main import perguntar, identificar_animal, normalizar, modo_catalogo

# Diretório base do projeto e busca automática pela imagem da Jessie
DIRETORIO_BASE = Path(__file__).resolve().parent

SUGESTOES_PERGUNTAS = [
    "Quais mamíferos aparecem no catálogo do CETRAS?",
    "Quais deles vivem na Caatinga?",
    "Quais desses vivem na Mata Atlântica?",
    "Compare Pikachu com um animal",
    "Que atividade com Pokémon os alunos fizeram segundo os artigos?",
    "Qual o habitat e a alimentação da preguiça-comum?",
]


def obter_imagem_jessie():
    nomes_possiveis = [
        "jessie_carregando.gif",
        "jessie_carregando.png",
        "jessie_carregando.jpg",
        "jessie_carregando.jpeg",
        "jessie.gif",
        "jessie.png",
        "jessie.jpg",
    ]
    for nome in nomes_possiveis:
        caminho = DIRETORIO_BASE / nome
        if caminho.is_file():
            return str(caminho)
    return None


def exibir_resposta_assistente(conteudo):
    separador = "\n\nTrechos consultados:\n\n"
    if separador in conteudo:
        texto_principal, trechos = conteudo.split(separador, 1)
        st.markdown(texto_principal)
        with st.expander("Conferir trechos consultados"):
            st.markdown(trechos)
    else:
        st.markdown(conteudo)


# Configuração da página
st.set_page_config(
    page_title="Universo Pokémon na Fauna Pernambucana",
    page_icon="🦋",
    layout="centered"
)

# Título e indicador de modo
st.title("🦋 Fauna Pernambucana dentro do Universo Pokémon")
st.subheader("Conheça a biodiversidade de Pernambuco!")

if modo_catalogo():
    st.caption("Modo ativo: **Catálogo (sem Ollama)** — consultas diretas às fichas e ao JSON.")
else:
    st.caption("Modo ativo: **Completo com Ollama (RAG + Catálogo)** — Jessie ativa para perguntas abertas e consultas.")

st.write("Converse com a Jessie e descubra curiosidades sobre os animais, seus habitats e suas semelhanças com os Pokémon!")
st.divider()

# Inicializar o histórico da conversa
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

# Armazenar o último animal identificado e contexto de listas
if "animal_atual" not in st.session_state:
    st.session_state.animal_atual = None

if "animal_sugerido" not in st.session_state:
    st.session_state.animal_sugerido = None

if "pergunta_pendente" not in st.session_state:
    st.session_state.pergunta_pendente = None

if "contexto_lista" not in st.session_state:
    st.session_state.contexto_lista = []

imagem_jessie = obter_imagem_jessie()

# Exibir o histórico da conversa
for mensagem in st.session_state.mensagens:
    if mensagem["role"] == "assistant":
        with st.chat_message("assistant", avatar=imagem_jessie):
            exibir_resposta_assistente(mensagem["content"])
    else:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])

# Caixas de perguntas sugeridas (clicáveis)
st.markdown("**💡 Sugestões de perguntas (clique para enviar):**")
pergunta_clicada = None
colunas = st.columns(2)
for idx, texto_sugestao in enumerate(SUGESTOES_PERGUNTAS):
    with colunas[idx % 2]:
        if st.button(texto_sugestao, key=f"sugestao_{idx}", use_container_width=True):
            pergunta_clicada = texto_sugestao

# Botão para limpar a conversa
if st.button("Limpar conversa"):
    st.session_state.mensagens = []
    st.session_state.animal_atual = None
    st.session_state.animal_sugerido = None
    st.session_state.pergunta_pendente = None
    st.session_state.contexto_lista = []
    st.rerun()

# Campo fixo na parte inferior para digitar qualquer pergunta
pergunta_digitada = st.chat_input("Pergunte sobre a fauna de Pernambuco...")
pergunta = pergunta_digitada or pergunta_clicada

if pergunta:

    # Mostrar pergunta do usuário
    st.session_state.mensagens.append({
        "role": "user",
        "content": pergunta
    })

    with st.chat_message("user"):
        st.markdown(pergunta)

    resposta = None
    pergunta_processamento = pergunta

    # Verificar se existe uma confirmação pendente
    if st.session_state.animal_sugerido:

        confirmacao = normalizar(pergunta)

        respostas_sim = ["sim", "s", "isso", "correto", "exatamente"]
        respostas_nao = ["nao", "n", "negativo", "errado"]

        if confirmacao in respostas_sim:
            animal_confirmado = st.session_state.animal_sugerido
            pergunta_processamento = (
                st.session_state.pergunta_pendente
                + " "
                + animal_confirmado
            )
            st.session_state.animal_atual = animal_confirmado
            st.session_state.animal_sugerido = None
            st.session_state.pergunta_pendente = None

        elif confirmacao in respostas_nao:
            st.session_state.animal_sugerido = None
            st.session_state.pergunta_pendente = None
            resposta = "Tudo bem, twip! Digite novamente o nome do animal."

        else:
            resposta = "Responda apenas sim ou não para confirmar o animal, twip."

    else:
        # Identificar o animal mencionado
        animal_mencionado, sugestao_animal = identificar_animal(pergunta)

        if sugestao_animal:
            st.session_state.animal_sugerido = sugestao_animal
            st.session_state.pergunta_pendente = pergunta
            resposta = (
                f"Você quis dizer **{sugestao_animal}**, twip? "
                "Responda sim ou não."
            )
        elif animal_mencionado:
            st.session_state.animal_atual = animal_mencionado

    # Consultar o backend somente quando não houver confirmação pendente
    if resposta is None:

        animal_referenciado = st.session_state.animal_atual

        with st.chat_message("assistant", avatar=imagem_jessie):
            placeholder_carregando = st.empty()

            with placeholder_carregando.container():
                if imagem_jessie:
                    col_img, col_txt = st.columns([1, 4])
                    with col_img:
                        st.image(imagem_jessie, width=110)
                    with col_txt:
                        st.info("Prepare-se para encrenca! A Jessie está vasculhando a base de conhecimento do Projeto MEW...")
                else:
                    st.info("Prepare-se para encrenca! A Jessie está vasculhando a base de conhecimento do Projeto MEW...")

            try:
                inicio_timer = time.perf_counter()

                resposta = perguntar(
                    pergunta_processamento,
                    animal_referenciado,
                    st.session_state.contexto_lista
                )

                latencia = round(time.perf_counter() - inicio_timer, 3)

                registro_log = {
                    "timestamp": datetime.now().isoformat(),
                    "pergunta": pergunta,
                    "latencia_segundos": latencia,
                    "tamanho_resposta": len(str(resposta)),
                }

                with open("logs_interacao.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(registro_log, ensure_ascii=False) + "\n")

                placeholder_carregando.empty()
                exibir_resposta_assistente(resposta)

            except Exception as erro:
                placeholder_carregando.empty()
                resposta = "Ocorreu um erro ao processar sua pergunta. Tente novamente!"
                st.error(resposta)
                st.exception(erro)

    else:
        with st.chat_message("assistant", avatar=imagem_jessie):
            exibir_resposta_assistente(resposta)

    # Salvar resposta no histórico
    st.session_state.mensagens.append({
        "role": "assistant",
        "content": resposta
    })