import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuração visual dos gráficos
sns.set_theme(style="darkgrid")
plt.rcParams.update({'font.size': 10})

def analisar_base():
    print("⏳ Carregando e processando a base de dados (fauna_pee.json)...")
    
    # Tenta encontrar o arquivo na raiz ou na pasta 'base'
    caminhos_possiveis = ["fauna_pee.json", "base/fauna_pee.json", "fauna-pee.json", "base/fauna-pee.json"]
    caminho_json = next((c for c in caminhos_possiveis if os.path.exists(c)), None)
    
    if not caminho_json:
        print("❌ ERRO: Arquivo fauna_pee.json não encontrado.")
        return

    with open(caminho_json, "r", encoding="utf-8") as f:
        dados = json.load(f)

    animais = dados.get("especies_ameacadas", [])
    
    # Criando um DataFrame
    dados_tabela = []
    for a in animais:
        dados_tabela.append({
            "Nome Popular": a.get("nome_popular", ""),
            "Nome Científico": a.get("nome_cientifico", ""),
            "Classe": a.get("classe", "Desconhecida"),
            "Status de Conservação": a.get("situacao", "Não informado"),
            "Pokémon Semelhante": a.get("pokemon_semelhante", {}).get("nome", "Nenhum"),
            "Geração do Pokémon": a.get("pokemon_semelhante", {}).get("geracao", 0)
        })
        
    df = pd.DataFrame(dados_tabela)

    # Limpando nomes de status para agrupar melhor
    df['Status de Conservação'] = df['Status de Conservação'].str.replace(' de extinção', '', regex=False)
    df['Status de Conservação'] = df['Status de Conservação'].str.capitalize()

    # --- RESUMO ESTATÍSTICO ---
    print("\n" + "="*50)
    print("📊 RESUMO DA BASE DE CONHECIMENTO")
    print("="*50)
    print(f"Total de Espécies catalogadas: {len(df)}")
    print(f"Total de Pokémon usados nas comparações: {df['Pokémon Semelhante'].nunique()}")
    print("\nDistribuição por Classe:")
    print(df["Classe"].value_counts().to_string())
    print("="*50 + "\n")

    # --- GERANDO OS GRÁFICOS ---
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("AED: Base de Conhecimento da Fauna de Pernambuco", fontsize=16, fontweight="bold")

    # Gráfico 1: Distribuição de Classes (Pizza)
    cores_classes = ['#3fb950', '#00e0ff', '#dc0a2d', '#ffcb05']
    axes[0].pie(df["Classe"].value_counts(), labels=df["Classe"].value_counts().index, 
                autopct="%1.1f%%", colors=cores_classes, startangle=90, wedgeprops={'edgecolor': 'white'})
    axes[0].set_title("Proporção de Animais por Classe")

    # Gráfico 2: Status de Conservação (Barras)
    sns.countplot(data=df, y="Status de Conservação", ax=axes[1], palette="Reds_r")
    axes[1].set_title("Status de Conservação (IUCN/MMA)")
    axes[1].set_xlabel("Quantidade de Espécies")
    axes[1].set_ylabel("")

    # Gráfico 3: Gerações dos Pokémon usados (Barras)
    sns.countplot(data=df, x="Geração do Pokémon", ax=axes[2], palette="Blues")
    axes[2].set_title("Gerações dos Pokémon Utilizados")
    axes[2].set_xlabel("Geração")
    axes[2].set_ylabel("Quantidade de Comparações")

    plt.tight_layout()
    plt.savefig("aed_base_conhecimento.png", dpi=300, bbox_inches='tight')
    print("✅ Gráfico salvo com sucesso: aed_base_conhecimento.png")

if __name__ == "__main__":
    analisar_base()