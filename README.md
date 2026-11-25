# Chat Mew — Fauna pernambucana

Chatbot local com Streamlit, Chroma e Ollama. Os PDFs e `fauna_pee.json`
podem ficar na raiz do projeto ou em `base/`. Quando houver um arquivo
com o mesmo nome nos dois locais, a cópia de `base/` tem prioridade.

## Testar o catálogo sem Ollama

No PowerShell, dentro da pasta do projeto:

```powershell
py -m pip install streamlit pypdf
$env:MEW_MODO = "catalogo"
py -m streamlit run interface.py
```

O catálogo lê as fichas diretamente dos PDFs e do JSON. Não precisa executar banco.py. Para voltar à geração de respostas com Ollama, abra um novo PowerShell e siga abaixo.

## Executar com Ollama

Com Python e Ollama instalados e o serviço Ollama em execução:

```powershell
python -m pip install -r requeriments.txt
ollama pull embeddinggemma
ollama pull qwen2.5:3b
python banco.py
streamlit run interface.py
```

Após esta atualização, **execute novamente `python banco.py` e reinicie
o Streamlit**. A versão anterior da base não contém os campos necessários.
O comando recria o índice local a partir dos arquivos de origem.
Repita esse processo quando alterar os PDFs ou o JSON.

## Conferir a entrega

Na tela inicial, confira o modo exibido sob o título. Escolha a sugestão
sobre os mamíferos do CETRAS. Devem aparecer cinco espécies com as páginas.
Continue na mesma conversa com “Quais deles vivem na Caatinga?” e depois
“Quais desses vivem na Mata Atlântica?”. Ambas devem listar quatro espécies.

Teste “Compare Pikachu com um animal”. A resposta deve informar que falta
o par no cadastro e mostrar os Pokémon disponíveis. No modo com Ollama,
use a sugestão sobre a atividade dos alunos e abra “Conferir trechos
consultados” para verificar as passagens e páginas enviadas ao modelo.

## Consultas aos documentos

- Listagens e contagens consultam todas as fichas do CETRAS e eliminam
  duplicatas por nome científico. Não dependem dos primeiros resultados
  da busca semântica nem de uma lista produzida pelo modelo.
- O catálogo atual contém 46 espécies, incluindo cinco mamíferos.
- Habitat, alimentação, tamanho e outros campos reconhecidos são
  respondidos separadamente. Dois campos aparecem juntos quando a pergunta
  pede os dois. Se o campo estiver ausente, a resposta informa isso.
- Nas fichas deste PDF, os biomas são apresentados como biomas; não são
  descritos como uma caracterização detalhada do habitat.
- Uma pergunta que cita explicitamente PDF/CETRAS usa os registros do PDF.
  Perguntas gerais sobre um animal também podem consultar o JSON.
- Artigos são divididos em trechos; as fichas de espécies são preservadas
  inteiras. Os artigos são lidos até a última página.
- Perguntas abertas continuam usando recuperação de contexto e geração
  pelo Ollama. Consultas a um grupo recuperam todas as fichas candidatas.
  Se o contexto completo exceder o limite, o chatbot solicita um recorte
  em vez de responder com uma amostra silenciosa.

## Verificar as regressões

```powershell
python -m unittest discover -s tests -v
```

Os testes extraem os PDFs reais e verificam o catálogo e as respostas
específicas sem exigir um serviço Ollama ou banco Chroma. O adaptador de
documento é substituído nos testes; a geração do modelo não é testada.
