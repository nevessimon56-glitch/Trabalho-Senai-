def main():
    nome_arquivo = input("Digite o nome do arquivo: ").strip()

    try:
        with open(nome_arquivo, "r", encoding="utf-8") as arquivo:
            conteudo = arquivo.read()
    except FileNotFoundError:
        print("Arquivo nao encontrado.")
        return
    except PermissionError:
        print("Sem permissao para ler o arquivo.")
        return

    print("Conteudo do arquivo:")
    print(conteudo)


if __name__ == "__main__":
    main()
