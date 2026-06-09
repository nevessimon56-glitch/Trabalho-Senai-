from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText
except ModuleNotFoundError as erro:
    tk = None
    filedialog = None
    messagebox = None
    ttk = None
    ScrolledText = None
    TKINTER_IMPORT_ERROR = erro
else:
    TKINTER_IMPORT_ERROR = None


def ler_decimal(valor, campo):
    texto = valor.strip().replace(",", ".")
    if not texto:
        raise ValueError(f"Preencha o campo {campo}.")
    return float(texto)


def ler_inteiro(valor, campo):
    texto = valor.strip()
    if not texto:
        raise ValueError(f"Preencha o campo {campo}.")
    return int(texto)


def formatar_numero(valor):
    if valor == int(valor):
        return str(int(valor))
    return f"{valor:.2f}"


class ExerciciosApp(tk.Tk if tk is not None else object):
    def __init__(self):
        if TKINTER_IMPORT_ERROR is not None:
            raise RuntimeError(
                "Tkinter nao esta instalado. No Windows, reinstale o Python marcando a opcao tcl/tk. "
                "No Linux, instale o pacote python3-tk."
            ) from TKINTER_IMPORT_ERROR

        super().__init__()
        self.title("Trabalho Senai - Exercicios em Python")
        self.geometry("820x620")
        self.minsize(720, 520)

        self.configure(bg="#edf2f7")
        self._configurar_estilo()
        self._montar_interface()

    def _configurar_estilo(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure("TFrame", background="#edf2f7")
        estilo.configure("Card.TFrame", background="#ffffff", relief="flat")
        estilo.configure("TLabel", background="#ffffff", foreground="#1a202c", font=("Arial", 11))
        estilo.configure("Title.TLabel", background="#edf2f7", foreground="#1a202c", font=("Arial", 18, "bold"))
        estilo.configure("Subtitle.TLabel", background="#edf2f7", foreground="#4a5568", font=("Arial", 11))
        estilo.configure("Result.TLabel", background="#ffffff", foreground="#2b6cb0", font=("Arial", 12, "bold"))
        estilo.configure("TButton", font=("Arial", 10, "bold"), padding=8)
        estilo.configure("TNotebook", background="#edf2f7", borderwidth=0)
        estilo.configure("TNotebook.Tab", font=("Arial", 10), padding=(12, 8))

    def _montar_interface(self):
        cabecalho = ttk.Frame(self)
        cabecalho.pack(fill="x", padx=24, pady=(20, 10))

        ttk.Label(cabecalho, text="Trabalho Senai", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            cabecalho,
            text="Aplicativo com telas para os exercicios de Python.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        abas = ttk.Notebook(self)
        abas.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        abas.add(self._tela_nome_idade(abas), text="Nome e idade")
        abas.add(self._tela_operacoes(abas), text="Operacoes")
        abas.add(self._tela_arquivo(abas), text="Arquivo")
        abas.add(self._tela_imc(abas), text="IMC")
        abas.add(self._tela_tabuada(abas), text="Tabuada")
        abas.add(self._tela_media(abas), text="Media")

    def _criar_cartao(self, pai):
        cartao = ttk.Frame(pai, style="Card.TFrame", padding=24)
        cartao.pack(fill="both", expand=True, padx=8, pady=8)
        return cartao

    def _criar_campo(self, pai, texto, largura=30):
        ttk.Label(pai, text=texto).pack(anchor="w", pady=(0, 4))
        entrada = ttk.Entry(pai, width=largura, font=("Arial", 11))
        entrada.pack(fill="x", pady=(0, 12))
        return entrada

    def _mostrar_erro(self, erro):
        messagebox.showerror("Erro", str(erro))

    def _tela_nome_idade(self, pai):
        tela = ttk.Frame(pai)
        cartao = self._criar_cartao(tela)

        ttk.Label(cartao, text="Mensagem personalizada", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 16))
        nome = self._criar_campo(cartao, "Nome:")
        idade = self._criar_campo(cartao, "Idade:")
        resultado = ttk.Label(cartao, text="", style="Result.TLabel")
        resultado.pack(anchor="w", pady=(8, 0))

        def calcular():
            try:
                nome_usuario = nome.get().strip()
                idade_usuario = ler_inteiro(idade.get(), "idade")
                if not nome_usuario:
                    raise ValueError("Preencha o campo nome.")
                resultado.config(
                    text=f"Ola, {nome_usuario}! Voce tem {idade_usuario} anos. Seja bem-vindo(a)!"
                )
            except ValueError as erro:
                self._mostrar_erro(erro)

        ttk.Button(cartao, text="Mostrar mensagem", command=calcular).pack(anchor="w")
        return tela

    def _tela_operacoes(self, pai):
        tela = ttk.Frame(pai)
        cartao = self._criar_cartao(tela)

        ttk.Label(cartao, text="Operacoes basicas", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 16))
        numero1 = self._criar_campo(cartao, "Primeiro numero:")
        numero2 = self._criar_campo(cartao, "Segundo numero:")
        resultado = ttk.Label(cartao, text="", style="Result.TLabel", justify="left")
        resultado.pack(anchor="w", pady=(8, 0))

        def calcular():
            try:
                valor1 = ler_decimal(numero1.get(), "primeiro numero")
                valor2 = ler_decimal(numero2.get(), "segundo numero")

                linhas = [
                    f"Soma: {formatar_numero(valor1 + valor2)}",
                    f"Subtracao: {formatar_numero(valor1 - valor2)}",
                    f"Multiplicacao: {formatar_numero(valor1 * valor2)}",
                ]

                if valor2 == 0:
                    linhas.append("Divisao: nao e possivel dividir por zero.")
                else:
                    linhas.append(f"Divisao: {formatar_numero(valor1 / valor2)}")

                resultado.config(text="\n".join(linhas))
            except ValueError as erro:
                self._mostrar_erro(erro)

        ttk.Button(cartao, text="Calcular", command=calcular).pack(anchor="w")
        return tela

    def _tela_arquivo(self, pai):
        tela = ttk.Frame(pai)
        cartao = self._criar_cartao(tela)

        ttk.Label(cartao, text="Ler conteudo de arquivo", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 16))
        caminho = self._criar_campo(cartao, "Nome ou caminho do arquivo:", largura=50)

        botoes = ttk.Frame(cartao, style="Card.TFrame")
        botoes.pack(fill="x", pady=(0, 12))

        conteudo = ScrolledText(cartao, height=15, wrap="word", font=("Consolas", 10))
        conteudo.pack(fill="both", expand=True)

        def escolher_arquivo():
            arquivo = filedialog.askopenfilename(title="Escolha um arquivo")
            if arquivo:
                caminho.delete(0, tk.END)
                caminho.insert(0, arquivo)

        def ler_arquivo():
            nome_arquivo = caminho.get().strip()
            if not nome_arquivo:
                self._mostrar_erro("Digite ou escolha um arquivo.")
                return

            arquivo = Path(nome_arquivo)
            if not arquivo.is_absolute():
                arquivo = Path.cwd() / arquivo

            try:
                texto = arquivo.read_text(encoding="utf-8")
            except FileNotFoundError:
                self._mostrar_erro("Arquivo nao encontrado.")
                return
            except PermissionError:
                self._mostrar_erro("Sem permissao para ler o arquivo.")
                return
            except UnicodeDecodeError:
                self._mostrar_erro("Nao foi possivel ler o arquivo como texto UTF-8.")
                return

            conteudo.delete("1.0", tk.END)
            conteudo.insert(tk.END, texto)

        ttk.Button(botoes, text="Escolher arquivo", command=escolher_arquivo).pack(side="left", padx=(0, 8))
        ttk.Button(botoes, text="Ler arquivo", command=ler_arquivo).pack(side="left")
        return tela

    def _tela_imc(self, pai):
        tela = ttk.Frame(pai)
        cartao = self._criar_cartao(tela)

        ttk.Label(cartao, text="Calculo de IMC", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 16))
        altura = self._criar_campo(cartao, "Altura em metros:")
        peso = self._criar_campo(cartao, "Peso em kg:")
        resultado = ttk.Label(cartao, text="", style="Result.TLabel")
        resultado.pack(anchor="w", pady=(8, 0))

        def calcular():
            try:
                altura_usuario = ler_decimal(altura.get(), "altura")
                peso_usuario = ler_decimal(peso.get(), "peso")

                if altura_usuario <= 0:
                    raise ValueError("A altura deve ser maior que zero.")

                imc = peso_usuario / (altura_usuario * altura_usuario)
                resultado.config(text=f"Seu IMC e: {imc:.2f}")
            except ValueError as erro:
                self._mostrar_erro(erro)

        ttk.Button(cartao, text="Calcular IMC", command=calcular).pack(anchor="w")
        return tela

    def _tela_tabuada(self, pai):
        tela = ttk.Frame(pai)
        cartao = self._criar_cartao(tela)

        ttk.Label(cartao, text="Tabuada completa", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 16))
        numero = self._criar_campo(cartao, "Numero inteiro:")
        resultado = ttk.Label(cartao, text="", style="Result.TLabel", justify="left")
        resultado.pack(anchor="w", pady=(8, 0))

        def calcular():
            try:
                valor = ler_inteiro(numero.get(), "numero inteiro")
                linhas = [f"Tabuada do {valor}:"]
                for multiplicador in range(1, 11):
                    linhas.append(f"{valor} x {multiplicador} = {valor * multiplicador}")
                resultado.config(text="\n".join(linhas))
            except ValueError as erro:
                self._mostrar_erro(erro)

        ttk.Button(cartao, text="Gerar tabuada", command=calcular).pack(anchor="w")
        return tela

    def _tela_media(self, pai):
        tela = ttk.Frame(pai)
        cartao = self._criar_cartao(tela)

        ttk.Label(cartao, text="Media final do aluno", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 16))
        nota1 = self._criar_campo(cartao, "Nota da primeira disciplina:")
        nota2 = self._criar_campo(cartao, "Nota da segunda disciplina:")
        nota3 = self._criar_campo(cartao, "Nota da terceira disciplina:")
        nota4 = self._criar_campo(cartao, "Nota da quarta disciplina:")
        resultado = ttk.Label(cartao, text="", style="Result.TLabel")
        resultado.pack(anchor="w", pady=(8, 0))

        def calcular():
            try:
                notas = [
                    ler_decimal(nota1.get(), "primeira nota"),
                    ler_decimal(nota2.get(), "segunda nota"),
                    ler_decimal(nota3.get(), "terceira nota"),
                    ler_decimal(nota4.get(), "quarta nota"),
                ]

                media = sum(notas) / len(notas)
                situacao = "Aluno aprovado." if media >= 7.0 else "Aluno reprovado."
                resultado.config(text=f"Media final: {media:.2f}\n{situacao}")
            except ValueError as erro:
                self._mostrar_erro(erro)

        ttk.Button(cartao, text="Calcular media", command=calcular).pack(anchor="w")
        return tela


def main():
    if TKINTER_IMPORT_ERROR is not None:
        raise SystemExit(
            "Tkinter nao esta instalado. No Windows, reinstale o Python marcando a opcao tcl/tk. "
            "No Linux, instale o pacote python3-tk."
        ) from TKINTER_IMPORT_ERROR

    app = ExerciciosApp()
    app.mainloop()


if __name__ == "__main__":
    main()
