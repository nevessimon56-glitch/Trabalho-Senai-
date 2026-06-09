def ler_numero(mensagem):
    return float(input(mensagem).replace(",", "."))


def main():
    numero1 = ler_numero("Digite o primeiro numero: ")
    numero2 = ler_numero("Digite o segundo numero: ")

    print(f"Soma: {numero1 + numero2}")
    print(f"Subtracao: {numero1 - numero2}")
    print(f"Multiplicacao: {numero1 * numero2}")

    if numero2 == 0:
        print("Divisao: nao e possivel dividir por zero.")
    else:
        print(f"Divisao: {numero1 / numero2}")


if __name__ == "__main__":
    main()
