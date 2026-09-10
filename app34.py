import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(page_title="Robô Investidor PRO", page_icon="🤖", layout="wide")

# ==========================================
# FUNÇÃO PARA ANALISAR ATIVO (RSI TEM PRIORIDADE MÁXIMA)
# ==========================================
def analisar_ativo(ticker):
    try:
        if ticker == "MMI_POLYGON":
            return None, None, "🪙 MMI", "#f39c12", None, "Ver QuickSwap", 0
        
        dados = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if len(dados) < 30:
            return None, None, None, None, None, None, None
        
        precos = dados['Close'].values.flatten()
        preco_atual = float(precos[-1])
        preco_inicial = float(precos[0])
        variacao = ((preco_atual - preco_inicial) / preco_inicial) * 100
        
        # RSI (INDICADOR PRINCIPAL)
        delta = dados['Close'].diff()
        ganho = delta.where(delta > 0, 0)
        perda = -delta.where(delta < 0, 0)
        media_ganho = ganho.rolling(window=14).mean()
        media_perda = perda.rolling(window=14).mean()
        rs = media_ganho / media_perda
        rsi = 100 - (100 / (1 + rs))
        rsi_atual = rsi.iloc[-1].item() if hasattr(rsi.iloc[-1], 'item') else float(rsi.iloc[-1])
        
        # ==========================================
        # LÓGICA CORRIGIDA: RSI TEM PRIORIDADE MÁXIMA
        # ==========================================
        sinal = "🟡 AGUARDAR"
        cor = "#f39c12"
        pontos = 0
        
        # REGRA 1: RSI ABAIXO DE 45 = COMPRA (Prioridade Máxima)
        if rsi_atual < 30:
            sinal = "🟢 COMPRA FORTE"
            cor = "#2ecc71"
            pontos = 5
        elif rsi_atual < 45:
            sinal = "🟢 COMPRAR"
            cor = "#2ecc71"
            pontos = 3
        # REGRA 2: RSI ENTRE 45 E 60 = AGUARDAR (Neutro)
        elif rsi_atual < 60:
            sinal = "🟡 AGUARDAR"
            cor = "#f39c12"
            pontos = 1
        # REGRA 3: RSI ACIMA DE 60 = VENDER (Prioridade Máxima)
        elif rsi_atual > 70:
            sinal = "🔴 VENDA FORTE"
            cor = "#e74c3c"
            pontos = -5
        elif rsi_atual > 60:
            sinal = "🔴 VENDER"
            cor = "#e74c3c"
            pontos = -3
        
        # ==========================================
        # BÔNUS/DESCONTO POR MACD E MÉDIAS (só se RSI estiver neutro)
        # ==========================================
        if 45 <= rsi_atual <= 60:
            # Calcular MACD
            macd = dados['Close'].ewm(span=12, adjust=False).mean() - dados['Close'].ewm(span=26, adjust=False).mean()
            sinal_macd = macd.ewm(span=9, adjust=False).mean()
            macd_atual = macd.iloc[-1].item() if hasattr(macd.iloc[-1], 'item') else float(macd.iloc[-1])
            sinal_atual = sinal_macd.iloc[-1].item() if hasattr(sinal_macd.iloc[-1], 'item') else float(sinal_macd.iloc[-1])
            
            media_50 = dados['Close'].rolling(window=50).mean().iloc[-1].item()
            media_200 = dados['Close'].rolling(window=200).mean().iloc[-1].item()
            
            # Se o MACD está subindo E a tendência é de alta, sobe para COMPRAR
            if macd_atual > sinal_atual and media_50 > media_200:
                sinal = "🟢 COMPRAR"
                cor = "#2ecc71"
                pontos = 3
            # Se o MACD está caindo E a tendência é de baixa, desce para VENDER
            elif macd_atual < sinal_atual and media_50 < media_200:
                sinal = "🔴 VENDER"
                cor = "#e74c3c"
                pontos = -3
        
        # Mini-gráfico
        cor_grafico = '#2ecc71' if variacao >= 0 else '#e74c3c'
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dados.index, y=precos, mode='lines',
            line=dict(color=cor_grafico, width=2),
            fill='tozeroy',
            fillcolor=f'rgba({int(cor_grafico[1:3], 16)}, {int(cor_grafico[3:5], 16)}, {int(cor_grafico[5:7], 16)}, 0.1)',
            showlegend=False, hoverinfo='skip'
        ))
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0), height=60,
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, visible=False),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', hovermode=False
        )
        
        return preco_atual, variacao, sinal, cor, fig, f"RSI: {rsi_atual:.1f}", rsi_atual
    except:
        return None, None, None, None, None, None, None

# ==========================================
# LISTA DE ATIVOS POR CATEGORIA
# ==========================================
ativos_por_categoria = {
    "🏦 Ações Brasileiras": {
        "PETR4": "PETR4.SA", "VALE3": "VALE3.SA", "ITUB4": "ITUB4.SA",
        "BBAS3": "BBAS3.SA", "BBDC4": "BBDC4.SA", "WEGE3": "WEGE3.SA",
        "MGLU3": "MGLU3.SA", "LREN3": "LREN3.SA", "ABEV3": "ABEV3.SA",
    },
    "🏠 FIIs (Fundos Imobiliários)": {
        "HGLG11": "HGLG11.SA", "MXRF11": "MXRF11.SA", "KNRI11": "KNRI11.SA",
        "KNCR11": "KNCR11.SA", "VGIR11": "VGIR11.SA", "ALZR11": "ALZR11.SA",
    },
    "💎 ETFs de Dividendos": {
        "NDIV11": "NDIV11.SA", "DIVD11": "DIVD11.SA",
        "SPYI11": "SPYI11.SA", "QQQI11": "QQQI11.SA",
    },
    "🪙 Criptomoedas": {
        "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Solana": "SOL-USD",
    },
    "🌾 Commodities": {
        "Ouro": "GC=F", "Prata": "SI=F", "Café": "KC=F",
        "Milho": "ZC=F", "Soja": "ZS=F", "Açúcar": "SB=F",
    },
    "🌍 Ações Internacionais": {
        "Apple": "AAPL", "Microsoft": "MSFT", "Realty Income": "O",
    },
    "🪙 MMI Infinity Token": {
        "MMI (Polygon)": "MMI_POLYGON",
    }
}

# ==========================================
# MENU LATERAL
# ==========================================
st.sidebar.title("🤖 Robô Investidor PRO")
opcao = st.sidebar.radio("Escolha uma opção:", 
                          ["📊 Painel de Mercado",
                           "🌟 Radar de Oportunidades", 
                           "📈 Swing Trade (Ações)", 
                           "📊 Ranking de Eficiência", 
                           "⏪ Backtest (Testar o Passado)", 
                           "🛒 Comprar Ativo (Simulação)", 
                           "🧪 Simulador de Teste", 
                           "📈 Gráfico Profissional",
                           "🪙 Meus Tokens (MMI)"])

# ==========================================
# TELA 1: PAINEL DE MERCADO
# ==========================================
if opcao == "📊 Painel de Mercado":
    st.title("📊 Painel de Mercado")
    st.write("Indicações baseadas no **RSI** (Prioridade Máxima): RSI < 45 = COMPRAR | RSI > 60 = VENDER")
    
    st.markdown("""
    🟢 **COMPRAR** = RSI abaixo de 45 | 
    🟡 **AGUARDAR** = RSI entre 45 e 60 | 
    🔴 **VENDER** = RSI acima de 60 | 
    🪙 **Token** = Ver QuickSwap
    """)
    
    st.markdown("---")
    
    for categoria, ativos in ativos_por_categoria.items():
        st.subheader(categoria)
        
        num_colunas = 4
        cols = st.columns(num_colunas)
        
        for idx, (nome, ticker) in enumerate(ativos.items()):
            col_idx = idx % num_colunas
            
            with cols[col_idx]:
                preco, variacao, sinal, cor, fig, info_rsi, rsi_val = analisar_ativo(ticker)
                
                if ticker == "MMI_POLYGON":
                    st.markdown(f"""
                    <div style="border: 2px solid #f39c12; border-radius: 10px; padding: 10px; margin-bottom: 10px; background-color: rgba(243, 156, 18, 0.1);">
                        <h4 style="margin: 0; color: #f39c12;">🪙 {nome}</h4>
                        <p style="margin: 5px 0; color: #f39c12;"><b>MMI Infinity Token</b></p>
                        <p style="margin: 5px 0; color: #f39c12;">Ver preço na QuickSwap</p>
                    </div>
                    """, unsafe_allow_html=True)
                elif preco is not None:
                    if "COMPRA" in sinal:
                        border_color = "#2ecc71"
                        bg_color = "rgba(46, 204, 113, 0.1)"
                    elif "VENDER" in sinal or "VENDA" in sinal:
                        border_color = "#e74c3c"
                        bg_color = "rgba(231, 76, 60, 0.1)"
                    else:
                        border_color = "#f39c12"
                        bg_color = "rgba(243, 156, 18, 0.1)"
                    
                    cor_var = "#2ecc71" if variacao >= 0 else "#e74c3c"
                    seta = "▲" if variacao >= 0 else "▼"
                    
                    st.markdown(f"""
                    <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 12px; margin-bottom: 10px; background-color: {bg_color};">
                        <h4 style="margin: 0;">{nome}</h4>
                        <p style="margin: 5px 0; font-size: 18px;"><b>R$ {preco:,.2f}</b></p>
                        <p style="margin: 5px 0; color: {cor_var}; font-size: 14px;">{seta} {variacao:.2f}%</p>
                        <p style="margin: 5px 0; font-size: 13px; color: #aaa;">{info_rsi}</p>
                        <p style="margin: 5px 0; font-size: 14px; font-weight: bold; color: {border_color};">{sinal}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{ticker}")
                else:
                    st.markdown(f"""
                    <div style="border: 1px solid #555; border-radius: 10px; padding: 10px; margin-bottom: 10px;">
                        <h4 style="margin: 0;">{nome}</h4>
                        <p style="margin: 5px 0; color: #888;">Dados indisponíveis</p>
                    </div>
                    """, unsafe_allow_html=True)

# ==========================================
# TELA 2: RADAR DE OPORTUNIDADES
# ==========================================
elif opcao == "🌟 Radar de Oportunidades":
    st.title("🌟 Radar de Oportunidades")
    st.write("Ativos com **RSI abaixo de 45** (oportunidades reais de compra).")
    
    todos_ativos = {}
    for categoria in ativos_por_categoria.values():
        todos_ativos.update(categoria)
    
    if st.button("🔍 Buscar Oportunidades Agora"):
        resultados = []
        progress_bar = st.progress(0)
        
        for i, (nome, ticker) in enumerate(todos_ativos.items()):
            preco, variacao, sinal, cor, _, info_rsi, rsi_val = analisar_ativo(ticker)
            if preco is not None and rsi_val is not None:
                resultados.append({
                    "Ativo": nome, "Ticker": ticker,
                    "Preço": round(preco, 2),
                    "Variação (%)": round(variacao, 2),
                    "RSI": round(rsi_val, 1),
                    "Sinal": sinal
                })
            progress_bar.progress((i + 1) / len(todos_ativos))
        
        progress_bar.empty()
        
        if resultados:
            df = pd.DataFrame(resultados)
            df = df.sort_values(by="RSI", ascending=True).reset_index(drop=True)
            
            st.subheader("🏆 TOP 5 MELHORES OPORTUNIDADES DE COMPRA (Menor RSI)")
            top_5 = df.head(5)
            
            cols = st.columns(5)
            for i, row in top_5.iterrows():
                with cols[i]:
                    if "COMPRA" in row['Sinal']:
                        st.success(f"### {row['Ativo']}\n**R$ {row['Preço']:.2f}**\nRSI: {row['RSI']}\n{row['Sinal']}")
                    elif "AGUARDAR" in row['Sinal']:
                        st.warning(f"### {row['Ativo']}\n**R$ {row['Preço']:.2f}**\nRSI: {row['RSI']}\n{row['Sinal']}")
                    else:
                        st.error(f"### {row['Ativo']}\n**R$ {row['Preço']:.2f}**\nRSI: {row['RSI']}\n{row['Sinal']}")
            
            st.subheader("📋 Tabela Completa (ordenada por RSI)")
            st.dataframe(df)
        else:
            st.warning("⚠️ Nenhum ativo encontrado.")

# ==========================================
# TELA 3: SWING TRADE
# ==========================================
elif opcao == "📈 Swing Trade (Ações)":
    st.title("📈 Swing Trade (Ações)")
    st.write("Ações com **RSI abaixo de 45** para operar na semana.")
    
    if st.button("🔍 Buscar Ações para Swing Trade"):
        resultados = []
        progress_bar = st.progress(0)
        
        acoes = ativos_por_categoria["🏦 Ações Brasileiras"]
        
        for i, (nome, ticker) in enumerate(acoes.items()):
            preco, variacao, sinal, cor, _, info_rsi, rsi_val = analisar_ativo(ticker)
            if preco is not None and rsi_val is not None:
                resultados.append({
                    "Ativo": nome, "Ticker": ticker,
                    "Preço": round(preco, 2),
                    "RSI": round(rsi_val, 1),
                    "Sinal": sinal
                })
            progress_bar.progress((i + 1) / len(acoes))
        
        progress_bar.empty()
        
        if resultados:
            df = pd.DataFrame(resultados)
            df = df.sort_values(by="RSI", ascending=True).reset_index(drop=True)
            
            acoes_baratas = df[df["RSI"] < 45]
            
            if not acoes_baratas.empty:
                st.subheader("🏆 AÇÕES PRONTAS PARA COMPRAR (RSI < 45)")
                for idx, row in acoes_baratas.iterrows():
                    st.success(f"**{row['Ativo']}** - R$ {row['Preço']:.2f} - RSI: {row['RSI']} - {row['Sinal']}")
            else:
                st.warning("⚠️ Nenhuma ação com RSI abaixo de 45. Aguarde a queda!")
            
            st.subheader("📋 Todas as Ações (ordenadas por RSI)")
            st.dataframe(df)
        else:
            st.warning("⚠️ Nenhuma ação encontrada.")

# ==========================================
# TELA 4: RANKING DE EFICIÊNCIA
# ==========================================
elif opcao == "📊 Ranking de Eficiência":
    st.title("📊 Ranking de Eficiência")
    st.write("Ativos com **RSI baixo (baratos)** e **histórico positivo**.")
    
    if st.button("🔍 Calcular Ranking"):
        resultados = []
        progress_bar = st.progress(0)
        
        todos_ativos = {}
        for categoria in ativos_por_categoria.values():
            todos_ativos.update(categoria)
        
        for i, (nome, ticker) in enumerate(todos_ativos.items()):
            if ticker == "MMI_POLYGON":
                progress_bar.progress((i + 1) / len(todos_ativos))
                continue
            
            try:
                dados = yf.download(ticker, period="3mo", interval="1d", progress=False)
                if len(dados) < 30:
                    progress_bar.progress((i + 1) / len(todos_ativos))
                    continue
                
                precos = dados['Close'].values.flatten()
                preco_hoje = float(precos[-1])
                preco_30d = float(precos[-30])
                taxa_acerto = 100 if preco_hoje > preco_30d else 0
                
                preco, variacao, sinal, cor, _, info_rsi, rsi_val = analisar_ativo(ticker)
                
                if preco is not None and rsi_val is not None:
                    resultados.append({
                        "Ativo": nome, "Ticker": ticker,
                        "Taxa de Acerto (%)": taxa_acerto,
                        "Preço Atual": round(preco, 2),
                        "RSI": round(rsi_val, 1)
                    })
            except:
                pass
            progress_bar.progress((i + 1) / len(todos_ativos))
        
        progress_bar.empty()
        
        if resultados:
            df = pd.DataFrame(resultados)
            # Filtrar apenas RSI < 45 (baratos)
            df_filtrado = df[df["RSI"] < 45]
            
            if not df_filtrado.empty:
                df_filtrado = df_filtrado.sort_values(by="RSI", ascending=True).reset_index(drop=True)
                st.subheader("🏆 ATIVOS BARATOS (RSI < 45) COM HISTÓRICO")
                
                for idx, row in df_filtrado.iterrows():
                    st.success(f"**{row['Ativo']}** - RSI: {row['RSI']} - Taxa: {row['Taxa de Acerto (%)']}% - R$ {row['Preço Atual']:.2f}")
                
                st.dataframe(df_filtrado)
            else:
                st.warning("⚠️ Nenhum ativo com RSI abaixo de 45 no momento.")
                st.subheader("📋 Todos os Ativos")
                st.dataframe(df.sort_values(by="RSI", ascending=True))
        else:
            st.warning("⚠️ Nenhum ativo encontrado.")

# ==========================================
# TELA 5: BACKTEST
# ==========================================
elif opcao == "⏪ Backtest (Testar o Passado)":
    st.title("⏪ Backtest - Teste o Passado")
    
    todos_ativos = {}
    for categoria in ativos_por_categoria.values():
        todos_ativos.update(categoria)
    
    ativo_escolhido = st.selectbox("Ativos disponíveis:", list(todos_ativos.keys()))
    ticker = todos_ativos[ativo_escolhido]
    
    if ticker == "MMI_POLYGON":
        st.warning("⚠️ Backtest não disponível para o MMI Token.")
    else:
        data_compra = st.date_input("Data da compra:", value=datetime.now() - timedelta(days=30))
        quantidade = st.number_input("Quantidade:", min_value=1, value=10, step=1)
        
        if st.button("🔮 Rodar Backtest"):
            try:
                dados = yf.download(ticker, period="6mo", interval="1d", progress=False)
                if len(dados) < 30:
                    st.error("Dados insuficientes.")
                else:
                    data_compra = pd.to_datetime(data_compra)
                    dados.index = pd.to_datetime(dados.index)
                    
                    preco_compra = None
                    for idx in dados.index:
                        if idx <= data_compra:
                            preco_compra = dados.loc[idx]['Close']
                        else:
                            break
                    
                    if preco_compra is None:
                        st.error("Data fora do intervalo.")
                    else:
                        preco_compra = float(preco_compra.iloc[0]) if hasattr(preco_compra, 'iloc') else float(preco_compra)
                        preco_atual = float(dados['Close'].iloc[-1].item())
                        
                        investimento = preco_compra * quantidade
                        valor_atual = preco_atual * quantidade
                        lucro = valor_atual - investimento
                        percentual = (lucro / investimento) * 100
                        
                        st.write("---")
                        st.subheader("📊 RESULTADO DO BACKTEST")
                        st.write(f"**{ativo_escolhido} ({ticker})**")
                        st.write(f"**Data da compra:** {data_compra.strftime('%d/%m/%Y')}")
                        st.write(f"**Comprou por:** R$ {preco_compra:.2f}")
                        st.write(f"**Valor atual:** R$ {preco_atual:.2f}")
                        st.write(f"**Investiu:** R$ {investimento:.2f}")
                        st.write(f"**Vale agora:** R$ {valor_atual:.2f}")
                        
                        if lucro > 0:
                            st.success(f"💰 **LUCRO: R$ {lucro:.2f} ({percentual:.2f}%)**")
                        elif lucro < 0:
                            st.error(f"📉 **PREJUÍZO: R$ {lucro:.2f} ({percentual:.2f}%)**")
                        else:
                            st.info("**Sem ganho nem perda.**")
            except Exception as e:
                st.error(f"Erro: {e}")

# ==========================================
# TELA 6: COMPRAR ATIVO (SIMULAÇÃO)
# ==========================================
elif opcao == "🛒 Comprar Ativo (Simulação)":
    st.title("🛒 Comprar Ativo (Simulação)")
    
    todos_ativos = {}
    for categoria in ativos_por_categoria.values():
        todos_ativos.update(categoria)
    
    ativo_escolhido = st.selectbox("Ativos disponíveis:", list(todos_ativos.keys()))
    ticker = todos_ativos[ativo_escolhido]
    
    if ticker == "MMI_POLYGON":
        st.warning("Preço do MMI indisponível.")
        preco_atual = 0
    else:
        dados = yf.download(ticker, period="1d", interval="1d", progress=False)
        preco_atual = dados['Close'].iloc[-1].item()
        st.write(f"**{ativo_escolhido}** está custando **R$ {preco_atual:.2f}**")
    
    quantidade = st.number_input("Quantidade:", min_value=1, step=1)
    
    if st.button("✅ Registrar Simulação"):
        if 'carteira_teste' not in st.session_state:
            st.session_state.carteira_teste = pd.DataFrame(columns=["Ativo", "Ticker", "Preco_Compra", "Quantidade", "Data_Compra"])
        
        novo_registro = pd.DataFrame([{"Ativo": ativo_escolhido, "Ticker": ticker, "Preco_Compra": preco_atual, "Quantidade": quantidade, "Data_Compra": datetime.now().strftime("%d/%m/%Y")}])
        st.session_state.carteira_teste = pd.concat([st.session_state.carteira_teste, novo_registro], ignore_index=True)
        st.success(f"✅ Compra simulada de {quantidade} unidades registrada!")

# ==========================================
# TELA 7: SIMULADOR DE TESTE
# ==========================================
elif opcao == "🧪 Simulador de Teste":
    st.title("🧪 Simulador de Teste")
    
    if 'carteira_teste' not in st.session_state or st.session_state.carteira_teste.empty:
        st.info("Você ainda não tem compras simuladas.")
    else:
        st.write("### 📊 Resultado das suas compras simuladas")
        for index, row in st.session_state.carteira_teste.iterrows():
            try:
                if row['Ticker'] == "MMI_POLYGON":
                    preco_atual = 0
                else:
                    dados = yf.download(row['Ticker'], period="1d", interval="1d", progress=False)
                    preco_atual = dados['Close'].iloc[-1].item()
                
                preco_compra = row['Preco_Compra']
                quantidade = row['Quantidade']
                
                investimento = preco_compra * quantidade
                valor_atual = preco_atual * quantidade
                lucro = valor_atual - investimento
                percentual = (lucro / investimento) * 100 if investimento > 0 else 0
                
                st.write(f"**{row['Ativo']} ({row['Ticker']})**")
                st.write(f"   Comprou por: R$ {preco_compra:.2f} | Valor atual: R$ {preco_atual:.2f}")
                
                if lucro > 0:
                    st.success(f"   💰 Lucro: R$ {lucro:.2f} ({percentual:.2f}%)")
                elif lucro < 0:
                    st.error(f"   📉 Prejuízo: R$ {lucro:.2f} ({percentual:.2f}%)")
                else:
                    st.info(f"   Sem ganho nem perda.")
                
                if st.button(f"Vender {row['Ativo']}", key=f"sell_{index}"):
                    st.session_state.carteira_teste = st.session_state.carteira_teste.drop(index)
                    st.success("✅ Venda simulada realizada!")
                    st.rerun()
            except:
                continue

# ==========================================
# TELA 8: GRÁFICO PROFISSIONAL
# ==========================================
elif opcao == "📈 Gráfico Profissional":
    st.title("📈 Gráfico Profissional")
    
    ticker = st.text_input("Ticker:", "PETR4.SA")
    
    if ticker == "MMI_POLYGON":
        st.warning("⚠️ Gráfico não disponível para o MMI Token.")
    else:
        if st.button("Gerar Gráfico"):
            dados = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if len(dados) < 30:
                st.error("Dados insuficientes.")
            else:
                dados.columns = [col[0] for col in dados.columns]
                df = dados[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                df.index = pd.to_datetime(df.index)
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                                             low=df['Low'], close=df['Close'], name='Candles'), row=1, col=1)
                
                df['MMA20'] = df['Close'].rolling(window=20).mean()
                fig.add_trace(go.Scatter(x=df.index, y=df['MMA20'], mode='lines', name='Média 20', line=dict(color='yellow')), row=1, col=1)
                
                delta = df['Close'].diff()
                ganho = delta.where(delta > 0, 0)
                perda = -delta.where(delta < 0, 0)
                media_ganho = ganho.rolling(window=14).mean()
                media_perda = perda.rolling(window=14).mean()
                rs = media_ganho / media_perda
                rsi = 100 - (100 / (1 + rs))
                
                rsi_para_grafico = rsi.dropna()
                
                fig.add_trace(go.Scatter(x=df.index, y=rsi_para_grafico, name='RSI', line=dict(color='purple')), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                
                fig.update_layout(title=f"📈 {ticker}", template='plotly_dark', height=700, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TELA 9: MEUS TOKENS (MMI)
# ==========================================
elif opcao == "🪙 Meus Tokens (MMI)":
    st.title("🪙 Meus Tokens (MMI Infinity)")
    st.success("✅ Token MMI Infinity (Polygon)")
    st.write(f"**Endereço do Contrato:** `0xba2aebF8F68E347D37a5101DD466F81BcCC56084`")
    st.markdown("""
    ---
    **Como comprar/vender MMI Infinity:**
    1. Acesse a **QuickSwap** (quickswap.exchange)
    2. Conecte sua carteira **MetaMask** (rede Polygon)
    3. Cole o endereço do contrato: `0xba2aebF8F68E347D37a5101DD466F81BcCC56084`
    4. Adicione o token à sua carteira
    5. Troque MATIC ou USDC por MMI
    """)