import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="SREA Açores - Smoobu Converter", page_icon="📊", layout="centered")

st.title("📊 SREA Açores — Conversor Smoobu")
st.write("Arraste o ficheiro **CSV de reservas exportado do Smoobu** para gerar automaticamente o relatório JSON estatístico oficial.")

uploaded_file = st.file_uploader("Selecione o ficheiro CSV (.csv)", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig')
        
        df['Preço_Clean'] = df['Preço'].astype(str).str.replace('€','', regex=False).str.replace(',','.', regex=False).str.strip().astype(float)
        df['Hospedes'] = df['Adultos'].fillna(0) + df['Crianças'].fillna(0)
        df['Dormidas'] = df['Hospedes'] * df['Número de noites']

        df_rc = df[df['Alojamento'].str.contains('RC|Ribeira|Suite|Green|Blue|Garden', case=False, na=False)]
        df_pb = df[df['Alojamento'].str.contains('Porto|Bay|Villa', case=False, na=False)]

        def extrair_pais_txt(texto):
            t = str(texto).upper()
            mapa = {
                'CZ': 'República Checa', 'CH': 'Suiça', 'DE': 'Alemanha', 'FR': 'França',
                'ES': 'Espanha', 'IT': 'Itália', 'GB': 'Reino Unido', 'UK': 'Reino Unido',
                'US': 'Estados Unidos da América', 'USA': 'Estados Unidos da América',
                'CA': 'Canadá', 'NL': 'Países Baixos(Holanda)', 'BE': 'Bélgica', 'PT': 'Portugal'
            }
            for k, v in mapa.items():
                if k in t: return v
            return 'Portugal'

        df['Pais_Nome'] = df.apply(lambda row: extrair_pais_txt(str(row.get('Endereço','')) + ' ' + str(row.get('Notas',''))), axis=1)

        def gerar_q1(sub_df):
            res = {}
            for pais, group in sub_df.groupby('Pais_Nome'):
                h = int(group['Hospedes'].sum())
                d = int(group['Dormidas'].sum())
                res[pais] = {"hospedesEntraram": h, "hospedesDormiram": h, "dormidas": d}
            return res

        relatorio = {
          "unidadesEstatisticas": {
            "1998_Casa_da_Ribeira_Cottage": {
              "idSREA": "1998",
              "nome": "Casa da Ribeira Cottage (Suites RC)",
              "diasAberturaBC107": 31,
              "quadro1_permanenciaHospedes": gerar_q1(df_rc),
              "quadro2_totais": {
                "totalHospedesEntraram": int(df_rc['Hospedes'].sum()),
                "totalDormidas": int(df_rc['Dormidas'].sum()),
                "totalNoitesUtilizacao_V103": int(df_rc['Número de noites'].sum())
              },
              "quadro2_3_rendimentos": {
                "V150_rendimentoTotalEUR": int(round(df_rc['Preço_Clean'].sum())),
                "V151_reditosAposentoEUR": int(round(df_rc['Preço_Clean'].sum())),
                "V152_reditosRestauracaoEUR": 0
              }
            },
            "3836_Porto_Bay_Villa": {
              "idSREA": "3836",
              "nome": "Porto Bay Villa",
              "diasAberturaBC107": 31,
              "quadro1_permanenciaHospedes": gerar_q1(df_pb),
              "quadro2_totais": {
                "totalHospedesEntraram": int(df_pb['Hospedes'].sum()),
                "totalDormidas": int(df_pb['Dormidas'].sum()),
                "totalNoitesUtilizacao_V120": int(df_pb['Número de noites'].sum())
              },
              "quadro2_3_rendimentos": {
                "V150_rendimentoTotalEUR": int(round(df_pb['Preço_Clean'].sum())),
                "V151_reditosAposentoEUR": int(round(df_pb['Preço_Clean'].sum())),
                "V152_reditosRestauracaoEUR": 0
              }
            }
          }
        }

        st.success(f"Ficheiro processado com sucesso! Encontradas **{len(df)} reservas** no total.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Casa da Ribeira (ID 1998)", f"{len(df_rc)} reservas", f"{int(round(df_rc['Preço_Clean'].sum()))} €")
        with col2:
            st.metric("Porto Bay Villa (ID 3836)", f"{len(df_pb)} reservas", f"{int(round(df_pb['Preço_Clean'].sum()))} €")

        json_str = json.dumps(relatorio, indent=2, ensure_ascii=False)
        
        st.subheader("Resultado JSON (Pronto para o SREA)")
        st.code(json_str, language='json')
        
        st.download_button(
            label="📥 Descarregar Ficheiro JSON",
            data=json_str,
            file_name="relatorio_srea.json",
            mime="application/json"
        )

    except Exception as e:
        st.error(f"Erro ao processar o ficheiro: {e}")
