import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Backtest Lay Zebra", page_icon="📊", layout="wide")

st.title("📊 Dashboard de Backtest - Estratégia Lay Zebra")
st.markdown("Validação da estratégia em **partidas históricas reais** com odds de mercado da Bet365 e Pinnacle.")

# Sidebar - Parâmetros do Backtest
st.sidebar.header("🎯 Parâmetros da Estratégia")
odd_min_zebra = st.sidebar.number_input("Odd Mínima Zebra (Visitante)", value=4.00, step=0.10)
odd_max_zebra = st.sidebar.number_input("Odd Máxima Zebra (Visitante)", value=8.00, step=0.10)
taxa_vitoria_min = st.sidebar.slider("% Mínima Vitórias Mandante em Casa", min_value=50, max_value=100, value=70)
amostragem_min_jogos = st.sidebar.number_input("Mínimo de Jogos Anteriores em Casa", value=5, step=1)

st.sidebar.subheader("🌍 Ligas para Testar")
temporada = st.sidebar.selectbox("Temporada Histórica", ["2324", "2223", "2122"])

LIGAS = {
    "Premier League (Inglaterra)": "E0",
    "La Liga (Espanha)": "SP1",
    "Serie A (Itália)": "I1",
    "Bundesliga (Alemanha)": "D1",
    "Primeira Liga (Portugal)": "P1"
}

ligas_selecionadas = st.sidebar.multiselect("Selecione as Ligas", list(LIGAS.keys()), default=["Premier League (Inglaterra)", "La Liga (Espanha)", "Primeira Liga (Portugal)"])

@st.cache_data
def carregar_dados_historicos(liga_code, temp):
    url = f"https://www.football-data.co.uk/mmz4281/{temp}/{liga_code}.csv"
    try:
        df = pd.read_csv(url)
        # Seleciona apenas colunas essenciais: Data, Mandante, Visitante, Golos, Odds Bet365 (B365H, B365D, B365A)
        colunas = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'B365H', 'B365D', 'B365A']
        df = df[[c for c in colunas if c in df.columns]].dropna()
        return df
    except Exception:
        return pd.DataFrame()

if st.button("🚀 Executar Backtest Histórico", type="primary"):
    with st.spinner("Descarregando histórico de partidas e calculando estatísticas..."):
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
            
            # Estrutura de análise retrospectiva
            entradas_validadas = []
            historico_mandantes = {}
            
            for idx, row in df.iterrows():
                m = row['HomeTeam']
                v = row['AwayTeam']
                golos_h = row['FTHG']
                golos_a = row['FTAG']
                resultado = row['FTR'] # 'H' = Home, 'D' = Draw, 'A' = Away
                
                odd_m = float(row['B365H'])
                odd_e = float(row['B365D'])
                odd_z = float(row['B365A']) # Zebra (Visitante)
                
                # Inicializa histórico do mandante se não existir
                if m not in historico_mandantes:
                    historico_mandantes[m] = {'jogos': 0, 'vitorias': 0}
                    
                stats_h = historico_mandantes[m]
                
                # Calcula taxa do mandante antes desta partida
                if stats_h['jogos'] >= amostragem_min_jogos:
                    taxa_m = (stats_h['vitorias'] / stats_h['jogos']) * 100
                else:
                    taxa_m = 0.0
                    
                # Condição de validação da estratégia Lay Zebra
                if (odd_min_zebra <= odd_z <= odd_max_zebra) and (taxa_m >= taxa_vitoria_min):
                    # No Lay Zebra (Apostar contra a Zebra), ganhamos se der Mandante (H) ou Empate (D)
                    green = (resultado != 'A')
                    lucro = 1.0 if green else -(odd_z - 1.0) # Modelo padrão de Lay
                    
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
                        "Lucro (Unidades)": round(lucro, 2)
                    })
                
                # Atualiza o histórico do mandante para os próximos jogos
                historico_mandantes[m]['jogos'] += 1
                if resultado == 'H':
                    historico_mandantes[m]['vitorias'] += 1
            
            if not entradas_validadas:
                st.warning("Nenhum jogo no histórico cumpriu todos os critérios da estratégia com os parâmetros selecionados.")
            else:
                df_res = pd.DataFrame(entradas_validadas)
                
                total_jogos = len(df_res)
                greens = len(df_res[df_res["Resultado Lay"] == "✅ GREEN"])
                reds = total_jogos - greens
                winrate = (greens / total_jogos) * 100
                lucro_total = df_res["Lucro (Unidades)"].sum()
                
                st.subheader("📈 Resumo dos Resultados do Backtest")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total de Entradas", total_jogos)
                c2.metric("Greens / Reds", f"{greens} / {reds}")
                c3.metric("Taxa de Acerto", f"{winrate:.1f}%")
                c4.metric("Lucro Líquido", f"{lucro_total:.2f} u", delta=f"{lucro_total:.2f}")
                
                st.subheader("📋 Lista de Partidas Analisadas pelo Algoritmo")
                st.dataframe(df_res, use_container_width=True)
  
