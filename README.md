# Trabalho-Senai-

Programas em Python para praticar entrada de dados, operacoes matematicas,
leitura de arquivos e estruturas de repeticao.

## Como executar

Para abrir o aplicativo com telas:

```bash
python3 app.py
```

No Windows, se o comando `python3` nao funcionar, use:

```powershell
python app.py
```

O aplicativo usa Tkinter, que normalmente ja vem junto com o Python no Windows.
Se aparecer erro dizendo que `tkinter` nao foi encontrado, reinstale o Python
marcando a opcao de instalar `tcl/tk`.

Use Python 3 para executar cada programa individualmente:

```bash
python3 programas/01_nome_idade.py
```

Para executar todos os programas de uma vez com exemplos prontos:

```bash
python3 executar_todos.py
```

No Windows, se o comando `python3` nao funcionar, use:

```powershell
python executar_todos.py
```

Se voce ainda nao tem a pasta do projeto no computador, baixe a branch com:

```powershell
git clone -b cursor/programas-basicos-1030 https://github.com/nevessimon56-glitch/Trabalho-Senai-.git
cd Trabalho-Senai-
python app.py
```

## Como transformar em executavel no Windows

Instale o PyInstaller:

```powershell
pip install pyinstaller
```

Depois gere o executavel:

```powershell
pyinstaller --onefile --windowed app.py
```

O arquivo final ficara dentro da pasta `dist`.

## Aplicativo

O arquivo `app.py` abre uma janela com abas para:

- Nome e idade
- Operacoes basicas
- Leitura de arquivo
- Calculo de IMC
- Tabuada
- Media do aluno

## Programas

1. `programas/01_nome_idade.py`: pede nome e idade e mostra uma mensagem personalizada.
2. `programas/02_operacoes_dois_numeros.py`: pede dois numeros e calcula soma, subtracao, multiplicacao e divisao.
3. `programas/03_imprimir_arquivo.py`: pede o nome de um arquivo e imprime seu conteudo.
4. `programas/04_calculadora_basica.py`: pede dois numeros e apresenta as quatro operacoes basicas.
5. `programas/05_calcular_imc.py`: pede altura e peso e calcula o IMC.
6. `programas/06_tabuada.py`: pede um numero inteiro e imprime a tabuada de 1 a 10.
7. `programas/07_media_aluno.py`: pede quatro notas, calcula a media e informa se o aluno foi aprovado ou reprovado.
