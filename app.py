import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="SREA Açores - Resumo Estatístico", page_icon="📊", layout="centered")

st.markdown("""
    <style>
    .report-box {
        background-color: #0e1117;
        border: 1px solid #262730;
        padding: 20px;
        border-radius: 10px;
        color: #fafafa;
        font-family: monospace;
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 14px;
        line-height: 1.5;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 SREA Açores — Resumo Estatístico Inteligente")
st.write("Pode carregar **vários ficheiros em simultâneo** (Booking.com, Airbnb, Smoobu em formato CSV, XLS ou XLSX).")

uploaded_files = st.file_uploader("Selecione os ficheiros de reservas", type=["csv", "xls", "xlsx"], accept_multiple_files=True)

MAPA_PAISES_ISO = {
    'PT': 'Portugal', 'DE': 'Alemanha', 'FR': 'França', 'ES': 'Espanha', 
    'NL': 'Países Baixos(Holanda)', 'GB': 'Reino Unido', 'UK': 'Reino Unido', 
    'US': 'Estados Unidos da América', 'CA': 'Canadá', 'CH': 'Suíça', 
    'IT': 'Itália', 'BE': 'Bélgica', 'AT': 'Áustria', 'SE': 'Suécia', 
    'DK': 'Dinamarca', 'NO': 'Noruega', 'FI': 'Finlândia', 'IE': 'Irlanda', 
    'PL': 'Polónia', 'CZ': 'República Checa', 'BR': 'Brasil', 'CY': 'Chipre',
    'IL': 'Israel'
}

if uploaded_files:
    try:
        lista_dfs = []
        
        for uploaded_file in uploaded_files:
            filename = uploaded_file.name.lower()
            if filename.endswith('.csv'):
                try:
                    temp_df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', on_bad_lines='skip')
                    if len(temp_df.columns) <= 1:
                        uploaded_file.seek(0)
                        temp_df = pd.read_csv(uploaded_file, sep=',', encoding='latin-1', on_bad_lines='skip')
                except:
                    uploaded_file.seek(0)
                    temp_df = pd.read_csv(uploaded_file, sep=',', encoding='latin-1', on_bad_lines='skip')
            else:
                try:
                    temp_df = pd.read_excel(uploaded_file, engine='openpyxl')
                except Exception:
                    try:
                        temp_df = pd.read_excel(uploaded_file, engine='xlrd')
                    except Exception as e_xlrd:
                        st.error(f"Erro ao ler o ficheiro Excel {uploaded_file.name}: {e_xlrd}")
                        continue
            
            lista_dfs.append(temp_df)
        
        if not lista_dfs:
            st.stop()
            
        df = pd.concat(lista_dfs, ignore_index=True)

        def encontrar_coluna(opcoes):
            for op in opcoes:
                for col in df.columns:
                    if op in col.lower():
                        return col
            return None

        col_preco = encontrar_coluna(['preço', 'price', 'total', 'valor', 'earnings'])
        col_alojamento = encontrar_coluna(['alojamento', 'unit type', 'listing', 'property', 'room', 'quarto'])
        col_noites = encontrar_coluna(['duration (nights)', 'número de noites', 'noites', 'duração', 'nights'])
        col_adultos = encontrar_coluna(['adultos', 'adults', '# of adults', 'persons'])
        col_criancas = encontrar_coluna(['crianças', 'children', 'kids', '# of children'])
        col_estado = encontrar_coluna(['estado', 'status'])
        col_telefone = encontrar_coluna(['telefone', 'phone number', 'contact'])
        col_pais_direto = encontrar_coluna(['booker country', 'country', 'país', 'pais', 'nacionalidade'])
        
        raw_alojamento = df[col_alojamento].astype(str) if col_alojamento else "Geral"

        # --- NORMALIZAÇÃO INTELIGENTE DAS UNIDADES TERRA VIVAZ ---
        def normalizar_unidade(val):
            val_lower = str(val).lower()
            if any(k in val_lower for k in ['green', 'blue', 'garden', 'ribeira', 'suite', 'rc']):
                return "Casa da Ribeira Cottage (ID 1998)"
            elif any(k in val_lower for k in ['porto', 'bay', 'villa']):
                return "Porto Bay Villa (ID 3836)"
            return val

        df['Alojamento_Norm'] = raw_alojamento.apply(normalizar_unidade)
        
        df['Noites_Norm'] = pd.to_numeric(df[col_noites], errors='coerce').fillna(1).astype(int) if col_noites else 1
        df['Adultos_Norm'] = pd.to_numeric(df[col_adultos], errors='coerce').fillna(1).astype(int) if col_adultos else 1
        df['Criancas_Norm'] = pd.to_numeric(df[col_criancas], errors='coerce').fillna(0).astype(int) if col_criancas else 0

        # Filtrar reservas canceladas
        if col_estado:
            df = df[~df[col_estado].astype(str).str.lower().str.contains('cancel|recusada|declined', na=False)].copy()

        # Limpeza universal de preço
        if col_preco:
            df['Preço_Bruto'] = (
                df[col_preco].astype(str)
                .str.replace(r'[^0-9,\.]', '', regex=True)
                .str.replace(',', '.', regex=False)
                .str.strip()
            )
            df['Preço_Bruto'] = pd.to_numeric(df['Preço_Bruto'], errors='coerce').fillna(0.0)
        else:
            df['Preço_Bruto'] = 0.0

        col_notas = encontrar_coluna(['nota', 'comentário', 'comment', 'note', 'instruction', 'remarks'])
        def extrair_taxa_turistica(row):
            texto = ""
            if col_notas and pd.notna(row[col_notas]):
                texto = str(row[col_notas])
            match = re.search(r'(\d+)\s*€', texto)
            if match and ('turistica' in texto.lower() or 'tx' in texto.lower()):
                return float(match.group(1))
            return 0.0

        df['Taxa_Turistica'] = df.apply(extrair_taxa_turistica, axis=1)
        df['Preço_Liquido'] = (df['Preço_Bruto'] - df['Taxa_Turistica']) / 1.04

        df['Hospedes'] = df['Adultos_Norm'] + df['Criancas_Norm']
        df['Dormidas'] = df['Hospedes'] * df['Noites_Norm']

        # Deteção inteligente de nacionalidade
        def detetar_nacionalidade_inteligente(row):
            if col_pais_direto and pd.notna(row[col_pais_direto]):
                val = str(row[col_pais_direto]).strip().upper()
                if val in MAPA_PAISES_ISO:
                    return MAPA_PAISES_ISO[val]
                if len(val) == 2 and val in MAPA_PAISES_ISO:
                    return MAPA_PAISES_ISO[val]

            if col_telefone and pd.notna(row[col_telefone]):
                tel = re.sub(r'\D', '', str(row[col_telefone]))
                if tel.startswith('55'): return 'Brasil'
                if tel.startswith('351'): return 'Portugal'
                if tel.startswith('33'): return 'França'
                if tel.startswith('44'): return 'Reino Unido'
                if tel.startswith('49'): return 'Alemanha'
                if tel.startswith('34'): return 'Espanha'
                if tel.startswith('39'): return 'Itália'
                if tel.startswith('31'): return 'Países Baixos(Holanda)'
                if tel.startswith('41'): return 'Suíça'
                if tel.startswith('1'): return 'Estados Unidos da América'
                if tel.startswith('46'): return 'Suécia'
                if tel.startswith('43'): return 'Áustria'
                if tel.startswith('972'): return 'Israel'

            texto_completo = " ".join([str(val) for val in row.values if pd.notna(val)]).upper()
            if any(k in texto_completo for k in ['+31', 'NETHERLANDS', 'HOLANDA', 'PAÍSES BAIXOS', 'GUEST LANGUAGE: NL']): return 'Países Baixos(Holanda)'
            if any(k in texto_completo for k in ['+55', 'BRASIL', 'GUEST LANGUAGE: PT']): return 'Brasil'
            if any(k in texto_completo for k in ['+41', 'SUIÇA', 'SUIZA']): return 'Suíça'
            if any(k in texto_completo for k in ['+33', 'FRANÇA', 'FRANCE', 'GUEST LANGUAGE: FR']): return 'França'
            if any(k in texto_completo for k in ['+44', 'REINO UNIDO', 'UK', 'GUEST LANGUAGE: EN']): return 'Reino Unido'
            if any(k in texto_completo for k in ['+49', 'ALEMANHA', 'GERMANY', 'GUEST LANGUAGE: DE']): return 'Alemanha'
            if any(k in texto_completo for k in ['+34', 'ESPANHA', 'SPAIN', 'GUEST LANGUAGE: ES']): return 'Espanha'
            if any(k in texto_completo for k in ['+39', 'ITÁLIA', 'ITALIA']): return 'Itália'
            if any(k in texto_completo for k in ['+351', 'PORTUGAL']): return 'Portugal'

            return 'Portugal'

        df['Pais'] = df.apply(detetar_nacionalidade_inteligente, axis=1)

        st.success(f"Ficheiros processados com sucesso! Total consolidado de {len(df)} reservas analisadas.")
        st.markdown("---")
        st.subheader("📋 Quadro 1 (Permanência por País) e Totais Consolidados por Unidade SREA")

        relatorios_blocos = []
        dados_excel = []

        for unidade_nome, sub_df in df.groupby('Alojamento_Norm'):
            num_res = len(sub_df)
            hospedes = int(sub_df['Hospedes'].sum())
            dormidas = int(sub_df['Dormidas'].sum())
            noites = int(sub_df['Noites_Norm'].sum())
            rendimento = int(round(sub_df['Preço_Liquido'].sum()))

            linhas = [
                f"UNIDADE: {unidade_nome} ({num_res} Reservas)",
                f"  -> Totais Gerais: Hóspedes: {hospedes} | Dormidas: {dormidas}",
                f"  -> Noites: {noites} | Rendimento Líquido: {rendimento:,} €",
                f"  -> Quadro 1 (Permanência por País):"
            ]

            agrupado = sub_df.groupby('Pais').agg(
                hospedes_entraram=('Hospedes', 'sum'),
                dormidas=('Dormidas', 'sum'),
                noites=('Noites_Norm', 'sum'),
                rendimento=('Preço_Liquido', 'sum')
            ).reset_index()

            for _, row in agrupado.iterrows():
                he = int(row['hospedes_entraram'])
                hd = he 
                dor = int(row['dormidas'])
                linhas.append(f"     [País] {row['Pais']}")
                linhas.append(f"        - Nº Hóspedes entram no mês: {he}")
                linhas.append(f"        - Nº Hóspedes dormem no mês a): {hd}")
                linhas.append(f"        - Nº de Dormidas (Hóspedes x Noites): {dor}")

                dados_excel.append({
                    'Unidade': unidade_nome,
                    'País': row['Pais'],
                    'Hóspedes Entram': he,
                    'Hóspedes Dormem': hd,
                    'Dormidas': dor,
                    'Noites': int(row['noites']),
                    'Rendimento Líquido (€)': round(row['rendimento'], 2)
                })

            relatorios_blocos.append("\n".join(linhas))

        relatorio_texto = "\n\n" + "="*50 + "\n\n".join(relatorios_blocos)

        st.markdown(f'<div class="report-box">{relatorio_texto}</div>', unsafe_allow_html=True)

        df_export = pd.DataFrame(dados_excel)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, sheet_name='SREA_Resumo', index=False)
        excel_data = output.getvalue()

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.download_button(
                label="📥 Descarregar Relatório Consolidado (.TXT)",
                data=relatorio_texto,
                file_name="relatorio_srea_quadro1.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col_btn2:
            st.download_button(
                label="📊 Descarregar Relatório Consolidado (.XLSX)",
                data=excel_data,
                file_name="relatorio_srea_quadro1.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Erro ao processar os ficheiros: {e}")
