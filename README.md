# ReputaAI — Análise de Reputação & Sentimentos

Dashboard Streamlit para mineração de opiniões, classificação de sentimentos em português e extração de aspectos com spaCy.

## O que faz

- **Web scraping** de comentários/avaliações via URL (BeautifulSoup)
- **Classificação léxica** calibrada para PT-BR (negações, intensificadores, contrastes)
- **Extração de tópicos** com POS tagging (spaCy `pt_core_news_sm`)
- **Diagnóstico de reputação** com índice líquido e exportação CSV

## Instalação

```bash
pip install -r requirements.txt
```

O modelo spaCy em português já está incluído no `requirements.txt`. Se preferir instalar manualmente:

```bash
python -m spacy download pt_core_news_sm
```

## Execução

```bash
streamlit run app.py
```

Abra o arquivo `reputai.html` com duplo clique no navegador — não precisa instalar nada.

Para scraping por URL e spaCy completo, use a versão Streamlit (`streamlit run app.py`).


1. Aba **Comentários Manuais** — use os exemplos pré-carregados e clique em **Analisar Texto Manual**
2. Aba **URL da Web** — cole o link de uma página com avaliações/comentários

## Stack

- Streamlit, Pandas
- spaCy (`pt_core_news_sm`)
- BeautifulSoup4, Requests
