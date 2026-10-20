import streamlit as st
import pandas as pd

st.set_page_config(page_title="SREA Açores - Resumo Estatístico", page_icon="📊", layout="centered")

st.title("📊 SREA Açores — Resumo Estatístico Smoobu")
st.write("Arraste o ficheiro **CSV de reservas exportado do Smoobu** para obter o relatório final formatado.")

uploaded_file = st.file_uploader("Selecione o ficheiro CSV (.csv)", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig')
        
        df['Preço_Clean'] = df['Preço'].astype(str).str.replace('€','', regex=False).str.replace(',','.', regex=False).str.strip().astype(float)
        df['Hospedes'] = df['Adultos'].fillna(0) + df['Crianças'].fillna(0)
        df['Dormidas'] = df['Hospedes'] * df['Número de noites']

        df_rc = df[df['Alojamento'].str.contains('RC|Ribeira|Suite|Green|Blue|Garden', case=False, na=False)]
        df_pb = df[df['Alojamento'].str.contains('Porto|Bay|Villa', case=False, na=False)]

        # Cálculos Casa da Ribeira
        rc_reservas = len(df_rc)
        rc_hospedes = int(df_rc['Hospedes'].sum())
        rc_dormidas = int(df_rc['Dormidas'].sum())
        rc_noites = int(df_rc['Número de noites'].sum())
        rc_rendimento = int(round(df_rc['Preço_Clean'].sum()))

        # Cálculos Porto Bay Villa
        pb_reservas = len(df_pb)
        pb_hospedes = int(df_pb['Hospedes'].sum())
        pb_dormidas = int(df_pb['Dormidas'].sum())
        pb_noites = int(df_pb['Número de noites'].sum())
        pb_rendimento = int(round(df_pb['Preço_Clean'].sum()))

        # Mensagem de sucesso personalizada com contagens separadas
        st.success(f"Ficheiro processado com sucesso! Total de {rc_reservas} reservas para Casa da Ribeira e {pb_reservas} reservas para Porto Bay Villa.")
        
        st.markdown("---")
        st.subheader("📋 Relatório Final para o SREA")

        # Texto formatado limpo
        relatorio_texto = f"""- Casa da Ribeira Cottage (ID 1998 — {rc_reservas} Reservas):
  - Total Hóspedes: {rc_hospedes}
  - Total Dormidas: {rc_dormidas}
  - Noites de Utilização (V103): {rc_noites}
  - Rendimento Total (V150/V151): {rc_rendimento:,} €
- Porto Bay Villa (ID 3836 — {pb_reservas} Reservas):
  - Total Hóspedes: {pb_hospedes}
  - Total Dormidas: {pb_dormidas}
  - Noites de Utilização (V120): {pb_noites}
  - Rendimento Total (V150/V151): {pb_rendimento:,} €"""

        st.code(relatorio_texto, language="markdown")

        st.download_button(
            label="📥 Descarregar Relatório em Texto",
            data=relatorio_texto,
            file_name="relatorio_srea_resumo.txt",
            mime="text/plain"
        )

    except Exception as e:
        st.error(f"Erro ao processar o ficheiro: {e}")
