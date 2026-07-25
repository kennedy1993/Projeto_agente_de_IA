"""CLI de teste para conversar com o agente de suporte da BimBam Buy."""
from agente import rag


def main() -> None:
    print("=== Assistente de Suporte BimBam Buy ===")
    print("Digite sua dúvida (ou 'sair' para encerrar)\n")

    historico: list[dict] = []
    while True:
        pergunta = input("Você: ").strip()
        if not pergunta:
            continue
        if pergunta.lower() in {"sair", "exit", "quit"}:
            print("Até logo!")
            break

        resposta, fontes = rag.ask(pergunta, historico)
        print(f"\nAgente: {resposta}\n")

        historico.append({"role": "user", "content": pergunta})
        historico.append({"role": "assistant", "content": resposta})
        historico = historico[-6:]

        if fontes:
            fontes_unicas = sorted({f["source"] for f in fontes})
            print(f"(fontes: {', '.join(fontes_unicas)})\n")


if __name__ == "__main__":
    main()
