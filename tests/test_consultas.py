"""Regressões com os PDFs reais, sem precisar de Ollama ou de um banco vetorial.

O adaptador Document é substituído somente durante a leitura dos arquivos.
A extração pypdf, os parsers, os metadados e o roteamento são os de produção.
"""

import contextlib
import io
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import carrega_base
import main
from consultas import consultar_catalogo, especies_unicas, identificar_campos


@dataclass
class DocumentoTeste:
    page_content: str
    metadata: dict


class ConsultasPDFTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        adapter = types.ModuleType("langchain_core.documents")
        adapter.Document = DocumentoTeste
        with patch.dict(sys.modules, {"langchain_core.documents": adapter}):
            with contextlib.redirect_stdout(io.StringIO()):
                cls.pdfs = carrega_base.carregar_pdf()
                cls.animais_json = carrega_base.carregar_json()
        cls.metadados = [d.metadata for d in cls.pdfs + cls.animais_json]

    def setUp(self):
        # Nenhuma consulta determinística deve chamar embeddings ou geração.
        self.patches = [
            patch.object(main, "db", object()),
            patch.object(main, "metadados", self.metadados),
            patch.object(main, "indice_animais", main.criar_indice_animais(self.metadados)),
            patch.object(main, "obter_modelo", side_effect=AssertionError("LLM não necessário")),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_cinco_fichas_reais_de_mamiferos(self):
        especies = especies_unicas(self.metadados, ["Mamíferos"])
        self.assertEqual({m["nome_cientifico"] for m in especies}, {
            "Bradypus variegatus", "Callithrix jacchus", "Didelphis albiventris",
            "Coendou prehensilis", "Nasua nasua",
        })

    def test_todas_as_fichas_tem_identidade_e_campos(self):
        especies = especies_unicas(self.metadados)
        self.assertEqual(len(especies), 46)
        self.assertTrue(all(m["nome_cientifico"] and m["campos"] for m in especies))

    def test_artigos_sem_corte_arbitrario_de_paginas(self):
        from pypdf import PdfReader
        for caminho in carrega_base.arquivos_base("pdf"):
            if "cetras" not in caminho.name:
                with self.subTest(arquivo=caminho.name):
                    paginas = [d.metadata["pagina"] for d in self.pdfs
                               if Path(d.metadata["origem"]).name == caminho.name]
                    self.assertEqual(max(paginas), len(PdfReader(caminho).pages))

    def test_listagem_completa_com_diferentes_formulacoes(self):
        for pergunta in (
            "Quais os mamíferos encontrados no CETRAS de Pernambuco?",
            "Quais são os mamíferos que vivem no CETRAS de Pernambuco?",
            "Liste todos os mamíferos do PDF",
            "Mostre os mamíferos presentes no CETRAS",
            "Quais mamíferos aparecem no catálogo do CETRAS?",
        ):
            with self.subTest(pergunta=pergunta):
                resposta = main.perguntar(pergunta, "Quati")
                self.assertIn("5 espécies", resposta)
                for especie in especies_unicas(self.metadados, ["Mamíferos"]):
                    self.assertIn(especie["nome_cientifico"], resposta)
                self.assertNotIn("Trichechus", resposta)

    def test_contagem_sem_llm(self):
        self.assertIn("5 espécies", main.perguntar("Quantos mamíferos há no CETRAS?"))

    def test_listagem_de_todos_os_animais_nao_limitada_a_cinco_documentos(self):
        resposta = main.perguntar("Quais são todos os animais do CETRAS?")
        self.assertIn("46 espécies", resposta)
        for especie in especies_unicas(self.metadados):
            self.assertIn(especie["nome_cientifico"], resposta)

    def test_chunks_duplicados_nao_inflam_contagem(self):
        resposta = consultar_catalogo("Quantos mamíferos?", self.metadados * 3, ["Mamíferos"])
        self.assertIn("5 espécies", resposta)

    def test_habitat_pdf_so_contem_biomas(self):
        resposta = main.perguntar("Qual o habitat do quati no PDF?")
        self.assertIn("Biomas registrados no PDF", resposta)
        self.assertIn("Caatinga", resposta)
        for trecho in ("Alimentação", "Tamanho", "52,5", "LC", "conservação"):
            self.assertNotIn(trecho, resposta)

    def test_sinonimo_de_habitat(self):
        for pergunta in ("Onde vive o quati?", "Onde o quati vive?"):
            resposta = main.perguntar(pergunta)
            self.assertIn("Biomas registrados no PDF", resposta)
            self.assertNotIn("conservação", resposta)

    def test_habitat_json_sem_alimentacao(self):
        resposta = main.perguntar("Qual o habitat do tamanduá-bandeira?")
        self.assertIn("savanas", resposta)
        self.assertNotIn("formigas", resposta)
        self.assertNotIn("cupins", resposta)

    def test_alimentacao_json_sem_habitat(self):
        resposta = main.perguntar("O que o tamanduá-bandeira come?")
        self.assertIn("formigas", resposta)
        self.assertNotIn("savanas", resposta)
        self.assertNotIn("Habitat:", resposta)

    def test_dois_campos_somente_quando_solicitados(self):
        resposta = main.perguntar("Qual o habitat e a alimentação do tamanduá-bandeira?")
        self.assertIn("savanas", resposta)
        self.assertIn("formigas", resposta)
        self.assertNotIn("Tamanho", resposta)

    def test_nao_inventa_campo_ausente_no_pdf(self):
        resposta = main.perguntar("Qual a alimentação do quati no PDF?")
        self.assertIn("Alimentação: informação não encontrada", resposta)
        self.assertNotIn("Biomas", resposta)

    def test_pdf_explicito_nao_usa_json(self):
        resposta = main.perguntar("Qual o habitat do tamanduá-bandeira no PDF do CETRAS?")
        self.assertIn("informação não encontrada", resposta)
        self.assertNotIn("savanas", resposta)

    def test_continuacao_respeita_campo(self):
        resposta = main.perguntar("E a alimentação dele?", "Quati")
        self.assertIn("Alimentação: informação não encontrada", resposta)
        self.assertNotIn("Biomas", resposta)

    def test_habitat_de_grupo_inclui_todas_as_especies(self):
        resposta = main.perguntar("Qual o habitat dos mamíferos do CETRAS?")
        self.assertEqual(resposta.count("Biomas registrados no PDF:"), 5)
        self.assertNotIn("Alimentação", resposta)

    def test_filtro_caatinga_consulta_todas_as_fichas(self):
        resposta = main.perguntar("Quais mamíferos vivem na Caatinga segundo o CETRAS?")
        self.assertIn("4 espécies", resposta)
        self.assertIn("Quati", resposta)
        self.assertNotIn("Coendou prehensilis", resposta)

    def test_filtro_endemismo(self):
        resposta = main.perguntar("Quais mamíferos são endêmicos no PDF?")
        self.assertIn("1 espécie", resposta)
        self.assertIn("Callithrix jacchus", resposta)
        self.assertNotIn("Nasua nasua", resposta)

    def test_negacao_de_campo(self):
        self.assertEqual(identificar_campos("habitat, sem alimentação"), ["Habitat"])

    def test_predicados_desconhecidos_nao_viram_listagem_sem_filtro(self):
        resposta = consultar_catalogo("Quais mamíferos possuem cauda longa?",
                                     self.metadados, ["Mamíferos"])
        self.assertIsNone(resposta)

    def test_lista_de_dois_grupos(self):
        resposta = main.perguntar("Quais aves e mamíferos são encontrados no CETRAS?")
        self.assertIn("39 espécies", resposta)
        self.assertIn("Nasua nasua", resposta)
        self.assertIn("Tyto furcata", resposta)

    def test_conservacao_agrupada_preserva_aviso_do_pdf(self):
        resposta = main.perguntar("Qual o status de conservação do quati no PDF?")
        self.assertIn("LC (Pouco preocupante)", resposta)
        self.assertIn("não foi confirmada", resposta)
        self.assertNotIn("Biomas", resposta)

    def test_peso_json_sem_outros_campos(self):
        resposta = main.perguntar("Qual o peso do tamanduá-bandeira?")
        self.assertIn("45 kg", resposta)
        self.assertNotIn("formigas", resposta)
        self.assertNotIn("Habitat", resposta)

    def test_pergunta_vazia(self):
        self.assertEqual(main.perguntar(" "), "Digite uma pergunta válida.")

    def test_comparacao_de_dois_pokemon_com_fichas(self):
        pergunta = "Compare 2 pokemon com as especie disponivel"
        self.assertIsNone(main.identificar_animal(pergunta)[1])
        resultado = main.perguntar(pergunta)
        self.assertEqual(resultado.count("Semelhança visual:"), 2)
        self.assertEqual(resultado.count("Diferença:"), 2)
        self.assertIn("fauna_pee.json", resultado)
        self.assertNotIn("Elusor", resultado)
        resultado = main.perguntar("Compare dois Pokémon, Sandshrew e Heatmor, com as espécies reais")
        self.assertIn("Sandshrew e Tatu-bola-do-nordeste", resultado)
        self.assertIn("Heatmor e Tamanduá-bandeira", resultado)


if __name__ == "__main__":
    unittest.main()
