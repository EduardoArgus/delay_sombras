import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Zonas de Sombra - Telemetria", layout="wide")

st.title("🚚 Dashboard de Zonas de Sombra e Latência")
st.markdown("Faça o upload de MÚLTIPLAS bases (Pargus, FT-Cloud, Hat-Cloud) simultaneamente.")

# --- FUNÇÃO AUXILIAR PARA CORES ---
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return list(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + [200]

# --- BARRA LATERAL (Filtros, Upload e Regras) ---
with st.sidebar:
    st.header("Configurações")
    uploaded_files = st.file_uploader("Arraste suas planilhas aqui (pode ser mais de uma)", type=["xlsx", "xls", "csv"], accept_multiple_files=True)
    
    st.divider()
    st.subheader("🎨 Regras de Cor e Latência")
    
    if 'regras' not in st.session_state:
        st.session_state.regras = [{'max': 5, 'cor': '#00b050'}, {'max': 30, 'cor': '#ffc000'}]
    
    novas_regras = []
    for i, regra in enumerate(st.session_state.regras):
        cols = st.columns([2, 1, 1])
        with cols[0]:
            novo_max = st.number_input(f"Até (min):", value=regra['max'], key=f"max_{i}")
        with cols[1]:
            nova_cor = st.color_picker(f"Cor", value=regra['cor'], key=f"cor_{i}", label_visibility="collapsed")
        with cols[2]:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            deletar = st.button("❌", key=f"del_{i}", help="Remover esta regra")
            
        if not deletar:
            novas_regras.append({'max': novo_max, 'cor': nova_cor})

    st.session_state.regras = novas_regras

    if st.button("➕ Adicionar Parâmetro"):
        ultimo_valor = st.session_state.regras[-1]['max'] + 10 if st.session_state.regras else 5
        st.session_state.regras.append({'max': ultimo_valor, 'cor': '#0000ff'})
        st.rerun()

    cor_critico = st.color_picker("Cor Acima do Máximo (Crítico)", value="#ff0000")
    regras_ordenadas = sorted(st.session_state.regras, key=lambda x: x['max'])

    def get_categoria(delay):
        prev_max = 0
        for regra in regras_ordenadas:
            max_val = int(regra['max'])
            if delay <= max_val:
                if prev_max == 0: return f"Até {max_val} min"
                else: return f"De {prev_max + 1} a {max_val} min"
            prev_max = max_val
        return f"Crítico (Acima de {prev_max} min)"

    todas_categorias = []
    p_max = 0
    for r in regras_ordenadas:
        m_val = int(r['max'])
        if p_max == 0: todas_categorias.append(f"Até {m_val} min")
        else: todas_categorias.append(f"De {p_max + 1} a {m_val} min")
        p_max = m_val
    todas_categorias.append(f"Crítico (Acima de {p_max} min)")

    st.divider()
    st.subheader("Filtro do Mapa")
    categorias_visiveis = st.multiselect("Selecione as faixas para ver no mapa e tabela:", options=todas_categorias, default=todas_categorias)

if uploaded_files:
    df_list = []
    
    with st.spinner("Lendo e traduzindo dados dos fornecedores..."):
        for file in uploaded_files:
            if file.name.endswith('csv'):
                temp_df = pd.read_csv(file)
            else:
                temp_df = pd.read_excel(file)
            
            colunas = temp_df.columns.tolist()
            
            if 'Hora de completação de evidências' in colunas:
                temp_df = temp_df.rename(columns={
                    'Frota': 'Operação',
                    'número de registro do veículo': 'Frota',
                    'Tipo de alarme': 'Evento',
                    'Tempo de alarme': 'Hora_alarme',
                    'Hora de completação de evidências': 'Hora_chegada_alarme'
                })
                temp_df['Fornecedor'] = 'FT-CLOUD'
                
            elif 'Received Time' in colunas:
                temp_df = temp_df.rename(columns={
                    'Organization': 'Operação',
                    'Plate No.': 'Frota',
                    'Alarm Item': 'Evento',
                    'Alarm Time': 'Hora_alarme',
                    'Received Time': 'Hora_chegada_alarme'
                })
                if 'Latitude' not in temp_df.columns: temp_df['Latitude'] = None
                if 'Longitude' not in temp_df.columns: temp_df['Longitude'] = None
                temp_df['Fornecedor'] = 'HAT-CLOUD'
                
            elif 'Hora_chegada_alarme' in colunas:
                temp_df['Fornecedor'] = 'PARGUS'
            
            colunas_oficiais = ['Fornecedor', 'Operação', 'Frota', 'Evento', 'Hora_alarme', 'Hora_chegada_alarme', 'Latitude', 'Longitude']
            col_existentes = [c for c in colunas_oficiais if c in temp_df.columns]
            df_list.append(temp_df[col_existentes])
            
        df = pd.concat(df_list, ignore_index=True)
        
        # Convertendo para datetime e forçando o padrão brasileiro (dia antes do mês)
        df['Hora_alarme'] = pd.to_datetime(df['Hora_alarme'], errors='coerce', dayfirst=True)
        df['Hora_chegada_alarme'] = pd.to_datetime(df['Hora_chegada_alarme'], errors='coerce', dayfirst=True)
        df = df.dropna(subset=['Hora_alarme', 'Hora_chegada_alarme'])
        
        # Cálculos de Delay (Minutos, Horas e Dias)
        df['Delay_Minutos'] = (df['Hora_chegada_alarme'] - df['Hora_alarme']).dt.total_seconds() / 60
        df['Delay_Minutos'] = df['Delay_Minutos'].astype(int)
        df['Delay_Horas'] = (df['Delay_Minutos'] / 60).round(1)
        df['Delay_Dias'] = (df['Delay_Horas'] / 24).round(1)
        
        df['Categoria_Delay'] = df['Delay_Minutos'].apply(get_categoria)

    # --- NOVOS FILTROS (Com Data) ---
    st.divider()
    
    # Extrair datas mínima e máxima da base para o calendário
    min_date = df['Hora_alarme'].dt.date.min()
    max_date = df['Hora_alarme'].dt.date.max()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        # Filtro de Data
        datas_selecionadas = st.date_input("Filtrar Período:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    with col2:
        forns = st.multiselect("Filtrar Fornecedor:", options=df['Fornecedor'].unique(), default=df['Fornecedor'].unique())
    with col3:
        ops = st.multiselect("Filtrar Operação:", options=df['Operação'].unique(), default=df['Operação'].unique())
    with col4:
        frotas = st.multiselect("Filtrar Frota:", options=df['Frota'].unique())
        
    df_filtrado = df.copy()
    
    # Aplica o filtro de data (trata se o usuário selecionou só o começo ou o começo e fim)
    if len(datas_selecionadas) == 2:
        df_filtrado = df_filtrado[(df_filtrado['Hora_alarme'].dt.date >= datas_selecionadas[0]) & (df_filtrado['Hora_alarme'].dt.date <= datas_selecionadas[1])]
    elif len(datas_selecionadas) == 1:
        df_filtrado = df_filtrado[df_filtrado['Hora_alarme'].dt.date == datas_selecionadas[0]]
        
    if forns: df_filtrado = df_filtrado[df_filtrado['Fornecedor'].isin(forns)]
    if ops: df_filtrado = df_filtrado[df_filtrado['Operação'].isin(ops)]
    if frotas: df_filtrado = df_filtrado[df_filtrado['Frota'].isin(frotas)]

    st.divider()

    # --- CÁLCULO DAS PORCENTAGENS ---
    # --- CÁLCULO DAS PORCENTAGENS ---
    st.subheader("Distribuição de Latência (Geral da Seleção)")
    total_eventos = len(df_filtrado)
    kpi_cols = st.columns(len(todas_categorias))
    
    for i, cat in enumerate(todas_categorias):
        qtd = len(df_filtrado[df_filtrado['Categoria_Delay'] == cat])
        pct = (qtd / total_eventos * 100) if total_eventos > 0 else 0
        with kpi_cols[i]:
            st.metric(
                label=cat, 
                value=f"{pct:.1f}%", 
                delta=f"{qtd} eventos", 
                delta_color="off" # Desliga o verde/vermelho padrão do delta
            )

    # --- FILTRO MAPA ---
    df_mapa = df_filtrado[df_filtrado['Categoria_Delay'].isin(categorias_visiveis)].copy()
    
    def aplicar_cor_dinamica(delay):
        for regra in regras_ordenadas:
            if delay <= regra['max']: return hex_to_rgb(regra['cor'])
        return hex_to_rgb(cor_critico)
            
    df_mapa['color'] = df_mapa['Delay_Minutos'].apply(aplicar_cor_dinamica)
    
    # Separar os que tem coordenada dos que não tem e criar uma cópia limpa
    df_com_coord = df_mapa.dropna(subset=['Latitude', 'Longitude']).copy()
    
    # Formatar as datas para aparecerem bonitas no mapa (padrão brasileiro)
    df_com_coord['Data_Gerado'] = df_com_coord['Hora_alarme'].dt.strftime('%d/%m/%Y %H:%M:%S')
    df_com_coord['Data_Chegada'] = df_com_coord['Hora_chegada_alarme'].dt.strftime('%d/%m/%Y %H:%M:%S')

    st.success(f"Mostrando no mapa: {len(df_com_coord)} eventos com coordenadas válidas. (Total na tabela: {len(df_mapa)})")

    # --- MAPA INTERATIVO ---
    st.subheader("Mapa de Áreas Críticas")
    
    layer = pdk.Layer(
        "ScatterplotLayer",
        df_com_coord,
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_scale=20,
        radius_min_pixels=5,
        radius_max_pixels=15,
        line_width_min_pixels=1,
        get_position="[Longitude, Latitude]",
        # get_radius="Delay_Minutos",
        get_fill_color="color",
        get_line_color=[0, 0, 0],
    )

    view_state = pdk.ViewState(
        latitude=df_com_coord['Latitude'].mean() if not df_com_coord.empty else -15.0,
        longitude=df_com_coord['Longitude'].mean() if not df_com_coord.empty else -50.0,
        zoom=10,
        pitch=0,
    )

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        # Balão (tooltip) atualizado com as datas formatadas
        tooltip={"text": "Fornecedor: {Fornecedor}\nFrota: {Frota}\nOperação: {Operação}\nFaixa: {Categoria_Delay}\nDelay: {Delay_Minutos} min\nGerado em: {Data_Gerado}\nChegou em: {Data_Chegada}"},
        map_style=None,
    )

    st.pydeck_chart(r)
    
    # --- TABELA DE DADOS ---
    # --- TABELA DE DADOS ---
    # --- TABELA DE DADOS ---
    st.subheader("Dados Críticos")
    
    # Criamos uma cópia só para a tabela para não estragar os dados originais
    df_tabela = df_mapa[['Fornecedor', 'Operação', 'Frota', 'Evento', 'Hora_alarme', 'Hora_chegada_alarme', 'Categoria_Delay', 'Delay_Minutos', 'Delay_Horas', 'Delay_Dias', 'Latitude', 'Longitude']].copy()
    
    # Formatando as datas para o padrão brasileiro
    df_tabela['Hora_alarme'] = df_tabela['Hora_alarme'].dt.strftime('%d/%m/%Y %H:%M:%S')
    df_tabela['Hora_chegada_alarme'] = df_tabela['Hora_chegada_alarme'].dt.strftime('%d/%m/%Y %H:%M:%S')
    
    # Exibindo a tabela ordenada
    st.dataframe(df_tabela.sort_values('Delay_Minutos', ascending=False))
else:
    st.info("Aguardando upload da(s) planilha(s)...")