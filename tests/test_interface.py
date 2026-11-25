import os
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


@unittest.skipIf(AppTest is None, "Teste de interface requer Streamlit")
class ConversaInterfaceTest(unittest.TestCase):
    @patch.dict(os.environ, {"MEW_MODO": "catalogo"})
    def test_conversa_com_fontes_e_filtros(self):
        caminho = Path(__file__).resolve().parents[1] / "interface.py"
        app = AppTest.from_file(str(caminho), default_timeout=90).run()
        self.assertFalse(app.exception)
        app.button(key="sugestao_1").click().run()
        self.assertIn("Semelhança visual", app.chat_message[-1].markdown[-1].value)
        app.button(key="sugestao_0").click().run()
        self.assertEqual(len(app.chat_message), 4)
        self.assertIn("5 espécies", app.chat_message[-1].markdown[-1].value)
        for pergunta, esperado in (
            ("Quais deles vivem na Caatinga?", "4 espécies"),
            ("Quais desses vivem na Mata Atlântica?", "4 espécies"),
            ("Compare Pikachu com um animal", "Não encontrei par"),
            ("Qual o habitat do ouriço-cacheiro?", "Catálogo do CETRAS, p. 64"),
            ("O que o tamanduá-bandeira come?", "fauna_pee.json"),
        ):
            with self.subTest(pergunta=pergunta):
                app.chat_input[0].set_value(pergunta).run()
                self.assertFalse(app.exception)
                self.assertIn(esperado, app.chat_message[-1].markdown[-1].value)
