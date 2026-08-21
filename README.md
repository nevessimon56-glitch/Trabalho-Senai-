# ReputaAI — Análise de Reputação & Sentimentos

Dashboard para mineração de opiniões a partir de **URL de sites**, classificação de sentimentos em português e extração de aspectos.

## Como usar (principal)

1. Cole a **URL** da página de produto/avaliações/comentários
2. Clique em **Extrair comentários e analisar**
3. Veja o diagnóstico de reputação e baixe o CSV

## URL que funciona no laboratório (copie e cole no app)

```
https://raw.githubusercontent.com/nevessimon56-glitch/Trabalho-Senai-/cursor/fix-reputaai-nlp-sentiment-c8f5/demo_pagina_avaliacoes.html
```

Página de **produto fictício** com **8 avaliações de compradores** em português, no formato HTML real (`reviewBody`, `customer-review`). Use no botão **Usar URL de demonstração** ou cole manualmente.

> Lojas grandes (Midea, Natura, Amazon, Mercado Livre) **não funcionam** — carregam reviews via JavaScript. Para essas lojas, copie os comentários manualmente da página do produto.

## Versão HTML — duplo clique no Windows

1. Baixe **`ReputaAI.html`** e **`ABRIR_REPUTAAI.bat`**
2. Duplo clique no **`.bat`**
3. Na aba **Extrair da URL**, clique em **Usar URL de demonstração** e depois **Extrair comentários e analisar**

> Alguns sites (Mercado Livre, Amazon, Reclame Aqui) bloqueiam acesso automático.  
> Use a **URL de demonstração** para testar, ou a versão Streamlit para URLs reais.

## Versão Streamlit — recomendada para URLs reais

```bash
pip install -r requirements.txt
streamlit run app.py
```

Na aba **Extrair da URL**, cole o link e clique em **Extrair comentários e analisar**.

## Arquivos

| Arquivo | Função |
|---------|--------|
| `ReputaAI.html` | Dashboard no navegador (URL + manual) |
| `ABRIR_REPUTAAI.bat` | Abre o HTML no Windows |
| `app.py` | Versão completa com spaCy e scraping Python |
| `demo_pagina_avaliacoes.html` | Página de teste com avaliações fictícias |

## Stack

- HTML + JavaScript (scraping via proxy CORS no navegador)
- Streamlit, Pandas, spaCy, BeautifulSoup4, Requests
