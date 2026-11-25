from dataclasses import dataclass
import json
import re
import textwrap
import unicodedata
from pathlib import Path

DIRETORIO_BASE = Path(__file__).resolve().parent
PASTA_BASE = DIRETORIO_BASE / "base"
VERSAO_BASE = 2


@dataclass
class Document:
    page_content: str
    metadata: dict


def arquivos_base(extensao):
    """Aceita a estrutura original e a pasta base, sem indexar cópias duplicadas."""
    arquivos = {p.name: p for p in DIRETORIO_BASE.glob(f"*.{extensao}")}
    arquivos.update({p.name: p for p in PASTA_BASE.glob(f"*.{extensao}")})
    return [arquivos[nome] for nome in sorted(arquivos)]

#========================
# NARMALIZAR O TEXTO
#========================

def normalizar_texto(texto):

    # Normalizar caracteres Unicode
    texto = unicodedata.normalize("NFKC", texto)

    # Remover caracteres invisíveis específicos
    texto = texto.replace("\ufeff", "")
    texto = texto.replace("\u00ad", "")
    texto = texto.replace("\u200b", "")

    # Padronizar quebras de linha
    texto = texto.replace("\r\n", "\n")
    texto = texto.replace("\r", "\n")

    # Remover caracteres de controle
    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Cc"
        or caractere in "\n\t"
    )

    # Remover espaços duplicados
    texto = re.sub(r"[ \t]+", " ", texto)

    # Corrigir espaços antes de sinais de pontuação
    texto = re.sub(r"[ \t]+([,.;:!?])", r"\1", texto)

    # Remover espaços nas extremidades das linhas
    linhas = [
        linha.strip()
        for linha in texto.splitlines()
    ]

    # Preservar a separação entre parágrafos
    texto = "\n".join(linhas)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()

#=================================
# LIMPAR OS CARACTERES DO CETRAS
#=================================

def limpar_texto_cetras(texto, pagina):

    # Corrigir nomes dos órgãos
    texto = texto.replace("CPRH/SEM AS", "CPRH/SEMAS")
    texto = texto.replace("ICMBio/M M A", "ICMBio/MMA")

    # Corrigir espaços entre autoria taxonômica e família
    texto = re.sub(
        r"(\))(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])",
        r"\1 ",
        texto
    )

    texto = re.sub(
        r"(\b(?:17|18|19|20)\d{2})(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])",
        r"\1 ",
        texto
    )

    # Siglas presentes nos mapas
    estados = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF",
        "ES", "GO", "MA", "MT", "MS", "MG", "PA",
        "PB", "PR", "PE", "PI", "RJ", "RN", "RS",
        "RO", "RR", "SC", "SP", "SE", "TO"
    }

    linhas = []

    for linha in texto.splitlines():

        linha_limpa = linha.strip()

        if not linha_limpa:
            continue

        # Remover siglas isoladas dos mapas
        if linha_limpa in estados:
            continue

        # Remover créditos fotográficos
        if linha_limpa.lower().startswith("foto:"):
            continue

        # Remover número da página
        if linha_limpa == str(pagina):
            continue

        linhas.append(linha_limpa)

    texto = "\n".join(linhas)

    # Corrigir expressões divididas em linhas
    expressoes = {
        r"ESPÉCIE\s+ENDÊMICA":
            "ESPÉCIE ENDÊMICA",

        r"INTERESSE\s+ZOONÓTICO":
            "INTERESSE ZOONÓTICO",

        r"ESPÉCIE\s+EXÓTICA\s+EM\s+PERNAMBUCO":
            "ESPÉCIE EXÓTICA EM PERNAMBUCO",

        r"Mata\s+Atlântica":
            "Mata Atlântica",

        r"Sistema\s+Costeiro-Marinho":
            "Sistema Costeiro-Marinho",

        r"Internacional\s*-\s*IUCN":
            "Internacional - IUCN"
    }

    for padrao, substituicao in expressoes.items():

        texto = re.sub(
            padrao,
            substituicao,
            texto,
            flags=re.IGNORECASE
        )

    return texto.strip()

#======================================================
# ORGANIZAÇÃO DA APRESENTAÇÃO DOS DADOS DO PDF CETRAS
#======================================================


def organizar_ficha_cetras(texto):

    linhas = [
        linha.strip()
        for linha in texto.splitlines()
        if linha.strip()
    ]

    ficha = {}
    campos_utilizados = set()

    # =========================================
    # 1. IDENTIFICAR NOME E AUTORIA TAXONÔMICA
    # =========================================

    for i, linha in enumerate(linhas):

        nome_cientifico = re.fullmatch(
            r"[A-Z][a-z-]+(?:\s+[a-z][a-z-]+){1,2}",
            linha
        )

        if not nome_cientifico:
            continue

        if i == 0 or i + 1 >= len(linhas):
            continue

        autoria = re.fullmatch(
            r"\(?[A-ZÀ-ÖØ-ÞŠ][\wÀ-ÿŠš.,&' -]*,"
            r"\s*\d{4}\)?",
            linhas[i + 1]
        )

        if autoria:

            ficha["Nome popular"] = linhas[i - 1]
            ficha["Nome científico"] = linha
            ficha["Autoria taxonômica"] = linhas[i + 1]

            campos_utilizados.update({
                i - 1,
                i,
                i + 1
            })

            break

    # =========================================
    # 2. IDENTIFICAR FAMÍLIA
    # =========================================

    for i, linha in enumerate(linhas):

        resultado = re.search(
            r"\b([A-Z][a-z]+idae)\b",
            linha
        )

        if resultado:

            ficha["Família"] = resultado.group(1)

            campos_utilizados.add(i)

            break


    # =========================================
    # 3. IDENTIFICAR ORDEM
    # =========================================

    ordens = {
        "Decapoda",
        "Crocodylia",
        "Testudines",
        "Squamata",
        "Accipitriformes",
        "Passeriformes",
        "Psittaciformes",
        "Strigiformes",
        "Pelecaniformes",
        "Charadriiformes",
        "Columbiformes",
        "Piciformes",
        "Falconiformes",
        "Pilosa",
        "Primates",
        "Carnivora",
        "Rodentia",
        "Cingulata",
        "Didelphimorphia",
        "Cetartiodactyla"
    }

    # Priorizar a ordem presente no PDF
    for i, linha in enumerate(linhas):

        if linha in ordens:

            ficha["Ordem"] = linha

            campos_utilizados.add(i)

            break

    # Relação entre famílias e ordens taxonômicas
    familias_ordens = {
        "Ucididae": "Decapoda",
        "Alligatoridae": "Crocodylia",
        "Boidae": "Squamata",
        "Iguanidae": "Squamata",
        "Chelidae": "Testudines",
        "Podocnemididae": "Testudines",
        "Testudinidae": "Testudines",
        "Accipitridae": "Accipitriformes",
        "Columbidae": "Columbiformes",
        "Falconidae": "Falconiformes",
        "Cardinalidae": "Passeriformes",
        "Fringillidae": "Passeriformes",
        "Icteridae": "Passeriformes",
        "Passerellidae": "Passeriformes",
        "Thraupidae": "Passeriformes",
        "Turdidae": "Passeriformes",
        "Tyrannidae": "Passeriformes",
        "Psittacidae": "Psittaciformes",
        "Strigidae": "Strigiformes",
        "Tytonidae": "Strigiformes",
        "Bradypodidae": "Pilosa",
        "Cebidae": "Primates",
        "Didelphidae": "Didelphimorphia",
        "Erethizontidae": "Rodentia",
        "Procyonidae": "Carnivora"
    }

    # Complementar a ordem somente quando ausente
    if "Ordem" not in ficha:

        familia = ficha.get("Família", "")

        if familia in familias_ordens:

            ficha["Ordem"] = familias_ordens[familia]

            ficha["Origem da ordem"] = (
                "Classificação taxonômica baseada na família"
            )

    # =========================================
    # 4. IDENTIFICAR TAMANHO CORPORAL
    # =========================================

    for i, linha in enumerate(linhas):

        resultado = re.fullmatch(
            r"(?:CT|CCC)\s*~?\s*\d+(?:[.,]\d+)?"
            r"\s*(?:mm|cm|m)",
            linha,
            flags=re.IGNORECASE
        )

        if resultado:

            ficha["Tamanho corporal"] = linha

            campos_utilizados.add(i)

            break

    # =========================================
    # 5. IDENTIFICAR BIOMAS
    # =========================================

    biomas_possiveis = [
        "Amazônia",
        "Caatinga",
        "Cerrado",
        "Mata Atlântica",
        "Pampa",
        "Pantanal",
        "Sistema Costeiro-Marinho"
    ]

    biomas_encontrados = []

    for i, linha in enumerate(linhas):

        encontrados = [
            bioma
            for bioma in biomas_possiveis
            if bioma.lower() in linha.lower()
        ]

        if encontrados:

            biomas_encontrados.extend(encontrados)

            campos_utilizados.add(i)

    # Remover duplicidades mantendo a ordem
    biomas_encontrados = list(
        dict.fromkeys(biomas_encontrados)
    )

    if biomas_encontrados:

        ficha["Biomas"] = " | ".join(
            biomas_encontrados
        )

    # =========================================
    # 6. IDENTIFICAR STATUS DE CONSERVAÇÃO
    # =========================================

    orgaos = {
        "Estadual - CPRH/SEMAS": "Estadual",
        "Nacional - ICMBio/MMA": "Nacional",
        "Internacional - IUCN": "Internacional"
    }

    categorias = {
        "EX": "Extinta",
        "EW": "Extinta na natureza",
        "RE": "Regionalmente extinta",
        "CR": "Criticamente em perigo",
        "EN": "Em perigo",
        "VU": "Vulnerável",
        "NT": "Quase ameaçada",
        "LC": "Pouco preocupante",
        "DD": "Dados insuficientes",
        "NE": "Não avaliada",
        "NA": "Não aplicável"
    }

    orgaos_encontrados = []
    codigos_encontrados = []
    status_diretos = {}

    for i, linha in enumerate(linhas):

        for orgao, abrangencia in orgaos.items():

            if linha.lower() == orgao.lower():

                orgaos_encontrados.append(abrangencia)
                campos_utilizados.add(i)

                # Verificar se o código aparece imediatamente após o órgão
                if i + 1 < len(linhas):

                    codigo = linhas[i + 1].upper()

                    if codigo in categorias:

                        status_diretos[abrangencia] = codigo

        codigo = linha.upper()

        if codigo in categorias:

            codigos_encontrados.append(codigo)

            campos_utilizados.add(i)

    # Padrão intercalado:
    # órgão seguido diretamente de seu código
    if (
        len(status_diretos) == 3
        and len(codigos_encontrados) == 3
    ):

        status = []

        for abrangencia, codigo in status_diretos.items():

            status.append(
                f"{abrangencia}: "
                f"{codigo} ({categorias[codigo]})"
            )

        ficha["Status de conservação"] = " | ".join(status)

    # Padrão agrupado ou extração incompleta:
    # preservar os códigos sem atribuição incerta
    elif codigos_encontrados:

        ficha["Órgãos de conservação"] = " | ".join(
            orgaos_encontrados
        )

        ficha["Categorias de conservação extraídas"] = " | ".join(
            f"{codigo} ({categorias[codigo]})"
            for codigo in codigos_encontrados
        )

        ficha["Observação sobre conservação"] = (
            "A associação individual entre os códigos "
            "e os órgãos não foi confirmada."
        )

    # =========================================
    # 7. IDENTIFICAR INFORMAÇÕES ADICIONAIS
    # =========================================

    informacoes_possiveis = {
        "INTERESSE ZOONÓTICO": "Interesse zoonótico",
        "ESPÉCIE ENDÊMICA": "Espécie endêmica",
        "ESPÉCIE EXÓTICA EM PERNAMBUCO":
            "Espécie exótica em Pernambuco"
    }

    informacoes = []

    for i, linha in enumerate(linhas):

        linha_upper = linha.upper()

        if linha_upper in informacoes_possiveis:

            informacoes.append(
                informacoes_possiveis[linha_upper]
            )

            campos_utilizados.add(i)

    if informacoes:

        ficha["Informações adicionais"] = " | ".join(
            dict.fromkeys(informacoes)
        )

    # =========================================
    # 8. PRESERVAR INFORMAÇÕES NÃO IDENTIFICADAS
    # =========================================

    rotulos = {
        "distribuição geográfica",
        "status de conservação",
        "biomas",
        "tamanho corporal"
    }

    outras_informacoes = [
        linha
        for i, linha in enumerate(linhas)
        if i not in campos_utilizados
        and linha.lower() not in rotulos
    ]

    if outras_informacoes:

        ficha["Outras informações extraídas"] = (
            " | ".join(outras_informacoes)
        )

    return ficha

#========================
# CARREGAMENTO DO PDF
#========================

def carregar_pdf():

    from pypdf import PdfReader

    documentos = []
    for caminho in arquivos_base("pdf"):
        for indice, pagina_pdf in enumerate(PdfReader(caminho).pages):
            documentos.append(Document(
                page_content=pagina_pdf.extract_text() or "",
                metadata={"source": str(caminho), "page": indice}
            ))

    if not documentos:
        raise FileNotFoundError("Nenhum PDF encontrado na raiz do projeto ou na pasta base.")

    arquivos = {
        documento.metadata.get("source", "")
        for documento in documentos
    }

    print("\nPDFs encontrados:")

    for arquivo in sorted(arquivos):
        print(arquivo)

    documentos_filtrados = []

    for documento in documentos:

        documento.metadata["tipo"] = "pdf"
        documento.metadata["versao_base"] = VERSAO_BASE

        origem = documento.metadata.get("source", "")
        pagina = documento.metadata.get("page", 0) + 1

        documento.metadata["origem"] = origem
        documento.metadata["pagina"] = pagina

        nome_arquivo = Path(origem).name.lower()

        # Normalizar o texto
        documento.page_content = normalizar_texto(
            documento.page_content
        )

        # Tratamento específico do PDF da Caatinga
        if nome_arquivo == "bioma-caatinga.pdf":

            # Página 1: iniciar a leitura a partir de RESUMO
            if pagina == 1:

                resultado = re.search(
                    r"\bRESUMO\b",
                    documento.page_content,
                    re.IGNORECASE
                )

                if resultado:
                    documento.page_content = documento.page_content[
                        resultado.start():
                    ]

            # Página 8: remover referências bibliográficas
            elif pagina == 8:

                documento.page_content = re.split(
                    r"\bREFERÊNCIAS\b",
                    documento.page_content,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )[0].strip()

        # Filtrar páginas do CETRAS
        if "cetras" in nome_arquivo:

            if not (12 <= pagina <= 65):
                continue

            # Ignorar capas dos grupos de animais
            if pagina in [16, 18, 25, 60]:
                continue

            # Limpar texto das páginas aproveitadas
            documento.page_content = limpar_texto_cetras(
                documento.page_content,
                pagina
            )

            # Organizar somente as fichas de animais
            if pagina >= 17:

                texto_original = documento.page_content

                ficha = organizar_ficha_cetras(
                    texto_original
                )

                if not ficha.get("Nome popular") or not ficha.get("Nome científico"):
                    raise ValueError(
                        f"Não foi possível identificar a espécie em {nome_arquivo}, página {pagina}. "
                        "A indexação foi interrompida para evitar uma lista incompleta."
                    )

                texto_organizado = "\n".join(
                    f"{campo}: {valor}"
                    for campo, valor in ficha.items()
                )

                documento.page_content = (
                    texto_organizado
                    + "\n\nTexto extraído da ficha:\n"
                    + texto_original
                )

                # Adicionar metadados específicos do animal
                documento.metadata["nome_animal"] = ficha.get(
                    "Nome popular", ""
                )

                documento.metadata["nome_cientifico"] = ficha.get(
                    "Nome científico", ""
                )

                documento.metadata["familia"] = ficha.get(
                    "Família", ""
                )

                documento.metadata["ordem"] = ficha.get(
                    "Ordem", ""
                )

                documento.metadata["categoria"] = "ficha_animal"
                documento.metadata["campos"] = json.dumps(ficha, ensure_ascii=False)

        # Identificar grupo
        grupo = identificar_grupo(pagina, origem)

        if grupo:
            documento.metadata["grupo"] = grupo

        # Ignorar documentos vazios
        if not documento.page_content.strip():
            continue

        # Exibir informações do CETRAS
        if "cetras" in nome_arquivo:

            print(
                f"Página {pagina} | "
                f"Caracteres extraídos: "
                f"{len(documento.page_content.strip())}"
            )

        print(f"Página: {pagina} | Grupo: {grupo}")

        documentos_filtrados.append(documento)

    print("\nCarregamento concluído!")
    print("Total de documentos:", len(documentos_filtrados))

    return documentos_filtrados

#=============================================================
# IDENTIFICAÇÃO DOS GRUPOS DOS ANIMAIS - AVES, MAMÍFEROS...
#=============================================================

def identificar_grupo(pagina, origem):

    nome_arquivo = Path(origem).name.lower()

    if "cetras" not in nome_arquivo:
        return None

    if "cetras" not in origem.lower():
        return None

    if 16 <= pagina < 18:
        return "Invertebrados marinhos"

    elif 18 <= pagina < 25:
        return "Répteis"

    elif 25 <= pagina < 60:
        return "Aves"

    elif pagina >= 60:
        return "Mamíferos"

    return None

#=================================
# CARREGAMENTO DO JSON
#=================================

def carregar_json():


    documentos = []

    caminho_json = next(
        (p for p in arquivos_base("json") if p.name == "fauna_pee.json"), None
    )
    if caminho_json is None:
        raise FileNotFoundError("Arquivo fauna_pee.json não encontrado na raiz ou na pasta base.")

    with open(caminho_json, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    especies = dados.get("especies_ameacadas", [])

    for animal in especies:

        # Transformar os dados do animal em texto
        texto = f"""
        Nome popular: {animal.get('nome_popular', '')}
        Nome científico: {animal.get('nome_cientifico', '')}
        Situação: {animal.get('situacao', '')}
        Classe: {animal.get('classe', '')}

        Habitat: {', '.join(animal.get('habitat', []))}
        Alimentação: {', '.join(animal.get('alimentacao', []))}

        Características:
        {json.dumps(animal.get('caracteristicas', {}), ensure_ascii=False, indent=2)}

        Principais ameaças:
        {', '.join(animal.get('principais_ameacas', []))}

        Pokémon semelhante:
        {json.dumps(animal.get('pokemon_semelhante', {}), ensure_ascii=False, indent=2)}

        Curiosidades:
        {json.dumps(animal.get('curiosidades', {}), ensure_ascii=False, indent=2)}
        """

        texto = textwrap.dedent(texto).strip()

        # Criar documento LangChain
        documento = Document(
            page_content=texto,
            metadata={
                "origem": "fauna_pee.json",
                "tipo": "animal",
                "categoria": "comparacao_pokemon",
                "grupo": animal.get("classe", ""),
                "nome_animal": animal.get("nome_popular", ""),
                "nome_cientifico": animal.get("nome_cientifico", ""),
                "nome_pokemon": animal.get("pokemon_semelhante", {}).get("nome", ""),
                "versao_base": VERSAO_BASE,
                "campos": json.dumps({
                    "Habitat": ", ".join(animal.get("habitat", [])),
                    "Alimentação": ", ".join(animal.get("alimentacao", [])),
                    "Características": animal.get("caracteristicas", {}),
                    "Tamanho corporal": animal.get("caracteristicas", {}).get("tamanho", ""),
                    "Peso": animal.get("caracteristicas", {}).get("peso", ""),
                    "Expectativa de vida": animal.get("caracteristicas", {}).get("expectativa_vida", ""),
                    "Coloração": animal.get("caracteristicas", {}).get("coloracao", ""),
                    "Comportamento": animal.get("caracteristicas", {}).get("comportamento", ""),
                    "Status de conservação": animal.get("situacao", ""),
                    "Ameaças": ", ".join(animal.get("principais_ameacas", [])),
                    "Pokémon": animal.get("pokemon_semelhante", {}),
                    "Curiosidades": animal.get("curiosidades", {})
                }, ensure_ascii=False)
            }
        )

        documentos.append(documento)

    print(f"Quantidade de espécies carregadas: {len(documentos)}")

    return documentos
