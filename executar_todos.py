import subprocess
import sys
from pathlib import Path


PROGRAMAS = [
    ("1. Nome e idade", "programas/01_nome_idade.py", "Ana\n18\n"),
    ("2. Operacoes com dois numeros", "programas/02_operacoes_dois_numeros.py", "10\n2\n"),
    ("3. Imprimir arquivo", "programas/03_imprimir_arquivo.py", "README.md\n"),
    ("4. Calculadora basica", "programas/04_calculadora_basica.py", "8\n4\n"),
    ("5. Calcular IMC", "programas/05_calcular_imc.py", "1,70\n70\n"),
    ("6. Tabuada", "programas/06_tabuada.py", "7\n"),
    ("7. Media do aluno", "programas/07_media_aluno.py", "8\n7\n6\n9\n"),
]


def executar_programa(titulo, caminho, entradas):
    print("=" * 60)
    print(titulo)
    print("=" * 60)

    resultado = subprocess.run(
        [sys.executable, caminho],
        input=entradas,
        text=True,
        capture_output=True,
        cwd=Path(__file__).parent,
        check=False,
    )

    print(resultado.stdout)

    if resultado.stderr:
        print("Erros:")
        print(resultado.stderr)

    if resultado.returncode != 0:
        print(f"O programa terminou com codigo {resultado.returncode}.")


def main():
    for titulo, caminho, entradas in PROGRAMAS:
        executar_programa(titulo, caminho, entradas)


if __name__ == "__main__":
    main()
