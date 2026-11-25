import streamlit as st
from main import perguntar, identificar_animal, normalizar, modo_catalogo

# Configuração da página
st.set_page_config(
    page_title="Chat Mew | Fauna de Pernambuco",
    page_icon="🐾",
    layout="centered"
)

st.title("Chat Mew")
catalogo = modo_catalogo()
st.caption("Fauna de Pernambuco · " + ("Modo catálogo" if catalogo else "Modo com Ollama"))


def exibir_resposta(texto):
    mensagem, separador, trechos = texto.partition("\n\nTrechos consultados:\n\n")
    st.markdown(mensagem)
    if separador:
        with st.expander("Conferir trechos consultados"):
            st.text(trechos.replace("**", ""))


# Inicializar o histórico da conversa
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

# Armazenar o último animal identificado
if "animal_atual" not in st.session_state:
    st.session_state.animal_atual = None

if "animal_sugerido" not in st.session_state:
    st.session_state.animal_sugerido = None

if "pergunta_pendente" not in st.session_state:
    st.session_state.pergunta_pendente = None

pergunta = None
exemplos = [
    "Quais mamíferos aparecem no catálogo do CETRAS?",
    "Compare dois Pokémon com as espécies disponíveis.",
    "Que atividade com Pokémon os alunos fizeram segundo os artigos?",
]
for i, exemplo in enumerate(exemplos):
    if st.button(exemplo, key=f"sugestao_{i}", disabled=catalogo and i == 2,
                 help="Disponível no modo com Ollama" if catalogo and i == 2 else None):
        pergunta = exemplo

# Exibir o histórico
for mensagem in st.session_state.mensagens:

    with st.chat_message(mensagem["role"]):
        if mensagem["role"] == "assistant":
            exibir_resposta(mensagem["content"])
        else:
            st.markdown(mensagem["content"])

# Campo para digitar a pergunta
pergunta = st.chat_input("Pergunte sobre a fauna de Pernambuco...") or pergunta



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

            resposta = "Tudo bem! Digite novamente o nome do animal."

        else:

            resposta = "Responda apenas sim ou não para confirmar o animal."

    else:

        # Identificar o animal mencionado
        animal_mencionado, sugestao_animal = identificar_animal(pergunta)

        if sugestao_animal:

            st.session_state.animal_sugerido = sugestao_animal
            st.session_state.pergunta_pendente = pergunta

            resposta = (
                f"Você quis dizer **{sugestao_animal}**? "
                "Responda sim ou não."
            )

        elif animal_mencionado:

            st.session_state.animal_atual = animal_mencionado

    # Consultar o backend somente quando não houver confirmação pendente
    if resposta is None:

        animal_referenciado = st.session_state.animal_atual

        with st.chat_message("assistant"):

            with st.spinner("Pensando..."):

                try:
                    resposta = perguntar(
                        pergunta_processamento,
                        animal_referenciado,
                        st.session_state.setdefault("contexto_lista", [])
                    )

                    exibir_resposta(resposta)

                except Exception as erro:
                    resposta = "Ocorreu um erro ao processar sua pergunta. Tente novamente!"
                    st.error(resposta)
                    st.exception(erro)

    else:

        with st.chat_message("assistant"):
            st.markdown(resposta)

    # Salvar resposta
    st.session_state.mensagens.append({
        "role": "assistant",
        "content": resposta
    })


if st.button("Limpar conversa"):
    st.session_state.contexto_lista = []
    st.session_state.mensagens = []
    st.session_state.animal_atual = None
    st.session_state.animal_sugerido = None
    st.session_state.pergunta_pendente = None

    st.rerun()
