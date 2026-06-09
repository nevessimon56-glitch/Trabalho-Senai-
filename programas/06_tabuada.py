def main():
    numero = int(input("Digite um numero inteiro: "))

    print(f"Tabuada do {numero}:")
    for multiplicador in range(1, 11):
        resultado = numero * multiplicador
        print(f"{numero} x {multiplicador} = {resultado}")


if __name__ == "__main__":
    main()
