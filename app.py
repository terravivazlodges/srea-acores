import streamlit as st
import pandas as pd

st.set_page_config(page_title="SREA Açores - Resumo Estatístico", page_icon="📊", layout="centered")

st.title("📊 SREA Açores — Resumo Estatístico Smoobu")
st.write("Arraste o ficheiro **CSV de reservas exportado do Smoobu** para obter o relatório final detalhado por país.")

uploaded_file = st.file_uploader("Selecione o ficheiro CSV (.csv)", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig')
        
        df['Preço_Clean'] = df['Preço'].astype(str).str.replace('€','', regex=False).str.replace(',','.', regex=False).str.strip().astype(float)
        df['Hospedes'] = df['Adultos'].fillna(0) + df['Crianças'].fillna(0)
        df['Dormidas'] = df['Hospedes'] * df['Número de noites']

        # Separação por unidade
        df_rc = df[df['Alojamento'].str.contains('RC|Ribeira|Suite|Green|Blue|Garden', case=False, na=False)].copy()
        df_pb = df[df['Alojamento'].str.contains('Porto|Bay|Villa', case=False, na=False)].copy()

        # Detetar o país com base nas colunas Endereço / Notas / Hóspede
        def extrair_pais(row):
            texto = f"{str(row.get('Endereço',''))} {str(row.get('Notas',''))} {str(row.get('Hóspede',''))}".upper()
            mapa = {
                'BRA': 'Brasil', 'BRASIL': 'Brasil',
                'CHE': 'Suíça', 'CH': 'Suíça', 'SUIÇA': 'Suíça', 'SUIZA': 'Suíça',
                'USA': 'Estados Unidos da América', 'US': 'Estados Unidos da América', 'ESTADOS UNIDOS': 'Estados Unidos da América',
                'FRA': 'França', 'FR': 'França',
                'GBR': 'Reino Unido', 'UK': 'Reino Unido', 'GB': 'Reino Unido',
                'DEU': 'Alemanha', 'DE': 'Alemanha', 'ALEMANHA': 'Alemanha',
                'ESP': 'Espanha', 'ES': 'Espanha', 'ESPANHA': 'Espanha',
                'ITA': 'Itália', 'IT': 'Itália', 'ITÁLIA': 'Itália',
                'NLD': 'Países Baixos(Holanda)', 'NL': 'Países Baixos(Holanda)', 'HOLANDA': 'Países Baixos(Holanda)',
                'CAN': 'Canadá', 'CA': 'Canadá',
                'ISR': 'Israel', 'IL': 'Israel'
            }
            for k, v in mapa.items():
                if k in texto:
                    return v
            return 'Portugal'

        df_rc['Pais'] = df_rc.apply(extrair_pais, axis=1)
        df_pb['Pais'] = df_pb.apply(extrair_pais, axis=1)

        # Totais gerais
        rc_reservas = len(df_rc)
        rc_hospedes = int(df_rc['Hospedes'].sum())
        rc_dormidas = int(df_rc['Dormidas'].sum())
        rc_noites = int(df_rc['Número de noites'].sum())
        rc_rendimento = int(round(df_rc['Preço_Clean'].sum()))

        pb_reservas = len(df_pb)
        pb_hospedes = int(df_pb['Hospedes'].sum())
        pb_dormidas = int(df_pb['Dormidas'].sum())
        pb_noites = int(df_pb['Número de noites'].sum())
        pb_rendimento = int(round(df_pb['Preço_Clean'].sum()))

        st.success(f"Ficheiro processado com sucesso! Total de {rc_reservas} reservas para Casa da Ribeira e {pb_reservas} reservas para Porto Bay Villa.")
        
        st.markdown("---")
        st.subheader("📋 Quadro 1 (Permanência por País) e Totais para o SREA")

        # Função para gerar as linhas exatamente com as 3 colunas do SREA
        def gerar_linhas_quadro1(sub_df):
            agrupado = sub_df.groupby('Pais').agg(
                hospedes_entraram=('Hospedes', 'sum'),
                dormidas=('Dormidas', 'sum')
            ).reset_index()
            
            linhas = []
            for _, row in agrupado.iterrows():
                he = int(row['hospedes_entraram'])
                hd = he # Hóspedes que dormiram (igual aos que entraram por predefinição)
                dor = int(row['dormidas'])
                linhas.append(f"  - {row['Pais']}:\n      - Nº Hóspedes entram: {he}\n      - Nº Hóspedes dormem: {hd}\n      - Nº Dormidas: {dor}")
            return "\n".join(linhas)

        rc_q1_txt = gerar_linhas_quadro1(df_rc)
        pb_q1_txt = gerar_linhas_quadro1(df_pb)

        # Texto estruturado final
        relatorio_texto = f"""- Casa da Ribeira Cottage (ID 1998 — {rc_reservas} Reservas):
  - Totais Gerais: Hóspedes: {rc_hospedes} | Dormidas: {rc_dormidas} | Noites (V103): {rc_noites} | Rendimento (V150/V151): {rc_rendimento:,} €
  - Quadro 1 (Permanência por País):
{rc_q1_txt}

- Porto Bay Villa (ID 3836 — {pb_reservas} Reservas):
  - Totais Gerais: Hóspedes: {pb_hospedes} | Dormidas: {pb_dormidas} | Noites (V120): {pb_noites} | Rendimento (V150/V151): {pb_rendimento:,} €
  - Quadro 1 (Permanência por País):
{pb_q1_txt}"""

        st.code(relatorio_texto, language="markdown")

        st.download_button(
            label="📥 Descarregar Relatório Completo em Texto",
            data=relatorio_texto,
            file_name="relatorio_srea_quadro1.txt",
            mime="text/plain"
        )

    except Exception as e:
        st.error(f"Erro ao processar o ficheiro: {e}")
