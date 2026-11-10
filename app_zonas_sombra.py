import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk

st.set_page_config(page_title="Zonas de Sombra - Telemetria", layout="wide")

st.title("🚚 Dashboard de Zonas de Sombra e Latência")
st.markdown("Faça o upload de MÚLTIPLAS bases (Pargus, FT-Cloud, Hat-Cloud) simultaneamente.")

# --- FUNÇÕES AUXILIARES ---
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return list(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + [200]

def corrigir_coordenada(val, limite):
    """Corrige coordenadas que perderam o ponto decimal no Excel (ex: -19645227 -> -19.645227)"""
    if pd.isna(val) or val == 0:
        return np.nan
    try:
        val = float(val)
    except:
        return np.nan
    while abs(val) > limite:
        val /= 10.0
    return val

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
            
            temp_df.columns = temp_df.columns.str.strip()
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
                temp_df['Fornecedor'] = 'HAT-CLOUD'
                
            elif 'Hora_chegada_alarme' in colunas or 'hora_chegada_alarme' in [c.lower() for c in colunas]:
                mapa_pargus = {
                    'operacao': 'Operação',
                    'operação': 'Operação',
                    'frota': 'Frota',
                    'evento': 'Evento',
                    'hora_alarme': 'Hora_alarme',
                    'hora_chegada_alarme': 'Hora_chegada_alarme',
                    'latitude': 'Latitude',
                    'longitude': 'Longitude'
                }
                temp_df = temp_df.rename(columns=lambda c: mapa_pargus.get(c.lower(), c))
                temp_df['Fornecedor'] = 'PARGUS'
            
            colunas_oficiais = ['Fornecedor', 'Operação', 'Frota', 'Evento', 'Hora_alarme', 'Hora_chegada_alarme', 'Latitude', 'Longitude']
            for col in colunas_oficiais:
                if col not in temp_df.columns:
                    temp_df[col] = np.nan if col in ['Latitude', 'Longitude', 'Hora_alarme', 'Hora_chegada_alarme'] else 'Não informado'
                    
            df_list.append(temp_df[colunas_oficiais])
            
        df = pd.concat(df_list, ignore_index=True)
        
        df['Hora_alarme'] = pd.to_datetime(df['Hora_alarme'], errors='coerce', dayfirst=True)
        df['Hora_chegada_alarme'] = pd.to_datetime(df['Hora_chegada_alarme'], errors='coerce', dayfirst=True)
        df = df.dropna(subset=['Hora_alarme', 'Hora_chegada_alarme'])
        
        df['Latitude'] = df['Latitude'].apply(lambda x: corrigir_coordenada(x, 90))
        df['Longitude'] = df['Longitude'].apply(lambda x: corrigir_coordenada(x, 180))
        
        df['Delay_Minutos'] = (df['Hora_chegada_alarme'] - df['Hora_alarme']).dt.total_seconds() / 60
        df['Delay_Minutos'] = df['Delay_Minutos'].astype(int)
        df['Delay_Horas'] = (df['Delay_Minutos'] / 60).round(1)
        df['Delay_Dias'] = (df['Delay_Horas'] / 24).round(1)
        
        df['Categoria_Delay'] = df['Delay_Minutos'].apply(get_categoria)

    # --- FILTROS ---
    st.divider()
    
    min_date = df['Hora_alarme'].dt.date.min()
    max_date = df['Hora_alarme'].dt.date.max()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        datas_selecionadas = st.date_input("Filtrar Período:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    with col2:
        forns = st.multiselect("Filtrar Fornecedor:", options=df['Fornecedor'].dropna().unique(), default=df['Fornecedor'].dropna().unique())
    with col3:
        ops = st.multiselect("Filtrar Operação:", options=df['Operação'].dropna().unique(), default=df['Operação'].dropna().unique())
    with col4:
        frotas = st.multiselect("Filtrar Frota:", options=df['Frota'].dropna().unique())
        
    df_filtrado = df.copy()
    
    if isinstance(datas_selecionadas, tuple):
        if len(datas_selecionadas) == 2:
            df_filtrado = df_filtrado[(df_filtrado['Hora_alarme'].dt.date >= datas_selecionadas[0]) & (df_filtrado['Hora_alarme'].dt.date <= datas_selecionadas[1])]
        elif len(datas_selecionadas) == 1:
            df_filtrado = df_filtrado[df_filtrado['Hora_alarme'].dt.date == datas_selecionadas[0]]
        
    if forns: df_filtrado = df_filtrado[df_filtrado['Fornecedor'].isin(forns)]
    if ops: df_filtrado = df_filtrado[df_filtrado['Operação'].isin(ops)]
    if frotas: df_filtrado = df_filtrado[df_filtrado['Frota'].isin(frotas)]

    st.divider()

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
                delta_color="off"
            )

    st.divider()

    # --- FILTRO MAPA ---
    df_mapa = df_filtrado[df_filtrado['Categoria_Delay'].isin(categorias_visiveis)].copy()
    
    def aplicar_cor_dinamica(delay):
        for regra in regras_ordenadas:
            if delay <= regra['max']: return hex_to_rgb(regra['cor'])
        return hex_to_rgb(cor_critico)
            
    df_mapa['color'] = df_mapa['Delay_Minutos'].apply(aplicar_cor_dinamica)
    
    df_com_coord = df_mapa.dropna(subset=['Latitude', 'Longitude']).copy()
    
    df_com_coord['Data_Gerado'] = df_com_coord['Hora_alarme'].dt.strftime('%d/%m/%Y %H:%M:%S')
    df_com_coord['Data_Chegada'] = df_com_coord['Hora_chegada_alarme'].dt.strftime('%d/%m/%Y %H:%M:%S')

    st.success(f"Mostrando no mapa: {len(df_com_coord)} eventos com coordenadas válidas. (Total na tabela: {len(df_mapa)})")

    # --- MAPA INTERATIVO (Com Satélite Híbrido Gratuito) ---
    st.subheader("Mapa de Áreas Críticas")
    
    camada_satelite = pdk.Layer(
        "TileLayer",
        data="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        min_zoom=0,
        max_zoom=19,
        tile_size=256,
    )
    
    camada_bolhas = pdk.Layer(
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
        get_radius="Delay_Minutos",
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
        layers=[camada_satelite, camada_bolhas],
        initial_view_state=view_state,
        tooltip={"text": "Fornecedor: {Fornecedor}\nFrota: {Frota}\nOperação: {Operação}\nFaixa: {Categoria_Delay}\nDelay: {Delay_Minutos} min\nGerado em: {Data_Gerado}\nChegou em: {Data_Chegada}"},
        map_style=None,
    )

    st.pydeck_chart(r)

    # --- NOVAS TABELAS: RANKING DE VEÍCULOS E EVENTOS ---
    st.divider()
    st.subheader("📊 Ranking de Criticidade: Veículos e Eventos")
    
    cat_critica = todas_categorias[-1]
    col_rank_veic, col_rank_ev = st.columns(2)
    
    with col_rank_veic:
        st.markdown("**🚛 Veículos (Do Mais Crítico ao Mais Estável)**")
        if not df_filtrado.empty:
            rank_veiculos = df_filtrado.groupby(['Frota', 'Operação', 'Fornecedor'], as_index=False).agg(
                Total_Eventos=('Delay_Minutos', 'count'),
                Qtd_Criticos=('Categoria_Delay', lambda x: (x == cat_critica).sum()),
                Media_Delay_Min=('Delay_Minutos', 'mean'),
                Maior_Delay_Min=('Delay_Minutos', 'max')
            )
            rank_veiculos['Pct_Critico'] = (rank_veiculos['Qtd_Criticos'] / rank_veiculos['Total_Eventos'] * 100).round(1)
            rank_veiculos['Media_Delay_Min'] = rank_veiculos['Media_Delay_Min'].round(1)
            
            rank_veiculos = rank_veiculos.sort_values(
                by=['Qtd_Criticos', 'Pct_Critico', 'Media_Delay_Min'], 
                ascending=[False, False, False]
            )
            
            st.dataframe(
                rank_veiculos,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Pct_Critico": st.column_config.ProgressColumn(
                        "% Crítico",
                        help="Porcentagem de eventos na faixa crítica",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Total_Eventos": "Total",
                    "Qtd_Criticos": "Críticos",
                    "Media_Delay_Min": "Média (min)",
                    "Maior_Delay_Min": "Máx (min)"
                }
            )
        else:
            st.info("Sem dados para exibir.")

    with col_rank_ev:
        st.markdown("**⚠️ Tipos de Evento (Do Mais Crítico ao Mais Estável)**")
        if not df_filtrado.empty:
            rank_eventos = df_filtrado.groupby(['Evento', 'Fornecedor'], as_index=False).agg(
                Total_Eventos=('Delay_Minutos', 'count'),
                Qtd_Criticos=('Categoria_Delay', lambda x: (x == cat_critica).sum()),
                Media_Delay_Min=('Delay_Minutos', 'mean'),
                Maior_Delay_Min=('Delay_Minutos', 'max')
            )
            rank_eventos['Pct_Critico'] = (rank_eventos['Qtd_Criticos'] / rank_eventos['Total_Eventos'] * 100).round(1)
            rank_eventos['Media_Delay_Min'] = rank_eventos['Media_Delay_Min'].round(1)
            
            rank_eventos = rank_eventos.sort_values(
                by=['Qtd_Criticos', 'Pct_Critico', 'Media_Delay_Min'], 
                ascending=[False, False, False]
            )
            
            st.dataframe(
                rank_eventos,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Pct_Critico": st.column_config.ProgressColumn(
                        "% Crítico",
                        help="Porcentagem de eventos na faixa crítica",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Total_Eventos": "Total",
                    "Qtd_Criticos": "Críticos",
                    "Media_Delay_Min": "Média (min)",
                    "Maior_Delay_Min": "Máx (min)"
                }
            )
        else:
            st.info("Sem dados para exibir.")

    # --- TABELA DE DADOS GERAIS ---
    st.divider()
    st.subheader("📋 Registro Geral de Eventos (Filtrados pelo Mapa)")
    df_tabela = df_mapa[['Fornecedor', 'Operação', 'Frota', 'Evento', 'Hora_alarme', 'Hora_chegada_alarme', 'Categoria_Delay', 'Delay_Minutos', 'Delay_Horas', 'Delay_Dias', 'Latitude', 'Longitude']].copy()
    
    df_tabela['Hora_alarme'] = df_tabela['Hora_alarme'].dt.strftime('%d/%m/%Y %H:%M:%S')
    df_tabela['Hora_chegada_alarme'] = df_tabela['Hora_chegada_alarme'].dt.strftime('%d/%m/%Y %H:%M:%S')
    
    st.dataframe(df_tabela.sort_values('Delay_Minutos', ascending=False), use_container_width=True)
else:
    st.info("Aguardando upload da(s) planilha(s)...")