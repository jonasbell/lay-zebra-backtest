import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Backtest Lay Zebra", page_icon="📊", layout="wide")

st.title("📊 Dashboard de Backtest - Lay Zebra")
st.markdown("Validação da estratégia em **partidas históricas reais** com gestão de banca, unidades e gráfico de evolução financeira.")

# Sidebar - Parâmetros da Gestão de Banca & Unidade
st.sidebar.header("💰 Gestão de Banca & Unidade")
valor_unidade = st.sidebar.number_input("Valor por Unidade (R$ / €)", value=50.00, step=10.00, min_value=1.00)

st.sidebar.header("🎯 Parâmetros da Estratégia")
odd_min_zebra = st.sidebar.number_input("Odd Mínima Zebra (Visitante)", value=4.00, step=0.10)
odd_max_zebra = st.sidebar.number_input("Odd Máxima Zebra (Visitante)", value=8.00, step=0.10)
taxa_vitoria_min = st.sidebar.slider("% Mínima Vitórias Mandante em Casa", min_value=50, max_value=100, value=70)
amostragem_min_jogos = st.sidebar.number_input("Mínimo de Jogos Anteriores em Casa", value=5, step=1)

st.sidebar.subheader("🌍 Ligas & Temporadas")
temporada = st.sidebar.selectbox("Temporada Histórica", ["2324", "2223", "2122"])

LIGAS = {
    "Premier League (Inglaterra)": "E0",
    "La Liga (Espanha)": "SP1",
    "Serie A (Itália)": "I1",
    "Bundesliga (Alemanha)": "D1",
    "Primeira Liga (Portugal)": "P1"
}

ligas_selecionadas = st.sidebar.multiselect(
    "Selecione as Ligas", 
    list(LIGAS.keys()), 
    default=["Premier League (Inglaterra)", "La Liga (Espanha)", "Primeira Liga (Portugal)"]
)

@st.cache_data
def carregar_dados_historicos(liga_code, temp):
    url = f"https://www.football-data.co.uk/mmz4281/{temp}/{liga_code}.csv"
    try:
        df = pd.read_csv(url)
        colunas = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'B365H', 'B365D', 'B365A']
        df = df[[c for c in colunas if c in df.columns]].dropna()
        return df
    except Exception:
        return pd.DataFrame()

if st.button("🚀 Executar Backtest Histórico", type="primary"):
    with st.spinner("Analisando histórico de partidas e gerando gráfico de saldo..."):
        dados_totais = []
        
        for nome_liga in ligas_selecionadas:
            code = LIGAS[nome_liga]
            df_liga = carregar_dados_historicos(code, temporada)
            if not df_liga.empty:
                df_liga["Liga"] = nome_liga
                dados_totais.append(df_liga)
                
        if not dados_totais:
            st.error("Não foi possível carregar os dados históricos das ligas selecionadas.")
        else:
            df = pd.concat(dados_totais, ignore_index=True)
            
            entradas_validadas = []
            historico_mandantes = {}
            
            for idx, row in df.iterrows():
                m = row['HomeTeam']
                v = row['AwayTeam']
                golos_h = row['FTHG']
                golos_a = row['FTAG']
                resultado = row['FTR']
                
                try:
                    odd_m = float(row['B365H'])
                    odd_z = float(row['B365A'])
                except ValueError:
                    continue
                
                if m not in historico_mandantes:
                    historico_mandantes[m] = {'jogos': 0, 'vitorias': 0}
                    
                stats_h = historico_mandantes[m]
                
                if stats_h['jogos'] >= amostragem_min_jogos:
                    taxa_m = (stats_h['vitorias'] / stats_h['jogos']) * 100
                else:
                    taxa_m = 0.0
                    
                if (odd_min_zebra <= odd_z <= odd_max_zebra) and (taxa_m >= taxa_vitoria_min):
                    green = (resultado != 'A')
                    lucro_unidades = 1.0 if green else -(odd_z - 1.0)
                    lucro_financeiro = lucro_unidades * valor_unidade
                    
                    entradas_validadas.append({
                        "Data": row['Date'],
                        "Liga": row['Liga'],
                        "Mandante": m,
                        "Visitante": v,
                        "Odd Mandante": odd_m,
                        "Odd Zebra": odd_z,
                        "% Vitória Mandante": f"{taxa_m:.1f}%",
                        "Placar": f"{int(golos_h)} x {int(golos_a)}",
                        "Resultado Lay": "✅ GREEN" if green else "❌ RED",
                        "Lucro (u)": round(lucro_unidades, 2),
                        "Lucro Fin (R$)": lucro_financeiro
                    })
                
                historico_mandantes[m]['jogos'] += 1
                if resultado == 'H':
                    historico_mandantes[m]['vitorias'] += 1
            
            if not entradas_validadas:
                st.warning("Nenhum jogo no histórico cumpriu todos os critérios da estratégia.")
            else:
                df_res = pd.DataFrame(entradas_validadas)
                
                # Cálculo do saldo acumulado jogo a jogo
                df_res["Entrada #"] = range(1, len(df_res) + 1)
                df_res["Saldo Acumulado (R$)"] = df_res["Lucro Fin (R$)"].cumsum()
                df_res["Saldo Acumulado (u)"] = df_res["Lucro (u)"].cumsum()
                
                total_jogos = len(df_res)
                greens = len(df_res[df_res["Resultado Lay"] == "✅ GREEN"])
                reds = total_jogos - greens
                winrate = (greens / total_jogos) * 100
                lucro_unidades_total = df_res["Lucro (u)"].sum()
                lucro_financeiro_total = df_res["Lucro Fin (R$)"].sum()
                
                st.subheader("📈 Resumo do Desempenho Financeiro")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total de Entradas", total_jogos)
                c2.metric("Greens / Reds", f"{greens} / {reds}")
                c3.metric("Taxa de Acerto", f"{winrate:.1f}%")
                c4.metric("Lucro Total (u)", f"{lucro_unidades_total:.2f} u")
                c5.metric("Lucro em Dinheiro (R$)", f"R$ {lucro_financeiro_total:.2f}", delta=f"R$ {lucro_financeiro_total:.2f}")
                
                # Gráfico da evolução da banca
                st.subheader("📉 Curva de Evolução da Banca (Jogo a Jogo)")
                st.line_chart(df_res, x="Entrada #", y="Saldo Acumulado (R$)", color="#00FF7F")
                
                # Exibição dos dados formatados
                st.subheader("📋 Detalhamento de Partidas")
                df_exibicao = df_res.copy()
                df_exibicao["Lucro / Prejuízo"] = df_exibicao["Lucro Fin (R$)"].apply(
                    lambda x: f"R$ {x:.2f}" if x >= 0 else f"-R$ {abs(x):.2f}"
                )
                df_exibicao["Saldo Acumulado"] = df_exibicao["Saldo Acumulado (R$)"].apply(
                    lambda x: f"R$ {x:.2f}" if x >= 0 else f"-R$ {abs(x):.2f}"
                )
                
                colunas_finais = [
                    "Entrada #", "Data", "Liga", "Mandante", "Visitante", 
                    "Odd Zebra", "Resultado Lay", "Lucro (u)", "Lucro / Prejuízo", "Saldo Acumulado"
                ]
                st.dataframe(df_exibicao[colunas_finais], use_container_width=True)
                
