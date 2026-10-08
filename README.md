# 🚚 Dashboard de Zonas de Sombra e Latência

Uma aplicação web interativa desenvolvida em Python (Streamlit) para mapear e analisar atrasos de comunicação (latência) em equipamentos de telemetria logística.

## O que faz?
* Processa arquivos de múltiplos fornecedores simultaneamente (Pargus, FT-Cloud, Hat-Cloud).
* Calcula automaticamente o atraso (delay) entre a geração do alarme no veículo e a recepção na plataforma.
* Plota os eventos críticos num mapa híbrido interativo para identificar zonas de sombra geográficas.
* Permite criar regras dinâmicas de cores e tempos de tolerância.

## Como rodar o projeto

1. Clone este repositório.
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Inicie a aplicação:
   ```bash
   streamlit run app_zonas_sombra.py
   ```
4. Acesse o link gerado no terminal (geralmente `http://localhost:8501`) e faça o upload das suas planilhas de telemetria.
