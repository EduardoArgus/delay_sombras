# 🚚 Dashboard de Zonas de Sombra e Latência - Telemetria Logística

![Status](https://img.shields.io/badge/Status-Concluído-success)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Framework-FF4B4B)

## 📌 Sobre o Projeto
Em operações logísticas e de telemetria, o atraso na comunicação de eventos (como perda de sinal, distração do motorista ou alertas de pânico) pode comprometer a segurança da frota. 

Este projeto é uma ferramenta de **Data Science e Geoprocessamento** construída para identificar "Zonas de Sombra" (áreas sem cobertura de rede) ao calcular a diferença exata entre a hora em que o evento ocorreu no equipamento e a hora em que chegou à plataforma na nuvem.

## 🚀 Principais Funcionalidades

* **ETL Universal (Multi-Fornecedor):** Leitura e padronização automática de dados provenientes de diferentes plataformas de rastreamento (PARGUS, FT-CLOUD e HAT-CLOUD).
* **Análise Espacial Dinâmica:** Mapeamento visual das ocorrências utilizando `PyDeck` com mapas de satélite, onde o tamanho do raio é proporcional ao tempo de latência.
* **Motor de Regras Customizável:** Interface que permite ao usuário criar parâmetros dinâmicos de tolerância (ex: Até 5 min = Verde; 6 a 30 min = Laranja; +30 min = Crítico) sem necessidade de alterar o código.
* **Cálculos Temporais:** Processamento do delay em Minutos, Horas e Dias completos.
* **KPIs em Tempo Real:** Cartões de métricas e distribuições percentuais que respondem instantaneamente aos filtros de Data, Operação e Frota.

## 🛠️ Tecnologias Utilizadas

* **Python:** Linguagem base da aplicação.
* **Streamlit:** Construção do frontend e reatividade do dashboard.
* **Pandas:** Limpeza, transformação (ETL) e cálculos matemáticos das datas.
* **PyDeck / Mapbox:** Renderização de mapas espaciais em alta performance.
* **OpenPyXL:** Leitura e extração de dados de arquivos `.xlsx` e `.xls`.

## ⚙️ Pré-requisitos e Instalação

Certifique-se de ter o [Python](https://www.python.org/) instalado na sua máquina.

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/SEU_USUARIO/zonas-de-sombra-telemetria.git
   cd zonas-de-sombra-telemetria
   ```

2. **Crie um ambiente virtual (Opcional, mas recomendado):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Windows use: venv\Scripts\activate
   ```

3. **Instale as bibliotecas necessárias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicie o servidor:**
   ```bash
   streamlit run app_zonas_sombra.py
   ```

## 📊 Como Utilizar
1. Na barra lateral, defina as suas regras de latência (tempo máximo em minutos e a respectiva cor desejada para o mapa).
2. Arraste um ou mais arquivos Excel/CSV com os dados de telemetria para a área de upload.
3. Utilize os filtros de **Período, Fornecedor, Operação ou Frota** para isolar anomalias.
4. Navegue pelo mapa, utilize o zoom e passe o mouse sobre os pontos para visualizar o diagnóstico completo de cada perda de sinal.

---
*Desenvolvido com foco na melhoria contínua de processos logísticos.*
