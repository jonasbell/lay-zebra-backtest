import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Backtest Lay Zebra - Incluindo Brasileirão", page_icon="⚽", layout="wide")

st.title("📊 Dashboard de Backtest - Lay Zebra")
st.markdown("Validação da estratégia com **Cashout HT**, **Brasileirão Série A** e **Filtro de Times**.")

# Sidebar - Parâmetros da Gestão de Risco
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

st.sidebar.header("⏱️ Momento de Saída")
momento_saida = st.sidebar.selectbox(
    "Momento de Fechamento da Posição",
    ["Sair no Intervalo (HT)", "Manter até o Fim do Jogo (FT)"]
)

st.sidebar.header("🎯 Parâmetros dos Jogos")
odd_min_zebra = st.sidebar.number_input("Odd Mínima Zebra (Visitante)", value=4.00, step=0.10)
odd_max_zebra = st.sidebar.number_input("Odd Máxima Zebra (Visitante)", value=8.00, step=0.10)
taxa_vitoria_min = st.sidebar.slider("% Mínima Vitórias Mandante em Casa", min_value=50, max_value=100, value=70)
amostragem_min_jogos = st.sidebar.number_input("Mínimo de Jogos Anteriores em Casa", value=5, step=1)

st.sidebar.subheader("🌍 Ligas, Temporadas e Times")
temporada = st.sidebar.selectbox("Temporada Histórica", ["2324", "2223", "2122"])

# Dicionário atualizado incluindo o Brasil (Série A)
LIGAS = {
    "Brasileirão Série A (Brasil)": "BRA",
    "Premier League (Inglaterra)": "E0",
    "La Liga (Espanha)": "SP1",
    "Serie A (Itália)": "I1",
    "Bundesliga (Alemanha)": "D1",
    "Primeira Liga (Portugal)": "P1"
}

ligas_selecionadas = st.sidebar.multiselect(
    "Selecione as Ligas", 
    list(LIGAS.keys()), 
    default=["Brasileirão Série A (Brasil)", "Premier League (Inglaterra)", "La Liga (Espanha)"]
)

@st.cache_data
def carregar_dados_historicos(liga_code, temp):
    # Trata a URL para o Brasil (que é armazenado em arquivo único de dados extras)
    if liga_code == "BRA":
        url = "https://www.football-data.co.uk/new/BRA.csv"
    else:
        url = f"https://www.football-data.co.uk/mmz4281/{temp}/{liga_code}.csv"
        
    try:
        df = pd.read_csv(url)
        # Padronização de colunas
        if 'Home' in df.columns:
            df = df.rename(columns={'Home': 'HomeTeam', 'Away': 'AwayTeam', 'HG': 'FTHG', 'AG': 'FTAG', 'Res': 'FTR', 'AvgA': 'B365A', 'AvgH': 'B365H'})
        
        colunas_necessarias = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
        for col in colunas_necessarias:
            if col not in df.columns:
                return pd.DataFrame()
                
        # Garante a existência de Odds e Placares HT (mesmo que com aproximação padrão caso falte)
        if 'B365A' not in df.columns and 'AvgA' in df.columns:
            df['B365A'] = df['AvgA']
        if 'HTHG' not in df.columns:
            df['HTHG'] = (df['FTHG'] / 2).apply(np.floor)
            df['HTAG'] = (df['FTAG'] / 2).apply(np.floor)
            df['HTR'] = np.where(df['HTHG'] > df['HTAG'], 'H', np.where(df['HTHG'] < df['HTAG'], 'A', 'D'))
            
        df = df.dropna(subset=['HomeTeam', 'AwayTeam', 'B365A'])
        return df
    except Exception:
        return pd.DataFrame()

# Carregamento prévio para obter a lista de times disponíveis
dados_pre_carregados = []
for nome_liga in ligas_selecionadas:
    code = LIGAS[nome_liga]
    df_temp = carregar_dados_historicos(code, temporada)
    if not df_temp.empty:
        df_temp["Liga"] = nome_liga
        dados_pre_carregados.append(df_temp)

if dados_pre_carregados:
    df_base = pd.concat(dados_pre_carregados, ignore_index=True)
    lista_times = sorted(df_base["HomeTeam"].dropna().unique().tolist())
    lista_times.insert(0, "Todos os Times")
else:
    lista_times = ["Todos os Times"]

time_selecionado = st.sidebar.selectbox("Filtrar por Time Mandante Específico", lista_times)

if st.button("🚀 Executar Backtest Com Brasileirão", type="primary"):
    if not dados_pre_carregados:
        st.error("Não foi possível carregar os dados históricos das ligas selecionadas.")
    else:
        df = df_base.copy()
        
        entradas_validadas = []
        historico_mandantes = {}
        
        for idx, row in df.iterrows():
            m = row['HomeTeam']
            v = row['AwayTeam']
            golos_h = row['FTHG']
            golos_a = row['FTAG']
            resultado_ft = row['FTR']
            
            hthg = int(row['HTHG'])
            htag = int(row['HTAG'])
            
            try:
                odd_z = float(row['B365A'])
            except (ValueError, TypeError, KeyError):
                continue
            
            if m not in historico_mandantes:
                historico_mandantes[m] = {'jogos': 0, 'vitorias': 0}
                
            stats_h = historico_mandantes[m]
            
            if stats_h['jogos'] >= amostragem_min_jogos:
                taxa_m = (stats_h['vitorias'] / stats_h['jogos']) * 100
            else:
                taxa_m = 0.0
            
            cumpre_time = (time_selecionado == "Todos os Times") or (m == time_selecionado)
                
            if (odd_min_zebra <= odd_z <= odd_max_zebra) and (taxa_m >= taxa_vitoria_min) and cumpre_time:
                
                if tipo_gestao == "Responsabilidade Fixa (Risco Fixo)":
                    responsabilidade = valor_base
                    stake = valor_base / (odd_z - 1.0)
                else:
                    stake = valor_base
                    responsabilidade = valor_base * (odd_z - 1.0)
                
                if momento_saida == "Manter até o Fim do Jogo (FT)":
                    green = (resultado_ft != 'A')
                    lucro_fin = stake if green else -responsabilidade
                    status_resultado = "✅ GREEN (FT)" if green else "❌ RED (FT)"
                else:
                    if hthg > htag:
                        odd_z_ht = odd_z * 3.0
                        status_resultado = "✅ GREEN (HT - Vitoria Mandante)"
                    elif hthg == htag:
                        odd_z_ht = odd_z * 1.30
                        status_resultado = "✅ GREEN (HT - Empate)"
                    else:
                        odd_z_ht = max(1.80, odd_z * 0.40)
                        status_resultado = "⚠️ STOP LOSS (HT - Zebra Vencendo)"
                    
                    lucro_fin = stake * (1.0 - (odd_z / odd_z_ht))
                
                entradas_validadas.append({
                    "Data": row['Date'],
                    "Liga": row['Liga'],
                    "Mandante": m,
                    "Visitante": v,
                    "Placar HT": f"{hthg} x {htag}",
                    "Placar FT": f"{int(golos_h)} x {int(golos_a)}",
                    "Odd Zebra Inicial": odd_z,
                    "Resultado": status_resultado,
                    "Stake (R$)": round(stake, 2),
                    "Risco (R$)": round(responsabilidade, 2),
                    "Lucro Fin (R$)": round(lucro_fin, 2)
                })
            
            historico_mandantes[m]['jogos'] += 1
            if resultado_ft == 'H':
                historico_mandantes[m]['vitorias'] += 1
        
        if not entradas_validadas:
            st.warning(f"Nenhum jogo cumpriu todos os critérios selecionados (Time: {time_selecionado}).")
        else:
            df_res = pd.DataFrame(entradas_validadas)
            
            df_res["Entrada #"] = range(1, len(df_res) + 1)
            df_res["Saldo Acumulado (R$)"] = df_res["Lucro Fin (R$)"].cumsum()
            
            total_jogos = len(df_res)
            greens = len(df_res[df_res["Lucro Fin (R$)"] > 0])
            reds = total_jogos - greens
            winrate = (greens / total_jogos) * 100
            lucro_financeiro_total = df_res["Lucro Fin (R$)"].sum()
            
            st.subheader(f"📈 Resumo do Desempenho — {time_selecionado} ({momento_saida})")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total de Entradas", total_jogos)
            c2.metric("Greens / Reds", f"{greens} / {reds}")
            c3.metric("Taxa de Acerto", f"{winrate:.1f}%")
            c4.metric("Lucro Líquido (R$)", f"R$ {lucro_financeiro_total:.2f}", delta=f"R$ {lucro_financeiro_total:.2f}")
            
            st.subheader("📉 Evolução da Banca (Saldo Acumulado)")
            st.line_chart(df_res, x="Entrada #", y="Saldo Acumulado (R$)", color="#00FF7F")
            
            st.subheader("📋 Detalhamento de Entradas")
            df_exibicao = df_res.copy()
            df_exibicao["Lucro / Prejuízo"] = df_exibicao["Lucro Fin (R$)"].apply(
                lambda x: f"R$ {x:.2f}" if x >= 0 else f"-R$ {abs(x):.2f}"
            )
            df_exibicao["Saldo Acumulado"] = df_exibicao["Saldo Acumulado (R$)"].apply(
                lambda x: f"R$ {x:.2f}" if x >= 0 else f"-R$ {abs(x):.2f}"
            )
            
            colunas_finais = [
                "Entrada #", "Data", "Liga", "Mandante", "Visitante", 
                "Placar HT", "Placar FT", "Odd Zebra Inicial", "Resultado", "Stake (R$)", "Risco (R$)", "Lucro / Prejuízo", "Saldo Acumulado"
            ]
            st.dataframe(df_exibicao[colunas_finais], use_container_width=True)
                                    
