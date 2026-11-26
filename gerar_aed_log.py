import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="darkgrid")
plt.rcParams.update({"font.size": 10})


def analisar_logs():
    print("⏳ Lendo logs de interação...")

    if not os.path.exists("logs_interacao.jsonl"):
        print("❌ ERRO: Arquivo 'logs_interacao.jsonl' não encontrado.")
        print("👉 Dica: Rode o 'streamlit run interface.py', faça algumas perguntas no chat e tente novamente.")
        return

    # Lendo o arquivo JSON Lines
    df = pd.read_json("logs_interacao.jsonl", lines=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["id_interacao"] = range(1, len(df) + 1)

    # Classifica a rota pelo tempo de resposta (< 1s = catálogo/regras; >= 1s = Ollama LLM)
    df["rota"] = df["latencia_segundos"].apply(
        lambda t: "Geração via Ollama (LLM)" if t >= 1.0 else "Catálogo / Regras (Python)"
    )

    # --- RESUMO ESTATÍSTICO GERAL ---
    print("\n" + "=" * 55)
    print("⚡ RESUMO DE DESEMPENHO DO CHATBOT (PROJETO MEW)")
    print("=" * 55)
    print(f"Total de interações avaliadas: {len(df)}")
    print(f"Latência Média   : {df['latencia_segundos'].mean():.3f} segundos")
    print(f"Latência Mediana : {df['latencia_segundos'].median():.3f} segundos")
    print(f"Latência Máxima  : {df['latencia_segundos'].max():.3f} segundos")
    print(f"Latência Mínima  : {df['latencia_segundos'].min():.3f} segundos")
    print(f"Tamanho Médio da Resposta: {int(df['tamanho_resposta'].mean())} caracteres")
    print("-" * 55)
    print("Desempenho por Rota de Processamento:")
    resumo_rotas = (
        df.groupby("rota")["latencia_segundos"]
        .agg(quantidade="count", media="mean", mediana="median", minimo="min", maximo="max")
        .round(3)
    )
    print(resumo_rotas)
    print("=" * 55 + "\n")

    # --- GERANDO OS GRÁFICOS ---
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    fig.suptitle("AED: Desempenho e Tempo de Resposta (Chat Mew)", fontsize=16, fontweight="bold")

    # Gráfico 1: Linha do Tempo de Latência (evidencia o warm-up inicial)
    axes[0].plot(
        df["id_interacao"],
        df["latencia_segundos"],
        marker="o",
        linestyle="-",
        color="#00e0ff",
        linewidth=2,
        label="Latência por pergunta"
    )
    axes[0].axhline(
        df["latencia_segundos"].mean(),
        color="#dc0a2d",
        linestyle="--",
        label=f"Média Geral ({df['latencia_segundos'].mean():.2f}s)"
    )
    axes[0].set_title("Tempo de Resposta por Ordem de Interação")
    axes[0].set_xlabel("Número da Pergunta")
    axes[0].set_ylabel("Latência (segundos)")
    axes[0].legend()

    # Gráfico 2: Relação entre Tamanho da Resposta e Tempo por Rota
    paleta_rotas = {
        "Geração via Ollama (LLM)": "#3fb950",
        "Catálogo / Regras (Python)": "#f49f0a"
    }
    sns.scatterplot(
        data=df,
        x="tamanho_resposta",
        y="latencia_segundos",
        hue="rota",
        palette=paleta_rotas,
        ax=axes[1],
        s=110,
        alpha=0.85
    )
    axes[1].set_title("Tamanho da Resposta vs Tempo de Geração")
    axes[1].set_xlabel("Tamanho da Resposta (caracteres)")
    axes[1].set_ylabel("Latência (segundos)")
    axes[1].legend(title="Rota")

    plt.tight_layout()
    plt.savefig("aed_logs_desempenho.png", dpi=300, bbox_inches="tight")
    print("✅ Gráfico salvo com sucesso: aed_logs_desempenho.png")


if __name__ == "__main__":
    analisar_logs()