from collections import Counter
from statistics import mean
import json
import re
import unicodedata
from urllib.parse import quote, urlparse

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


class PaginaBloqueadaError(Exception):
    """A página retornou bloqueio (Cloudflare, captcha etc.), não comentários reais."""


TEXTO_BLOQUEADO = (
    "cookie", "privacidade", "todos os direitos", "aceitar cookies",
    "newsletter", "cadastre-se", "fale conosco", "menu", "carrinho",
)

TEXTO_ERRO_SISTEMA = (
    "cloudflare", "ray id", "origin web server", "please try again",
    "unknown connection issue", "web page can not be displayed",
    "web page cannot be displayed", "performance & security by cloudflare",
    "troubleshooting resources", "error 502", "error 503", "error 403",
    "access denied", "attention required", "cf-error", "checking your browser",
    "enable javascript", "captcha", "bot detection", "just a moment",
    "security check", "ddos protection", "please wait", "blocked",
)

PALAVRAS_PT_COMUNS = {
    "de", "da", "do", "das", "dos", "nao", "não", "que", "com", "para", "uma", "um",
    "produto", "loja", "compra", "comprei", "muito", "bem", "recomendo", "entrega",
    "atendimento", "preco", "preço", "qualidade", "cliente", "servico", "serviço",
}

TEXTO_INSTITUCIONAL = (
    "fortune 500", "joint venture", "canal oficial", "politica de", "política de",
    "clique aqui", "acesse:", "0800", "3003.", "whatsapp", "ouvidoria",
    "nota fiscal", "garantia dever", "checkout", "disponibilizamos",
    "fabricantes de eletrodomesticos", "fabricantes de eletrodomésticos",
    "recomendamos a leitura", "conforme a nossa", "transportadoras parceiras",
    "descarte consciente", "programa de beneficios", "programa de benefícios",
    "politica de troca", "política de troca", "desconfie de pedidos",
    "navegue e encontre", "tenha sempre em maos", "tenha sempre em mãos",
    "central de atendimento", "autorizada informando", "registrar seu produto",
    "suporte mais rapido", "suporte mais rápido", "politica de pagamento",
)

INICIO_FAQ_MARKETING = (
    "sim!", "sim,", "temos,", "temos ", "as opcoes", "as opções", "as marcas",
    "e simples", "voce encontra", "você encontra", "desconfie", "todos os atendimentos",
    "a midea e", "a midea é", "este e o canal", "este é o canal", "disponibilizamos",
    "o reembolso segue", "design compacto",
)

SINAIS_COMPRADOR = (
    "comprei", "comprado", "recebi", "chegou", "gostei", "amei", "odiei",
    "recomendo", "nao recomendo", "não recomendo", "insatisfeito", "satisfeito",
    "minha experi", "minha compra", "usei ", "utilizei", "estrelas",
    "vale a pena", "decepcion", "expectativa", "arrepend", "produto veio",
    "entrega foi", "atendimento foi", "nota ", "pessimo produto", "péssimo produto",
)

SELETORES_REMOVER = (
    "[class*='FAQ']", "[class*='faq']", "[data-testid='faq']",
    "[class*='help-']", "[class*='Help']", "[class*='institutional']",
    "[class*='footer']", "[class*='Footer']", "[class*='banner']",
    "[class*='Banner']", "[class*='newsletter']",
)


def _eh_texto_de_erro(texto: str) -> bool:
    lower = _limpar_texto(texto).lower()
    return any(termo in lower for termo in TEXTO_ERRO_SISTEMA)


def _tem_cara_de_portugues(texto: str) -> bool:
    lower = _limpar_texto(texto).lower()
    if re.search(r"[áàâãéêíóôõúç]", lower):
        return True
    tokens = set(re.findall(r"[a-zà-ú]+", lower))
    return len(tokens & PALAVRAS_PT_COMUNS) >= 2


def _detectar_pagina_bloqueada(html: str, soup: BeautifulSoup) -> str | None:
    lower = html.lower()
    indicadores = sum(
        1
        for termo in (
            "cloudflare",
            "ray id",
            "origin web server",
            "cf-error",
            "attention required",
            "checking your browser",
        )
        if termo in lower
    )
    if indicadores >= 2 or soup.select("#cf-wrapper, .cf-error-overview, [class*='cf-error']"):
        return (
            "O site bloqueou o acesso automático (proteção Cloudflare/anti-bot). "
            "Não foi possível obter comentários reais — use a aba manual ou a URL de demonstração."
        )
    if _eh_texto_de_erro(soup.title.get_text(strip=True) if soup.title else ""):
        return "A página retornou uma tela de erro, não comentários de clientes."
    return None


def _parece_comentario(texto: str, exigir_portugues: bool = True) -> bool:
    texto = _limpar_texto(texto)
    if len(texto) < 20 or len(texto) > 800:
        return False
    if texto.count(" ") < 3:
        return False
    lower = texto.lower()
    if any(termo in lower for termo in TEXTO_BLOQUEADO):
        return False
    if _eh_texto_de_erro(texto):
        return False
    if re.fullmatch(r"[\d\s\W]+", texto):
        return False
    if exigir_portugues and not _tem_cara_de_portugues(texto):
        return False
    return True


def _parece_avaliacao_comprador(texto: str) -> bool:
    """Filtra FAQ, marketing e textos institucionais — mantém opinião de clientes."""
    if not _parece_comentario(texto, exigir_portugues=True):
        return False

    lower = _limpar_texto(texto).lower()
    normalizado = remover_acentos(lower)

    if any(termo in lower or remover_acentos(termo) in normalizado for termo in TEXTO_INSTITUCIONAL):
        return False
    if re.search(r"\b0\d{3,4}[\s.-]?\d{4,}", lower) or "0800" in lower:
        return False
    if any(normalizado.startswith(remover_acentos(p)) for p in INICIO_FAQ_MARKETING):
        return False
    if any(
        p in normalizado
        for p in (
            "voce pode comprar", "para voce escolher", "saiba mais",
            "clique aqui", "acesse:",
        )
    ):
        return False

    tem_voz_comprador = any(remover_acentos(s) in normalizado for s in SINAIS_COMPRADOR)
    tem_eu = bool(re.search(r"\b(eu|minha|meu|minhas|meus)\b", normalizado))
    tokens = set(re.findall(r"[a-zà-ú]+", normalizado))
    tem_sentimento = bool(tokens & set(LEXICO_PT.keys()))

    if not tem_voz_comprador and not tem_eu and not tem_sentimento:
        return False

    return True


def _remover_blocos_institucionais(soup: BeautifulSoup) -> None:
    for seletor in SELETORES_REMOVER:
        for elemento in soup.select(seletor):
            elemento.decompose()


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
            if isinstance(corpo, str) and _parece_avaliacao_comprador(corpo):
                candidatos.append(_limpar_texto(corpo))
    return candidatos


def extrair_comentarios_do_html(html: str) -> list[str]:
    """Extrai comentários/avaliações de HTML já baixado."""
    soup = BeautifulSoup(html, "html.parser")

    bloqueio = _detectar_pagina_bloqueada(html, soup)
    if bloqueio:
        raise PaginaBloqueadaError(bloqueio)

    _remover_blocos_institucionais(soup)

    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav", "aside", "form"]):
        tag.decompose()

    candidatos: list[str] = []
    candidatos.extend(_extrair_json_ld(soup))

    seletores_prioritarios = [
        "[itemprop='reviewBody']",
        "[itemprop='commentBody']",
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
        "[data-review]",
        "[data-comment]",
        "blockquote",
        ".review-item p",
        ".comment-item p",
    ]

    vistos_elementos: set[int] = set()
    for seletor in seletores_prioritarios:
        for elemento in soup.select(seletor):
            elemento_id = id(elemento)
            if elemento_id in vistos_elementos:
                continue
            vistos_elementos.add(elemento_id)
            texto = _limpar_texto(elemento.get_text(" ", strip=True))
            if _parece_avaliacao_comprador(texto):
                candidatos.append(texto)

    comentarios_unicos: list[str] = []
    for texto in candidatos:
        if texto not in comentarios_unicos:
            comentarios_unicos.append(texto)

    if not comentarios_unicos:
        raise PaginaBloqueadaError(
            "Nenhuma avaliação de comprador encontrada nesta URL. "
            "A página parece ser FAQ, institucional ou marketing — não comentários de clientes. "
            "Use a URL da página do produto com avaliações visíveis, ou cole os comentários na aba manual. "
            "Sites como Midea carregam reviews via JavaScript (Vurdere); se não aparecerem no HTML, "
            "copie manualmente os textos da seção de avaliações."
        )

    return _deduplicar_comentarios(comentarios_unicos)[:100]


def _deduplicar_comentarios(textos: list[str]) -> list[str]:
    """Remove comentários contidos em outros (ex.: '5 estrelas' + texto vs só texto)."""
    finais: list[str] = []
    for texto in sorted(set(textos), key=len, reverse=True):
        if any(texto in outro and texto != outro for outro in finais):
            continue
        finais = [u for u in finais if u not in texto]
        finais.append(texto)
    return finais


VURDERE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Origin": "https://www.midea.com.br",
    "Referer": "https://www.midea.com.br/",
}

VURDERE_ECOMMERCE_ID = "mds"


def _parece_texto_vurdere(texto: str) -> bool:
    """Texto vindo da API Vurdere — filtro leve (já são avaliações de compradores)."""
    texto = _limpar_texto(texto)
    if len(texto) < 15 or len(texto) > 2000:
        return False
    if _eh_texto_de_erro(texto):
        return False
    lower = texto.lower()
    if any(termo in lower for termo in TEXTO_INSTITUCIONAL):
        return False
    return True


def _parse_vurdere_json(data) -> list[str]:
    """Extrai textos de avaliação de respostas JSON da Vurdere (Midea)."""
    comentarios: list[str] = []
    chaves = ("reviewBody", "reviewText", "text", "comment", "description", "message", "content", "body")

    def walk(obj):
        if isinstance(obj, dict):
            for key in chaves:
                valor = obj.get(key)
                if isinstance(valor, str):
                    texto = _limpar_texto(BeautifulSoup(valor, "html.parser").get_text(" ", strip=True))
                    if _parece_texto_vurdere(texto):
                        comentarios.append(texto)
            for valor in obj.values():
                walk(valor)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return _deduplicar_comentarios(comentarios)


def _vurdere_get_json(url_api: str, referer: str) -> dict | list | None:
    try:
        resposta = requests.get(
            url_api,
            timeout=20,
            headers={**VURDERE_HEADERS, "Referer": referer},
        )
        if resposta.status_code != 200:
            return None
        if "application/json" not in resposta.headers.get("Content-Type", "application/json"):
            if resposta.text.lstrip().startswith("<"):
                return None
        return resposta.json()
    except (requests.RequestException, json.JSONDecodeError, ValueError):
        return None


def _eh_homepage_midea(url: str) -> bool:
    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    if "midea.com.br" not in parsed.netloc:
        return False
    caminho = parsed.path.strip("/").lower()
    return caminho in ("", "home")


def _extrair_comentarios_vurdere_midea(url: str) -> list[str]:
    """
    Busca avaliações reais na API Vurdere (seção 'Avaliações da loja' / reviews de produto).
    O HTML estático da Midea não traz esses textos — só o widget vazio + FAQ.
    """
    if "midea.com.br" not in url:
        return []

    url_norm = url if url.startswith("http") else f"https://{url}"
    referer = url_norm

    if _eh_homepage_midea(url_norm):
        apis_loja = [
            f"https://midea-br.mais.social/api/store/reviews?ecommerceId={VURDERE_ECOMMERCE_ID}&locale=ptBr&limit=50&filtersCityOff=true",
            f"https://mideastore-br.mais.social/api/store/reviews?ecommerceId={VURDERE_ECOMMERCE_ID}&locale=ptBr&limit=50&filtersCityOff=true",
            f"https://midea-br.mais.social/api/jamstack/reviews?ecommerceId={VURDERE_ECOMMERCE_ID}&locale=ptBr&limit=50",
        ]
        for api in apis_loja:
            dados = _vurdere_get_json(api, referer)
            if dados:
                comentarios = _parse_vurdere_json(dados)
                if comentarios:
                    return comentarios[:100]
        return []

    # Página de produto — resolve IDs via API seo e busca reviews
    seo_url = (
        "https://mideastore-br.mais.social/api/pdp/seo?"
        f"ecommerceId={VURDERE_ECOMMERCE_ID}&url={quote(url_norm, safe='')}"
        "&locale=ptBr&v=4&selectiveLoad=true&trigger=init"
    )
    seo = _vurdere_get_json(seo_url, referer)
    if not isinstance(seo, dict):
        return []

    product_id = seo.get("productId") or seo.get("product_id")
    product_id2 = seo.get("productId2") or seo.get("product_id2") or ""
    sku_id = seo.get("skuId") or seo.get("sku_id") or ""

    if not product_id and isinstance(seo.get("product"), dict):
        product_id = seo["product"].get("productId") or seo["product"].get("id")

    if not product_id:
        return []

    params = (
        f"ecommerceId={VURDERE_ECOMMERCE_ID}&productId={product_id}&locale=ptBr"
        f"&limit=50&showRelated=true&filtersCityOff=true"
    )
    if product_id2:
        params += f"&productId2={product_id2}"
    if sku_id:
        params += f"&skuId={quote(str(sku_id), safe='')}"

    reviews_url = f"https://mideastore-br.mais.social/api/pdp/reviews?{params}"
    dados = _vurdere_get_json(reviews_url, referer)
    if dados:
        comentarios = _parse_vurdere_json(dados)
        if comentarios:
            return comentarios[:100]
    return []


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

    if "midea.com.br" in url:
        comentarios_vurdere = _extrair_comentarios_vurdere_midea(url)
        if comentarios_vurdere:
            return comentarios_vurdere

    try:
        return extrair_comentarios_do_html(resposta.text)
    except PaginaBloqueadaError:
        if "midea.com.br" in url:
            raise PaginaBloqueadaError(
                "A Midea carrega avaliações reais via **Vurdere** (role até *Avaliações da loja*), "
                "mas bloqueia extração automática por URL (CORS/Cloudflare). "
                f"Use a demo: `{MIDEA_DEMO_URL}` ou cole os textos na aba manual."
            ) from None
        raise


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

MIDEA_HOME_URL = "https://www.midea.com.br/"

MIDEA_DEMO_URL = (
    "https://raw.githubusercontent.com/nevessimon56-glitch/Trabalho-Senai-/"
    "cursor/fix-reputaai-nlp-sentiment-c8f5/demo_midea_avaliacoes.html"
)

URL_LAB_FUNCIONA = DEMO_URL  # página pública de teste com avaliações de compradores no HTML

st.title("🛡️ ReputaAI — Análise de Reputação & Sentimentos")
st.caption(
    "Cole a **URL** de uma página de produto/avaliações — o sistema extrai os comentários "
    "automaticamente e gera o diagnóstico de reputação."
)

with st.container(border=True):
    aba_url, aba_manual = st.tabs(["🌐 Extrair da URL (principal)", "✍️ Colar comentários manualmente"])

    with aba_url:
        col_demo, col_midea = st.columns(2)
        with col_demo:
            if st.button("Usar URL de demonstração"):
                st.session_state["url_field"] = DEMO_URL
        with col_midea:
            if st.button("Demo Midea (funciona)"):
                st.session_state["url_field"] = MIDEA_DEMO_URL

        url_input = st.text_input(
            "Link da página (produto, avaliações, reclamações...)",
            placeholder="https://loja.com.br/produto/smartphone-xyz",
            help="O scraper busca blocos de comentários, avaliações e depoimentos na página.",
            key="url_field",
        )
        btn_url = st.button("🔍 Extrair comentários e analisar", type="primary", width="stretch")

        st.success(
            f"**URL que funciona no laboratório:** cole esta página de produto com avaliações "
            f"visíveis no HTML:\n\n`{URL_LAB_FUNCIONA}`"
        )
        st.info(
            "**Midea real** (`midea.com.br`): as avaliações ao rolar a página são da Vurdere, "
            "mas **não dá para extrair pela URL** — use **ReputaAI.html → aba Midea (Vurdere)** "
            "com o bookmarklet, ou a **Demo Midea** acima para o laboratório."
        )
        with st.expander("Como copiar avaliações da Midea real (ReputaAI.html)"):
            st.markdown(
                "1. Abra [midea.com.br](https://www.midea.com.br/) e role até **Avaliações da loja**.\n"
                "2. No **ReputaAI.html**, aba **Midea (Vurdere)**, arraste o bookmarklet verde para favoritos.\n"
                "3. Na Midea, clique no favorito → volte ao ReputaAI → aba manual → Ctrl+V → Analisar."
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
                    except PaginaBloqueadaError as erro:
                        st.error(str(erro))
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
