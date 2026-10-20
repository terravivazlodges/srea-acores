import streamlit as st
import pandas as pd

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

st.title("📊 SREA Açores — Resumo Estatístico Smoobu")
st.write("Arraste o ficheiro **CSV de reservas exportado do Smoobu** para obter o relatório final detalhado por país.")

uploaded_file = st.file_uploader("Selecione o ficheiro CSV (.csv)", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig')
        
        df['Preço_Clean'] = df['Preço'].astype(str).str.replace('€','', regex=False).str.replace(',','.', regex=False).str.strip().astype(float)
        df['Hospedes'] = df['Adultos'].fillna(0) + df['Crianças'].fillna(0)
        df['Dormidas'] = df['Hospedes'] * df['Número de noites']

        df_rc = df[df['Alojamento'].str.contains('RC|Ribeira|Suite|Green|Blue|Garden', case=False, na=False)].copy()
        df_pb = df[df['Alojamento'].str.contains('Porto|Bay|Villa', case=False, na=False)].copy()

        def extrair_pais(row):
            texto = " ".join([
                str(row.get('Endereço', '')),
                str(row.get('Notas', '')),
                str(row.get('Hóspede', '')),
                str(row.get('Portal', '')),
                str(row.get('Instruções do assistente', '')),
                str(row.get('Email', ''))
            ]).upper()

            mapa_paises = {
                'BRA': 'Brasil', 'BRASIL': 'Brasil', '+55': 'Brasil',
                'CHE': 'Suíça', 'CH': 'Suíça', 'SUIÇA': 'Suíça', 'SUIZA': 'Suíça', '+41': 'Suíça',
                'USA': 'Estados Unidos da América', 'US': 'Estados Unidos da América', 'ESTADOS UNIDOS': 'Estados Unidos da América', '+1': 'Estados Unidos da América',
                'FRA': 'França', 'FR': 'França', 'FRANÇA': 'França', '+33': 'França',
                'GBR': 'Reino Unido', 'UK': 'Reino Unido', 'GB': 'Reino Unido', '+44': 'Reino Unido',
                'DEU': 'Alemanha', 'DE': 'Alemanha', 'ALEMANHA': 'Alemanha', '+49': 'Alemanha',
                'ESP': 'Espanha', 'ES': 'Espanha', 'ESPANHA': 'Espanha', '+34': 'Espanha',
                'ITA': 'Itália', 'IT': 'Itália', 'ITÁLIA': 'Itália', '+39': 'Itália',
                'NLD': 'Países Baixos(Holanda)', 'NL': 'Países Baixos(Holanda)', 'HOLANDA': 'Países Baixos(Holanda)', 'NETHERLANDS': 'Países Baixos(Holanda)', '+31': 'Países Baixos(Holanda)',
                'CAN': 'Canadá', 'CA': 'Canadá',
                'ISR': 'Israel', 'IL': 'Israel', '+972': 'Israel',
                'PRT': 'Portugal', 'PORTUGAL': 'Portugal', '+351': 'Portugal'
            }

            for chave, pais in mapa_paises.items():
                if chave in texto:
                    return pais
            return 'Portugal'

        df_rc['Pais'] = df_rc.apply(extrair_pais, axis=1)
        df_pb['Pais'] = df_pb.apply(extrair_pais, axis=1)

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

        def gerar_bloco_unidade(nome_unidade, id_unidade, num_res, hospedes, dormidas, noites, rendimento, sub_df):
            linhas = [
                f"UNIDADE: {nome_unidade} (ID {id_unidade} — {num_res} Reservas)",
                f"  -> Totais Gerais: Hóspedes: {hospedes} | Dormidas: {dormidas}",
                f"  -> Noites (V103/V120): {noites} | Rendimento (V150/V151): {rendimento:,} €",
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
                linhas.append(f"       - Nº Hóspedes entram no mês: {he}")
                linhas.append(f"       - Nº Hóspedes dormem no mês a): {hd}")
                linhas.append(f"       - Nº de Dormidas (Hóspedes x Noites): {dor}")
                
            return "\n".join(linhas)

        rc_bloco = gerar_bloco_unidade("Casa da Ribeira Cottage", "1998", rc_reservas, rc_hospedes, rc_dormidas, rc_noites, rc_rendimento, df_rc)
        pb_bloco = gerar_bloco_unidade("Porto Bay Villa", "3836", pb_reservas, pb_hospedes, pb_dormidas, pb_noites, pb_rendimento, df_pb)

        relatorio_texto = f"{rc_bloco}\n\n{'='*50}\n\n{pb_bloco}"

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
