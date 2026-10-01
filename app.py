import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Backtest Lay Zebra", page_icon="📊", layout="wide")

st.title("📊 Dashboard de Backtest - Lay Zebra")
st.markdown("Validação da estratégia comparando a saída no **Final do Jogo (FT)** vs. **Saída no Intervalo (HT)**.")

# Sidebar - Parâmetros da Gestão de Banca & Responsabilidade
st.sidebar.header("💰 Gestão de Risco & Estratégia")
tipo_gestao = st.sidebar.radio(
    "Modelo de Entrada:",
    ["Responsabilidade Fixa (Risco Fixo)", "Stake Fixa (Lucro Fixo)"]
)

valor_base = st.sidebar.number_input(
    "Valor Base (R$ / €)", 
    value=50.00, 
    step=10.00, 
    min_value=1.00
)

# Nova opção: Momento de Saída da Aposta
st.sidebar.header("⏱️ Momento de Saída (Cashout)")
momento_saida = st.sidebar.selectbox(
    "Momento de Fechamento da Posição",
    ["Manter até o Fim do Jogo (FT)", "Sair no Intervalo (HT)"]
)

if momento_saida == "Sair no Intervalo (HT)":
    pct_lucro_ht = st.sidebar.slider("% do Lucro Capturado no HT (Favorito/Empate)", 30, 90, 60) / 100.0
    pct_perda_ht = st.sidebar.slider("% do Risco Assumido em Red no HT (Zebra Vencendo)", 30, 90, 65) / 100.0

st.sidebar.header("🎯 Parâmetros dos Jogos")
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
        colunas = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'HTHG', 'HTAG', 'HTR', 'B365H', 'B365D', 'B365A']
        df = df[[c for c in colunas if c in df.columns]].dropna()
        return df
    except Exception:
        return pd.DataFrame()

if st.button("🚀 Executar Backtest Com Estratégia HT/FT", type="primary"):
    with st.spinner("Analisando histórico de partidas (incluindo dados de 1º tempo)..."):
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
                resultado_ft = row['FTR']
                
                # Dados do 1º Tempo
                hthg = row['HTHG']
                htag = row['HTAG']
                resultado_ht = row['HTR']
                
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
                    
                    if tipo_gestao == "Responsabilidade Fixa (Risco Fixo)":
                        responsabilidade = valor_base
                        stake = valor_base / (odd_z - 1.0)
                    else:
                        stake = valor_base
                        responsabilidade = valor_base * (odd_z - 1.0)
                    
                    # Cálculo conforme o Momento de Saída
                    if momento_saida == "Manter até o Fim do Jogo (FT)":
                        green = (resultado_ft != 'A')
                        lucro_fin = stake if green else -responsabilidade
                        status_resultado = "✅ GREEN (FT)" if green else "❌ RED (FT)"
                    else:
                        # Saída no Intervalo (HT)
                        zebra_vencendo_ht = (resultado_ht == 'A')
                        
                        if not zebra_vencendo_ht:
                            # Mandante vencendo ou Empate no HT -> Lucro Parcial em HT
                            green = True
                            lucro_fin = stake * pct_lucro_ht
                            status_resultado = "✅ GREEN (HT)"
                        else:
                            # Zebra vencendo no HT -> Stop Loss Parcial em HT
                            green = False
                            lucro_fin = - (responsabilidade * pct_perda_ht)
                            status_resultado = "⚠️ STOP LOSS (HT)"
                    
                    entradas_validadas.append({
                        "Data": row['Date'],
                        "Liga": row['Liga'],
                        "Mandante": m,
                        "Visitante": v,
                        "Placar HT": f"{int(hthg)} x {int(htag)}",
                        "Placar FT": f"{int(golos_h)} x {int(golos_a)}",
                        "Odd Zebra": odd_z,
                        "Resultado": status_resultado,
                        "Stake (R$)": round(stake, 2),
                        "Risco (R$)": round(responsabilidade, 2),
                        "Lucro Fin (R$)": round(lucro_fin, 2)
                    })
                
                historico_mandantes[m]['jogos'] += 1
                if resultado_ft == 'H':
                    historico_mandantes[m]['vitorias'] += 1
            
            if not entradas_validadas:
                st.warning("Nenhum jogo no histórico cumpriu todos os critérios da estratégia.")
            else:
                df_res = pd.DataFrame(entradas_validadas)
                
                # Cálculo da evolução do saldo
                df_res["Entrada #"] = range(1, len(df_res) + 1)
                df_res["Saldo Acumulado (R$)"] = df_res["Lucro Fin (R$)"].cumsum()
                
                total_jogos = len(df_res)
                greens = len(df_res[df_res["Resultado"].str.contains("GREEN")])
                reds = total_jogos - greens
                winrate = (greens / total_jogos) * 100
                lucro_financeiro_total = df_res["Lucro Fin (R$)"].sum()
                
                st.subheader(f"📈 Resumo da Estratégia ({momento_saida})")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total de Entradas", total_jogos)
                c2.metric("Greens / Reds (ou Stop)", f"{greens} / {reds}")
                c3.metric("Taxa de Acerto", f"{winrate:.1f}%")
                c4.metric("Lucro Líquido (R$)", f"R$ {lucro_financeiro_total:.2f}", delta=f"R$ {lucro_financeiro_total:.2f}")
                
                # Gráfico
                st.subheader("📉 Evolução da Banca (Saldo Acumulado)")
                st.line_chart(df_res, x="Entrada #", y="Saldo Acumulado (R$)", color="#00FF7F")
                
                # Tabela detalhada
                st.subheader("📋 Detalhamento de Partidas (Com Placares HT e FT)")
                df_exibicao = df_res.copy()
                df_exibicao["Lucro / Prejuízo"] = df_exibicao["Lucro Fin (R$)"].apply(
                    lambda x: f"R$ {x:.2f}" if x >= 0 else f"-R$ {abs(x):.2f}"
                )
                df_exibicao["Saldo Acumulado"] = df_exibicao["Saldo Acumulado (R$)"].apply(
                    lambda x: f"R$ {x:.2f}" if x >= 0 else f"-R$ {abs(x):.2f}"
                )
                
                colunas_finais = [
                    "Entrada #", "Data", "Liga", "Mandante", "Visitante", 
                    "Placar HT", "Placar FT", "Odd Zebra", "Resultado", "Stake (R$)", "Risco (R$)", "Lucro / Prejuízo", "Saldo Acumulado"
                ]
                st.dataframe(df_exibicao[colunas_finais], use_container_width=True)
                        
