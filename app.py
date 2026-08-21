from collections import Counter
from statistics import mean
import json
import re
import unicodedata
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import pandas as pd
import requests
import spacy
import streamlit as st

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="ReputaAI - Análise de Reputação & Sentimentos",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
        border-radius: 12px;
        padding: 12px 16px;
        border: 1px solid #e2e8f0;
    }
    .sent-positivo { color: #059669; font-weight: 600; }
    .sent-negativo { color: #dc2626; font-weight: 600; }
    .sent-neutro { color: #d97706; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Carregando modelo spaCy (pt)...")
def carregar_modelo_spacy():
    try:
        return spacy.load("pt_core_news_sm")
    except OSError:
        st.error(
            "Modelo spaCy não encontrado. Execute: "
            "`python -m spacy download pt_core_news_sm` ou `pip install -r requirements.txt`"
        )
        st.stop()


nlp = carregar_modelo_spacy()

# ==============================================================================
# LÉXICO E REGRAS DE PLN
# ==============================================================================
def remover_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


LEXICO_PT_BASE = {
    "adoro": 0.7, "agradavel": 0.5, "amei": 0.9, "atencioso": 0.7, "barato": 0.4,
    "boa": 0.5, "bom": 0.5, "confiavel": 0.8, "excelente": 0.9, "facil": 0.4,
    "feliz": 0.7, "gostei": 0.7, "incrivel": 0.8, "maravilhosa": 0.9, "maravilhoso": 0.9,
    "otima": 0.8, "otimo": 0.8, "perfeito": 0.9, "rapida": 0.5, "rapido": 0.5,
    "recomendo": 0.8, "resolvido": 0.6, "satisfeito": 0.8, "seguro": 0.5, "top": 0.7,
    "monstro": 0.7, "show": 0.8, "impecavel": 0.9, "embalado": 0.4, "embalagem": 0.3,
    "abafado": -0.4, "amassada": -0.5, "amassado": -0.5, "atrasada": -0.6, "atrasado": -0.6,
    "caro": -0.4, "defeito": -0.8, "demora": -0.6, "devolucao": -0.4, "enganosa": -0.7,
    "enganoso": -0.7, "fraude": -0.9, "horrivel": -0.9, "insatisfeito": -0.8,
    "inutilizavel": -0.8, "lenta": -0.4, "lento": -0.4, "nao recomendo": -0.9,
    "pessima": -0.8, "pessimo": -0.8, "problema": -0.6, "quebrada": -0.7,
    "quebrado": -0.7, "reclamacao": -0.6, "ruim": -0.6, "terrivel": -0.8, "lixo": -0.9,
    "fragil": -0.5,
}

LEXICO_PT = {remover_acentos(k): v for k, v in LEXICO_PT_BASE.items()}
EXPRESSOES_COMPOSTAS = sorted(
    [(k, v) for k, v in LEXICO_PT.items() if " " in k],
    key=lambda item: len(item[0]),
    reverse=True,
)

NEGACOES = {"nao", "nunca", "jamais", "nem", "sem"}
INTENSIFICADORES = {"muito", "muita", "bem", "super", "totalmente", "extremamente", "demais"}
CONTRASTE = {"mas", "porem", "entretanto", "contudo", "todavia"}

EXEMPLOS = """Entrega super rápida, produto bem embalado e atendimento excelente!
O produto chegou com defeito e a loja não respondeu minha reclamação.
Comprei ontem. Ainda não tive tempo de testar tudo.
O preço é bom, mas o acabamento é bem ruim e frágil.
Não recomendo, tive dor de cabeça com o processo de devolução."""

CORES_SENTIMENTO = {
    "Positivo": "#059669",
    "Neutro": "#d97706",
    "Negativo": "#dc2626",
}

# ==============================================================================
# PIPELINE DE PROCESSAMENTO
# ==============================================================================
def tokenizar_para_lexico(texto: str) -> list[str]:
    """Usa a forma superficial (sem acento) — o léxico está em flexões, não lemas."""
    doc = nlp(texto.lower())
    return [
        remover_acentos(token.text.lower())
        for token in doc
        if not token.is_space and not token.is_punct
    ]


def _indices_da_expressao(tokens: list[str], expressao: str) -> list[int]:
    partes = expressao.split()
    tamanho = len(partes)
    return [i for i in range(len(tokens) - tamanho + 1) if tokens[i : i + tamanho] == partes]


def calcular_sentimento(texto: str) -> tuple[str, float, list[str]]:
    tokens = tokenizar_para_lexico(texto)
    score = 0.0
    termos_encontrados: list[str] = []
    indices_usados: set[int] = set()

    # 1) Expressões compostas (ex.: "nao recomendo")
    for expressao, valor in EXPRESSOES_COMPOSTAS:
        for inicio in _indices_da_expressao(tokens, expressao):
            if any(i in indices_usados for i in range(inicio, inicio + len(expressao.split()))):
                continue
            score += valor
            termos_encontrados.append(expressao)
            for i in range(inicio, inicio + len(expressao.split())):
                indices_usados.add(i)

    # 2) Ponto de contraste — amplifica o trecho após "mas", "porém" etc.
    indice_contraste = next((i for i, t in enumerate(tokens) if t in CONTRASTE), None)

    # 3) Tokens individuais com janela de contexto
    for indice, token in enumerate(tokens):
        if indice in indices_usados or token not in LEXICO_PT or " " in token:
            continue

        valor = LEXICO_PT[token]
        janela_anterior = tokens[max(0, indice - 3) : indice]

        if any(negacao in janela_anterior for negacao in NEGACOES):
            valor *= -0.85

        if any(intensificador in janela_anterior for intensificador in INTENSIFICADORES):
            valor *= 1.25

        if indice_contraste is not None and indice > indice_contraste:
            valor *= 1.2

        score += valor
        termos_encontrados.append(token)

    if score >= 0.20:
        sentimento = "Positivo"
    elif score <= -0.20:
        sentimento = "Negativo"
    else:
        sentimento = "Neutro"

    return sentimento, round(score, 2), sorted(set(termos_encontrados))


def extrair_topicos(texto: str) -> list[str]:
    doc = nlp(texto)
    classes = {"NOUN", "ADJ", "PROPN"}
    return [
        token.lemma_.lower()
        for token in doc
        if token.pos_ in classes and not token.is_stop and not token.is_punct and len(token.text) > 2
    ]


def quebrar_comentarios(texto: str) -> list[str]:
    linhas = []
    for linha in texto.splitlines():
        linha = " ".join(linha.strip().split())
        if len(linha) >= 10:
            linhas.append(linha)
    return linhas


def _limpar_texto(texto: str) -> str:
    return " ".join(texto.split())


TEXTO_BLOQUEADO = (
    "cookie", "privacidade", "todos os direitos", "aceitar cookies",
    "newsletter", "cadastre-se", "fale conosco", "menu", "carrinho",
)


def _parece_comentario(texto: str) -> bool:
    texto = _limpar_texto(texto)
    if len(texto) < 20 or len(texto) > 800:
        return False
    if texto.count(" ") < 3:
        return False
    lower = texto.lower()
    if any(termo in lower for termo in TEXTO_BLOQUEADO):
        return False
    if re.fullmatch(r"[\d\s\W]+", texto):
        return False
    return True


def _iter_json_ld(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from _iter_json_ld(item)
    elif isinstance(obj, dict):
        yield obj
        for valor in obj.values():
            if isinstance(valor, (dict, list)):
                yield from _iter_json_ld(valor)


def _extrair_json_ld(soup: BeautifulSoup) -> list[str]:
    candidatos: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            dados = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        for bloco in _iter_json_ld(dados):
            tipo = bloco.get("@type", "")
            tipos = tipo if isinstance(tipo, list) else [tipo]
            if not any(t in ("Review", "UserComments", "Comment") for t in tipos):
                continue
            corpo = bloco.get("reviewBody") or bloco.get("description") or bloco.get("text")
            if isinstance(corpo, str) and _parece_comentario(corpo):
                candidatos.append(_limpar_texto(corpo))
    return candidatos


def extrair_comentarios_do_html(html: str) -> list[str]:
    """Extrai comentários/avaliações de HTML já baixado."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()

    candidatos: list[str] = []
    candidatos.extend(_extrair_json_ld(soup))

    seletores = [
        "[itemprop='reviewBody']",
        "[itemprop='commentBody']",
        "[itemprop='description'][itemscope]",
        "[class*='review-text']",
        "[class*='review-body']",
        "[class*='review-content']",
        "[class*='comment-text']",
        "[class*='comment-body']",
        "[class*='comment-content']",
        "[class*='user-comment']",
        "[class*='customer-review']",
        "[class*='avaliacao']",
        "[class*='depoimento']",
        "[class*='testimonial']",
        "[class*='opinion']",
        "[class*='feedback']",
        "[class*='comment']",
        "[class*='review']",
        "[id*='comment']",
        "[id*='review']",
        "[id*='avaliacao']",
        "[data-review]",
        "[data-comment]",
        "blockquote",
        ".review-item p",
        ".comment-item p",
        "article p",
    ]

    vistos_elementos: set[int] = set()
    for seletor in seletores:
        for elemento in soup.select(seletor):
            elemento_id = id(elemento)
            if elemento_id in vistos_elementos:
                continue
            vistos_elementos.add(elemento_id)
            texto = _limpar_texto(elemento.get_text(" ", strip=True))
            if _parece_comentario(texto):
                candidatos.append(texto)

    if len(candidatos) < 3:
        for paragrafo in soup.find_all("p"):
            texto = _limpar_texto(paragrafo.get_text(" ", strip=True))
            if _parece_comentario(texto):
                candidatos.append(texto)

    if len(candidatos) < 2:
        candidatos.extend(
            linha for linha in quebrar_comentarios(soup.get_text("\n", strip=True)) if _parece_comentario(linha)
        )

    comentarios_unicos: list[str] = []
    for texto in candidatos:
        if texto not in comentarios_unicos:
            comentarios_unicos.append(texto)

    return comentarios_unicos[:100]


def extrair_comentarios_da_pagina(url: str) -> list[str]:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    resposta = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        },
    )
    resposta.raise_for_status()
    resposta.encoding = resposta.apparent_encoding or "utf-8"
    return extrair_comentarios_do_html(resposta.text)


def analisar_comentarios(comentarios: list[str]) -> tuple[pd.DataFrame, list[str]]:
    linhas = []
    todos_topicos = []

    for comentario in comentarios:
        sentimento, score, termos = calcular_sentimento(comentario)
        topicos = extrair_topicos(comentario)
        todos_topicos.extend(topicos)
        linhas.append(
            {
                "comentario": comentario,
                "sentimento": sentimento,
                "score": score,
                "palavras_de_sentimento": ", ".join(termos) if termos else "-",
                "topicos": ", ".join(topicos[:6]) if topicos else "-",
            }
        )

    return pd.DataFrame(linhas), todos_topicos


def calcular_reputacao(df: pd.DataFrame) -> tuple[str, float, str]:
    if df.empty:
        return "Sem dados", 0.0, "Insira comentários para processar."

    positivos = (df["sentimento"] == "Positivo").sum()
    negativos = (df["sentimento"] == "Negativo").sum()
    total = len(df)
    score_medio = mean(df["score"])
    indice = ((positivos - negativos) / total) * 100

    if indice >= 30 and score_medio > 0:
        return "🟢 Boa Reputação", indice, "A percepção geral é predominantemente favorável."
    if indice <= -15 or score_medio < -0.2:
        return "🔴 Reputação em Risco", indice, "Excesso de menções negativas ou reclamações graves."
    return "🟡 Reputação Neutra / Mista", indice, "Opiniões balanceadas ou comentários descritivos."


# ==============================================================================
# INTERFACE GRÁFICA STREAMLIT
# ==============================================================================
DEMO_URL = (
    "https://raw.githubusercontent.com/nevessimon56-glitch/Trabalho-Senai-/"
    "cursor/fix-reputaai-nlp-sentiment-c8f5/demo_pagina_avaliacoes.html"
)

st.title("🛡️ ReputaAI — Análise de Reputação & Sentimentos")
st.caption(
    "Cole a **URL** de uma página de produto/avaliações — o sistema extrai os comentários "
    "automaticamente e gera o diagnóstico de reputação."
)

with st.container(border=True):
    aba_url, aba_manual = st.tabs(["🌐 Extrair da URL (principal)", "✍️ Colar comentários manualmente"])

    with aba_url:
        if st.button("Usar URL de demonstração"):
            st.session_state["url_field"] = DEMO_URL

        url_input = st.text_input(
            "Link da página (produto, avaliações, reclamações...)",
            placeholder="https://loja.com.br/produto/smartphone-xyz",
            help="O scraper busca blocos de comentários, avaliações e depoimentos na página.",
            key="url_field",
        )
        btn_url = st.button("🔍 Extrair comentários e analisar", type="primary", width="stretch")

        st.info(
            "Como funciona: informe a URL → o sistema baixa a página → "
            "identifica textos de comentários/avaliações → classifica sentimentos e aspectos."
        )

        if btn_url:
            if not url_input.strip():
                st.warning("Insira a URL do site para continuar.")
            else:
                with st.spinner("Acessando a página e extraindo comentários..."):
                    try:
                        comentarios_extraidos = extrair_comentarios_da_pagina(url_input.strip())
                        if comentarios_extraidos:
                            st.session_state["comentarios"] = comentarios_extraidos
                            st.session_state["origem"] = urlparse(url_input.strip()).netloc or "URL informada"
                            st.rerun()
                        else:
                            st.error(
                                "Nenhum comentário encontrado nesta página. "
                                "Alguns sites bloqueiam acesso automático — tente outra URL ou a aba manual."
                            )
                    except requests.HTTPError as erro:
                        st.error(
                            f"Site retornou erro HTTP ({erro.response.status_code}). "
                            "Muitas lojas bloqueiam scraping — use a URL de demonstração ou a aba manual."
                        )
                    except requests.RequestException as erro:
                        st.error(f"Não foi possível acessar a URL: {erro}")
                    except Exception as erro:
                        st.error(f"Erro inesperado: {erro}")

    with aba_manual:
        texto_manual = st.text_area(
            "Cole os comentários (um por linha)",
            value=EXEMPLOS,
            height=160,
        )
        if st.button("Analisar Texto Manual", type="primary", width="stretch"):
            comentarios_divididos = quebrar_comentarios(texto_manual)
            if comentarios_divididos:
                st.session_state["comentarios"] = comentarios_divididos
                st.session_state["origem"] = "Inserção Manual"
                st.rerun()
            else:
                st.warning("Nenhuma linha válida encontrada (mínimo 10 caracteres por linha).")

# ==============================================================================
# EXIBIÇÃO DE RESULTADOS
# ==============================================================================
comentarios_processar = st.session_state.get("comentarios", [])
origem_atual = st.session_state.get("origem", "")

if not comentarios_processar:
    st.info("👆 Cole a **URL** do site na aba acima e clique em **Extrair comentários e analisar**.")
    st.stop()

with st.expander(f"Ver {len(comentarios_processar)} comentários extraídos", expanded=False):
    for i, c in enumerate(comentarios_processar[:20], 1):
        st.write(f"{i}. {c}")
    if len(comentarios_processar) > 20:
        st.caption(f"... e mais {len(comentarios_processar) - 20} comentários.")

df_resultado, lista_topicos = analisar_comentarios(comentarios_processar)
status_reputacao, indice_rep, explicacao_rep = calcular_reputacao(df_resultado)
contagem_sentimentos = df_resultado["sentimento"].value_counts()

st.divider()
st.subheader(f"📊 Diagnóstico — {origem_atual}")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Status da Reputação", status_reputacao)
col_m2.metric(
    "Índice Líquido",
    f"{indice_rep:+.1f}%",
    help="(% Positivos − % Negativos) sobre o total de comentários",
)
col_m3.metric("Total de Comentários", len(df_resultado))
col_m4.metric("Score Médio", f"{df_resultado['score'].mean():.2f}")

st.info(f"**Diagnóstico:** {explicacao_rep}")

col_grafico, col_topicos = st.columns([1.1, 0.9])

with col_grafico:
    with st.container(border=True):
        st.markdown("**Distribuição dos Sentimentos**")
        df_chart = pd.DataFrame(
            {
                "Sentimento": ["Positivo", "Neutro", "Negativo"],
                "Quantidade": [
                    int(contagem_sentimentos.get("Positivo", 0)),
                    int(contagem_sentimentos.get("Neutro", 0)),
                    int(contagem_sentimentos.get("Negativo", 0)),
                ],
                "Cor": [CORES_SENTIMENTO[s] for s in ["Positivo", "Neutro", "Negativo"]],
            }
        )
        st.bar_chart(
            df_chart,
            x="Sentimento",
            y="Quantidade",
            color="Cor",
            x_label="Sentimento",
            y_label="Quantidade",
            height=280,
        )

with col_topicos:
    with st.container(border=True):
        st.markdown("**Tópicos e Aspectos (spaCy POS)**")
        topicos_frequentes = Counter(lista_topicos).most_common(8)
        if topicos_frequentes:
            max_freq = max(freq for _, freq in topicos_frequentes)
            df_topicos = pd.DataFrame(topicos_frequentes, columns=["Aspecto/Termo", "Menções"])
            st.dataframe(
                df_topicos,
                width="stretch",
                hide_index=True,
                height=260,
                column_config={
                    "Menções": st.column_config.ProgressColumn(
                        "Frequência",
                        format="%d",
                        min_value=0,
                        max_value=max_freq,
                    )
                },
            )
        else:
            st.write("Nenhum tópico relevante extraído.")

with st.container(border=True):
    col_tab_tit, col_tab_filter = st.columns([0.7, 0.3])
    with col_tab_tit:
        st.markdown("**Detalhamento dos Comentários**")
    with col_tab_filter:
        filtro_sentimento = st.selectbox(
            "Filtrar por sentimento",
            ["Todos", "Positivo", "Neutro", "Negativo"],
            label_visibility="collapsed",
        )

    df_exibicao = df_resultado.copy()
    if filtro_sentimento != "Todos":
        df_exibicao = df_exibicao[df_exibicao["sentimento"] == filtro_sentimento]

    st.dataframe(
        df_exibicao.sort_values("score", ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "comentario": st.column_config.TextColumn("Comentário", width="large"),
            "sentimento": st.column_config.TextColumn("Sentimento", width="small"),
            "score": st.column_config.NumberColumn("Score", format="%.2f", width="small"),
            "palavras_de_sentimento": st.column_config.TextColumn("Gatilhos Léxicos"),
            "topicos": st.column_config.TextColumn("Aspectos (POS)"),
        },
    )

    nome_arquivo = f"analise_reputacao_{origem_atual.replace('.', '_').replace(' ', '_')}.csv"
    st.download_button(
        "📥 Baixar Relatório em CSV",
        data=df_resultado.to_csv(index=False).encode("utf-8"),
        file_name=nome_arquivo,
        mime="text/csv",
        width="stretch",
    )
