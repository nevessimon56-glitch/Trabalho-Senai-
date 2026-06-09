def ler_nota(mensagem):
    return float(input(mensagem).replace(",", "."))


def main():
    nota1 = ler_nota("Digite a nota da primeira disciplina: ")
    nota2 = ler_nota("Digite a nota da segunda disciplina: ")
    nota3 = ler_nota("Digite a nota da terceira disciplina: ")
    nota4 = ler_nota("Digite a nota da quarta disciplina: ")

    media = (nota1 + nota2 + nota3 + nota4) / 4

    print(f"Media final: {media:.2f}")

    if media >= 7.0:
        print("Aluno aprovado.")
    else:
        print("Aluno reprovado.")


if __name__ == "__main__":
    main()
