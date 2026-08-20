# ReputaAI — Análise de Reputação & Sentimentos

Dashboard para mineração de opiniões, classificação de sentimentos em português e extração de aspectos.

## O que faz

- **Classificação léxica** calibrada para PT-BR (negações, intensificadores, contrastes)
- **Extração de tópicos/aspectos** citados nos comentários
- **Diagnóstico de reputação** com índice líquido e exportação CSV
- **Web scraping** por URL (apenas na versão Streamlit)

## Versão HTML — roda direto no navegador

Abra o arquivo **`reputai.html`** com duplo clique (Chrome, Edge ou Firefox). Não precisa instalar Python.

1. Os exemplos já vêm carregados
2. Clique em **Analisar Comentários**
3. Use **Baixar CSV** para exportar o relatório

> Scraping por URL não funciona no HTML (bloqueio CORS do navegador). Use a versão Streamlit para isso.

## Versão Streamlit — completa (spaCy + URL)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Na aba **Comentários Manuais**, use os exemplos e clique em **Analisar Texto Manual**.

## Stack

- HTML + JavaScript (standalone)
- Streamlit, Pandas, spaCy (`pt_core_news_sm`), BeautifulSoup4, Requests
