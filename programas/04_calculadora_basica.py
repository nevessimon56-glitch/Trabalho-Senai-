def ler_numero(mensagem):
    return float(input(mensagem).replace(",", "."))


def main():
    numero1 = ler_numero("Digite o primeiro numero: ")
    numero2 = ler_numero("Digite o segundo numero: ")

    soma = numero1 + numero2
    subtracao = numero1 - numero2
    multiplicacao = numero1 * numero2

    print("Resultados:")
    print(f"{numero1} + {numero2} = {soma}")
    print(f"{numero1} - {numero2} = {subtracao}")
    print(f"{numero1} * {numero2} = {multiplicacao}")

    if numero2 == 0:
        print(f"{numero1} / {numero2} = nao e possivel dividir por zero.")
    else:
        print(f"{numero1} / {numero2} = {numero1 / numero2}")


if __name__ == "__main__":
    main()
