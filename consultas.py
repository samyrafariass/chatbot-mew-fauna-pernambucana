"""Consultas de catálogo e de campos: respostas completas sem depender do LLM."""

import json
import re
import unicodedata


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def contem(texto, termo):
    return f" {termo} " in f" {texto} "


def identificar_campos(pergunta):
    texto = normalizar(pergunta)
    termos = {
        "Habitat": ("habitat", "habitats", "bioma", "biomas", "onde vive", "onde vivem",
                    "onde ele vive", "onde ela vive", "onde eles vivem", "onde elas vivem",
                    "vive onde", "vivem onde", "em que ambiente", "em quais ambientes"),
        "Alimentação": ("alimentacao", "dieta", "o que come", "o que comem",
                        "come", "comem", "o que ele come", "o que ela come",
                        "se alimenta", "se alimentam"),
        "Tamanho corporal": ("tamanho", "comprimento", "medida", "medidas"),
        "Peso": ("peso", "pesa", "pesam"),
        "Expectativa de vida": ("expectativa de vida", "quanto tempo vive", "quantos anos vive"),
        "Coloração": ("coloracao", "cor", "cores"),
        "Comportamento": ("comportamento", "comportamentos", "habitos"),
        "Ameaças": ("ameacas", "ameaca", "riscos"),
        "Status de conservação": ("conservacao", "status", "situacao"),
        "Reprodução": ("reproducao", "reproduz", "reproduzem", "gestacao"),
        "Características": ("caracteristica", "caracteristicas"),
        "Curiosidades": ("curiosidade", "curiosidades"),
        "Importância ecológica": ("importancia", "papel ecologico"),
        "Família": ("familia",),
        "Ordem": ("ordem",),
    }
    # Comparações e justificativas sobre Pokémon precisam do contexto relacional.
    if contem(texto, "pokemon"):
        return []
    campos = [campo for campo, aliases in termos.items()
            if any(contem(texto, alias) and not re.search(
                rf"\b(?:sem|nao inclua|nao inclua a|nao fale sobre|nao fale sobre a) {re.escape(alias)}\b",
                texto) for alias in aliases)]
    if "Habitat" not in campos and re.search(r"\bonde\b.*\b(?:vive|vivem|habita|habitam)\b", texto):
        campos.insert(0, "Habitat")
    return campos


def ler_campos(metadata):
    return json.loads(metadata.get("campos", "{}"))


def fonte_ficha(m):
    if m.get("tipo") == "animal":
        return "fauna_pee.json"
    return f"Catálogo do CETRAS, p. {m['pagina']}"


def comparar_pares_pokemon(texto, registros):
    """Usa as associações educativas cadastradas para pedidos de exemplos."""
    if not (re.search(r"\bcompar\w*", texto) and
            re.search(r"\b(pokemons?|especies?|animais|animal|fauna)\b", texto)):
        return None
    if re.search(r"\b(pdf|artigo[s]?|cetras)\b", texto):
        return None
    numeros = {"um": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5}
    pedido = re.search(r"\b(\d+|um|dois|duas|tres|quatro|cinco) pokemons?\b", texto)
    pares = {}
    for registro in registros:
        if registro.get("tipo") != "animal":
            continue
        dados = ler_campos(registro).get("Pokémon") or {}
        if dados.get("nome"):
            pares[dados["nome"]] = (registro["nome_animal"], dados)
    citados = [p for p in pares if contem(texto, normalizar(p)) or
               contem(texto, normalizar(pares[p][0]))]
    # Nomes explícitos como "compare Pikachu e Heatmor com as espécies".
    alvo = re.search(r"\bcompar(?:e|ar|a)\s+(.+?)\s+(?:com|aos?)\b", texto)
    desconhecidos = []
    if alvo:
        for parte in re.split(r"\s+e\s+", alvo[1]):
            parte = re.sub(r"^(?:(?:o|a|os|as|pokemon[s]?|dois|duas|um|tres|quatro|cinco|\d+)\s+)*", "", parte).strip()
            if (parte and len(parte.split()) == 1 and parte not in
                    {"pokemon", "pokemons", "animais", "especies", "especie", "animal"}
                    and not parte.isdigit() and parte not in numeros
                    and not any(contem(parte, normalizar(p)) for p in citados)):
                desconhecidos.append(parte)
    if desconhecidos:
        opcoes = ", ".join(sorted(pares))
        return (f"Não encontrei par cadastrado para {', '.join(n.capitalize() for n in desconhecidos)}. "
                f"Pokémon disponíveis: {opcoes}.\n\nFonte: fauna_pee.json.")
    if not pedido and not citados:
        return None
    quantidade = len(citados)
    if pedido:
        n = pedido.group(1)
        quantidade = int(n) if n.isdecimal() else numeros[n]
    ordem = citados + sorted(set(pares) - set(citados))
    linhas = []
    if quantidade > len(ordem):
        linhas.append(f"O cadastro contém apenas {len(ordem)} pares.")
    for nome in ordem[:quantidade]:
        animal, dados = pares[nome]
        linhas.append(f"**{nome} e {animal}**")
        for campo, rotulo in (("similaridade_visual", "Semelhança visual"),
                              ("diferencas", "Diferença")):
            valores = dados.get(campo)
            if valores:
                linhas.append(f"- {rotulo}: {valores[0]}")
        linhas.append("")
    linhas.append("Fonte: fauna_pee.json (comparações educativas).")
    return "\n".join(linhas)


def formatar_valor(valor):
    if isinstance(valor, dict):
        return "; ".join(f"{k.replace('_', ' ')}: {formatar_valor(v)}"
                         for k, v in valor.items() if v)
    if isinstance(valor, list):
        return "; ".join(formatar_valor(v) for v in valor)
    return str(valor)


def responder_campos(registros, campos, nome):
    registros = sorted(registros, key=lambda m: 0 if m.get("tipo") == "animal" else 1)
    linhas = [f"**{nome}**"]
    for campo in campos:
        valor = None
        rotulo = campo
        for registro in registros:
            dados = ler_campos(registro)
            valor = dados.get(campo)
            if campo == "Habitat" and not valor and dados.get("Biomas"):
                valor = dados["Biomas"]
                rotulo = "Biomas registrados no PDF"
            if campo == "Importância ecológica" and not valor:
                valor = dados.get("Curiosidades", {}).get("importancia_ecologica")
            if campo == "Status de conservação" and not valor:
                valor = " ".join(dados.get(k, "") for k in (
                    "Categorias de conservação extraídas", "Observação sobre conservação")).strip()
            if valor:
                break
        if valor:
            linhas.append(f"- {rotulo}: {formatar_valor(valor).rstrip(chr(46))}. ({fonte_ficha(registro)})")
        else:
            fontes = ", ".join(dict.fromkeys(fonte_ficha(m) for m in registros))
            linhas.append(f"- {campo}: informação não encontrada nas fontes consultadas." + (f" ({fontes})" if fontes else ""))
    return "\n".join(linhas)


def especies_unicas(metadados, grupos=()):
    especies = {}
    for metadata in metadados:
        if not metadata or metadata.get("categoria") != "ficha_animal":
            continue
        if grupos and metadata.get("grupo") not in grupos:
            continue
        nome = metadata.get("nome_animal")
        chave = normalizar(metadata.get("nome_cientifico") or nome or "")
        if nome and chave:
            especies.setdefault(chave, metadata)
    return sorted(especies.values(), key=lambda m: normalizar(m["nome_animal"]))


def listagem_simples(texto, grupos, campos):
    """Não transforme um predicado desconhecido em uma lista de todo o grupo."""
    expressoes = list(grupos) + list(campos) + [
        "Amazônia", "Caatinga", "Cerrado", "Mata Atlântica", "Pampa", "Pantanal",
        "Sistema Costeiro-Marinho", "invertebrado marinho", "invertebrados marinhos",
        "réptil", "répteis", "ave", "aves", "pássaro", "pássaros", "mamífero", "mamíferos",
        "onde vivem", "onde vive", "em que ambiente", "em quais ambientes",
        "o que comem", "o que come", "expectativa de vida", "tamanho corporal",
        "centro de triagem", "centro de reabilitação", "centro de preservação",
    ]
    for expressao in sorted(expressoes, key=len, reverse=True):
        texto = re.sub(rf"\b{re.escape(normalizar(expressao))}\b", " ", texto)
    permitidas = set("""
        a as o os um uma uns umas de da das do dos e ou em na nas no nos
        para por pelo pela pelos pelas que se sao e ha tem existem quais
        qual quanto quanta quantos quantas quantidade numero total liste listar lista todos todas
        relacao nomes mostre mostra aparecem aparece constam consta figuram figura
        encontrados encontradas encontrado encontrada
        presentes presente registrados registradas documentados documentadas
        apresentados apresentadas citados citadas catalogados catalogadas
        cetras pdf pdfs documento documentos documentacao catalogo pernambuco pe
        estado segundo conforme acordo animais animal especies especie fauna
        vivem vive habitat habitats bioma biomas endemico endemica endemicos
        endemicas exotico exotica exoticos exoticas nao principais
    """.split())
    return all(palavra in permitidas for palavra in texto.split())


def consultar_catalogo(pergunta, metadados, grupos=(), campos=(), selecionadas=None):
    texto = normalizar(pergunta)
    contagem = any(contem(texto, t) for t in (
        "quantos", "quantas", "quantidade", "numero de", "total de"))
    listagem = any(contem(texto, t) for t in (
        "quais", "liste", "listar", "lista", "todos", "todas", "relacao", "nomes",
        "mostre", "mostra", "encontrados", "encontradas", "existem", "presentes",
        "aparecem", "aparece", "constam", "consta", "figuram", "figura"))
    escopo_geral = any(contem(texto, t) for t in ("cetras", "pdf")) and any(
        contem(texto, t) for t in ("animais", "especies", "fauna"))
    if not (grupos or escopo_geral) or not (contagem or listagem or campos):
        return None
    # Questões conceituais, relações com Pokémon e outros predicados não são
    # listagens simples. O chamador deve recuperar todo o grupo nesses casos.
    if any(contem(texto, t) for t in (
        "pokemon", "diferenca", "diferencas", "semelhanca", "semelhancas",
        "ameacadas", "ameacados", "extincao", "reabilitacao", "resgate",
        "noturnos", "diurnos", "herbivoros", "carnivoros", "onivoros",
        "comem", "alimentam", "maiores", "menores")):
        return None
    if not listagem_simples(texto, grupos, campos):
        return None

    especies = especies_unicas(metadados, grupos)
    biomas = [b for b in ("Amazônia", "Caatinga", "Cerrado", "Mata Atlântica", "Pampa",
                          "Pantanal", "Sistema Costeiro-Marinho")
              if contem(texto, normalizar(b))]
    if biomas:
        operador = any if contem(texto, "ou") else all
        especies = [m for m in especies if operador(
            contem(normalizar(ler_campos(m).get("Biomas", "")), normalizar(b))
            for b in biomas)]
    for termo, flag in (("endemic", "Espécie endêmica"), ("exotic", "Espécie exótica em Pernambuco")):
        if re.search(rf"\b{termo}[ao]s?\b", texto):
            negativo = re.search(rf"\bnao {termo}[ao]s?\b", texto) is not None
            especies = [m for m in especies if
                        (flag in ler_campos(m).get("Informações adicionais", "")) != negativo]

    if not especies:
        return "Não encontrei espécies com esses critérios na documentação do CETRAS."
    grupo = ", ".join(g.lower() for g in grupos) if grupos else "animais"
    recorte = " com os critérios solicitados" if biomas or re.search(r"\b(?:endemic|exotic)", texto) else ""
    palavra = "espécie" if len(especies) == 1 else "espécies"
    cabecalho = (f"A documentação do CETRAS apresenta {len(especies)} "
                 f"{palavra} de {grupo}{recorte}.")
    if selecionadas is not None:
        selecionadas.extend(m["nome_cientifico"] for m in especies)
    if contagem and not listagem and not campos:
        return cabecalho + "\n\nCatálogo do CETRAS, páginas consultadas: " + ", ".join(str(p) for p in sorted({m["pagina"] for m in especies}))
    linhas = [cabecalho, ""]
    for numero, metadata in enumerate(especies, 1):
        nome = metadata["nome_animal"]
        cientifico = metadata.get("nome_cientifico", "")
        linhas.append(f"{numero}. {nome}" + (f" ({cientifico})" if cientifico else "") + f" — p. {metadata['pagina']}")
        if campos:
            linhas.extend(responder_campos([metadata], campos, nome).splitlines()[1:])
    return "\n".join(linhas)
