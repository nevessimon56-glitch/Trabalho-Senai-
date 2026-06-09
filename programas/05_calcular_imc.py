def ler_numero(mensagem):
    return float(input(mensagem).replace(",", "."))


def main():
    altura = ler_numero("Digite sua altura em metros: ")
    peso = ler_numero("Digite seu peso em kg: ")

    if altura <= 0:
        print("A altura deve ser maior que zero.")
        return

    imc = peso / (altura * altura)

    print(f"Seu IMC e: {imc:.2f}")


if __name__ == "__main__":
    main()
