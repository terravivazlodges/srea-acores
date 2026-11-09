import streamlit as st
import pandas as pd
import re

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
st.write("Arraste qualquer ficheiro de exportação (**Smoobu, Booking.com ou Airbnb** em formato CSV, XLS ou XLSX).")

uploaded_file = st.file_uploader("Selecione o ficheiro de reservas", type=["csv", "xls", "xlsx"])

# Dicionário robusto de códigos ISO e termos geográficos para deteção inteligente
MAPA_PAISES_ISO = {
    'PT': 'Portugal', 'DE': 'Alemanha', 'FR': 'França', 'ES': 'Espanha', 
    'NL': 'Países Baixos(Holanda)', 'GB': 'Reino Unido', 'UK': 'Reino Unido', 
    'US': 'Estados Unidos da América', 'CA': 'Canadá', 'CH': 'Suíça', 
    'IT': 'Itália', 'BE': 'Bélgica', 'AT': 'Áustria', 'SE': 'Suécia', 
    'DK': 'Dinamarca', 'NO': 'Noruega', 'FI': 'Finlândia', 'IE': 'Irlanda', 
    'PL': 'Polónia', 'CZ': 'República Checa', 'BR': 'Brasil', 'CY': 'Chipre'
}

if uploaded_file is not None:
    try:
        filename = uploaded_file.name.lower()
        
        # Leitura universal com tratamento robusto de formatos
        if filename.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig')
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=',', encoding='utf-8-sig')
        else:
            # Tenta ler com openpyxl (funciona para xlsx e muitos xls salvos em formato moderno). 
            # Se falhar por ser um .xls antigo, dá fallback automático ou avisa de forma amigável.
            try:
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            except Exception:
                try:
                    df = pd.read_excel(uploaded_file, engine='xlrd')
                except Exception as e_xlrd:
                    st.error(f"Erro ao ler o ficheiro Excel. Se for um ficheiro .xls antigo, certifique-se de que a biblioteca 'xlrd' está incluída no seu requirements.txt. Detalhe: {e_xlrd}")
                    st.stop()

        # Normalização genérica de colunas para acomodar Booking, Airbnb e Smoobu
        def encontrar_coluna(opcoes):
            for op in opcoes:
                for col in df.columns:
                    if op in col.lower():
                        return col
            return None

        col_preco = encontrar_coluna(['preço', 'price', 'total', 'valor'])
        col_alojamento = encontrar_coluna(['alojamento', 'tipo de unidade', 'listing', 'property', 'room', 'quarto'])
        col_noites = encontrar_coluna(['noites', 'duração', 'nights'])
        col_adultos = encontrar_coluna(['adultos', 'adults'])
        col_criancas = encontrar_coluna(['crianças', 'children', 'kids'])
        col_estado = encontrar_coluna(['estado', 'status'])
        
        # Criação de colunas normalizadas para processamento seguro
        df['Alojamento_Norm'] = df[col_alojamento].astype(str) if col_alojamento else "Geral"
        df['Noites_Norm'] = df[col_noites].fillna(1).astype(int) if col_noites else 1
        df['Adultos_Norm'] = df[col_adultos].fillna(1).astype(int) if col_adultos else 1
        df['Criancas_Norm'] = df[col_criancas].fillna(0).astype(int) if col_criancas else 0

        # Filtrar apenas reservas ativas/confirmadas se a coluna de estado existir
        if col_estado:
            df = df[~df[col_estado].astype(str).str.lower().str.contains('cancel|recusada|declined', na=False)].copy()

        # Limpeza universal do preço
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

        # Extração de taxa turística nas notas/comentários
        col_notas = encontrar_coluna(['nota', 'comentário', 'comment', 'note', 'instruction'])
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

        # --- MOTOR INTELIGENTE DE DETEÇÃO DE NACIONALIDADE ---
        def detetar_nacionalidade_inteligente(row):
            # 1. Verificar colunas diretas de país
            for col in df.columns:
                if any(k in col.lower() for k in ['country', 'país', 'pais', 'nacionalidade']):
                    val = str(row[col]).strip().upper()
                    if val in MAPA_PAISES_ISO:
                        return MAPA_PAISES_ISO[val]
                    if len(val) == 2 and val in MAPA_PAISES_ISO:
                        return MAPA_PAISES_ISO[val]
                    if val and val != 'NAN' and len(val) > 2:
                        return val.title()

            # 2. Varrimento inteligente de todo o texto da linha
            texto_completo = " ".join([str(val) for val in row.values if pd.notna(val)]).upper()

            if any(k in texto_completo for k in ['+31', '0031', '.NL', 'NETHERLANDS', 'HOLANDA', 'PAÍSES BAIXOS']):
                return 'Países Baixos(Holanda)'
            if any(k in texto_completo for k in ['+55', 'BRASIL', 'BRA ']):
                return 'Brasil'
            if any(k in texto_completo for k in ['+41', 'SUIÇA', 'SUIZA', 'CHE']):
                return 'Suíça'
            if any(k in texto_completo for k in ['+1 ', 'ESTADOS UNIDOS', 'USA', '.US']):
                return 'Estados Unidos da América'
            if any(k in texto_completo for k in ['+33', 'FRANÇA', 'FRANCE', 'FRA ']):
                return 'França'
            if any(k in texto_completo for k in ['+44', 'REINO UNIDO', 'UK', 'GBR', '.UK']):
                return 'Reino Unido'
            if any(k in texto_completo for k in ['+49', 'ALEMANHA', 'GERMANY', 'DEU', '.DE']):
                return 'Alemanha'
            if any(k in texto_completo for k in ['+34', 'ESPANHA', 'SPAIN', '.ES']):
                return 'Espanha'
            if any(k in texto_completo for k in ['+39', 'ITÁLIA', 'ITALIA', '.IT']):
                return 'Itália'
            if any(k in texto_completo for k in ['+46', 'SUÉCIA', 'SUECIA', 'SWEDEN']):
                return 'Suécia'
            if any(k in texto_completo for k in ['+43', 'ÁUSTRIA', 'AUSTRIA']):
                return 'Áustria'
            if any(k in texto_completo for k in ['+351', 'PORTUGAL', 'PRT ', '.PT']):
                return 'Portugal'

            return 'Portugal' # Fallback predefinido

        df['Pais'] = df.apply(detetar_nacionalidade_inteligente, axis=1)

        # Divisão por Unidades Terra Vivaz
        df_rc = df[df['Alojamento_Norm'].str.contains('RC|Ribeira|Suite|Green|Blue|Garden', case=False, na=False)].copy()
        df_pb = df[df['Alojamento_Norm'].str.contains('Porto|Bay|Villa', case=False, na=False)].copy()
        
        if len(df_rc) == 0 and len(df_pb) == 0:
            df_rc = df.copy()

        rc_reservas = len(df_rc)
        rc_hospedes = int(df_rc['Hospedes'].sum())
        rc_dormidas = int(df_rc['Dormidas'].sum())
        rc_noites = int(df_rc['Noites_Norm'].sum())
        rc_rendimento = int(round(df_rc['Preço_Liquido'].sum()))

        pb_reservas = len(df_pb)
        pb_hospedes = int(df_pb['Hospedes'].sum())
        pb_dormidas = int(df_pb['Dormidas'].sum())
        pb_noites = int(df_pb['Noites_Norm'].sum())
        pb_rendimento = int(round(df_pb['Preço_Liquido'].sum()))

        st.success(f"Ficheiro processado com sucesso! Total de {len(df)} reservas analisadas inteligentemente.")
        
        st.markdown("---")
        st.subheader("📋 Quadro 1 (Permanência por País) e Totais para o SREA")

        def gerar_bloco_unidade(nome_unidade, id_unidade, num_res, hospedes, dormidas, noites, rendimento, sub_df, var_noites):
            if num_res == 0:
                return f"UNIDADE: {nome_unidade} (ID {id_unidade} — Sem reservas neste ficheiro)"
                
            linhas = [
                f"UNIDADE: {nome_unidade} (ID {id_unidade} — {num_res} Reservas)",
                f"  -> Totais Gerais: Hóspedes: {hospedes} | Dormidas: {dormidas}",
                f"  -> Noites ({var_noites}): {noites} | Rendimento (V150/V151): {rendimento:,} €",
                f"  -> Quadro 1 (Permanência por País):"
            ]
            
            agrupado = sub_df.groupby('Pais').agg(
                hospedes_entraram=('Hospedes', 'sum'),
                dormidas=('Dormidas', 'sum')
            ).reset_index()
            
            for _, row in agrupado.iterrows():
                he = int(row['hospedes_entraram'])
                hd = he 
                dor = int(row['dormidas'])
                linhas.append(f"     [País] {row['Pais']}")
                linhas.append(f"        - Nº Hóspedes entram no mês: {he}")
                linhas.append(f"        - Nº Hóspedes dormem no mês a): {hd}")
                linhas.append(f"        - Nº de Dormidas (Hóspedes x Noites): {dor}")
                
            return "\n".join(linhas)

        rc_bloco = gerar_bloco_unidade("Casa da Ribeira Cottage", "1998", rc_reservas, rc_hospedes, rc_dormidas, rc_noites, rc_rendimento, df_rc, "V103")
        pb_bloco = gerar_bloco_unidade("Porto Bay Villa", "3836", pb_reservas, pb_hospedes, pb_dormidas, pb_noites, pb_rendimento, df_pb, "V120")

        relatorio_texto = rc_bloco + ("\n\n" + "="*50 + "\n\n" + pb_bloco if pb_reservas > 0 else "")

        st.markdown(f'<div class="report-box">{relatorio_texto}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Descarregar Relatório Completo em Texto",
            data=relatorio_texto,
            file_name="relatorio_srea_quadro1.txt",
            mime="text/plain"
        )

    except Exception as e:
        st.error(f"Erro ao processar o ficheiro: {e}")
