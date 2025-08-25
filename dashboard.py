import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from sklearn.linear_model import LinearRegression

# -------------------------------
# Macros
# -------------------------------
percentMean = 0.01693333333
EUR_RATE = 0.85457717  # 1 USD = 0.85457717 EUR

# -------------------------------
# Hardcoded multipliers per coin
# -------------------------------
multipliers = {
    "BTC": ((1 - percentMean)**4) * 0.95 * 0.95,
    "ETH": ((1 - percentMean)**4) * 0.95 * 0.95,
    "ADA": ((1 - percentMean)**4) * 0.95 * 0.95,
    "AVAX": ((1 - percentMean)**4) * 0.95 * 0.95
}

# -------------------------------
# Streamlit page config
# -------------------------------
st.set_page_config(page_title="Crypto Dashboard", layout="wide")
st.title("Crypto Prices - All Time (Offline)")

# -------------------------------
# Currency selector
# -------------------------------
currency = st.sidebar.radio("Select currency", ["USD", "EUR"])
currency_factor = 1.0 if currency == "USD" else EUR_RATE
currency_symbol = "$" if currency == "USD" else "€"

# -------------------------------
# Log scale toggle
# -------------------------------
log_scale = st.sidebar.checkbox("Logarithmic scale", value=False)

# -------------------------------
# Database setup
# -------------------------------
db_file = "crypto_prices.db"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS coin_ranges (
    coin TEXT PRIMARY KEY,
    regression_start INTEGER,
    regression_end INTEGER,
    mean_start INTEGER,
    mean_end INTEGER
)
""")
conn.commit()

# -------------------------------
# 1️⃣ Load available coins
# -------------------------------
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
available_coins = [t.replace("_prices","") for t in tables['name'] if t.endswith("_prices")]
if not available_coins:
    st.warning("No price data found in the database. Run the update script first.")
    st.stop()

# -------------------------------
# 2️⃣ Select coin
# -------------------------------
selected_coin = st.selectbox("Select cryptocurrency", options=available_coins, index=0)

# -------------------------------
# 3️⃣ Load coin data
# -------------------------------
df = pd.read_sql_query(f"SELECT * FROM {selected_coin}_prices", conn)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['date'] = df['timestamp'].dt.date
min_date, max_date = df['date'].min(), df['date'].max()

# -------------------------------
# 4️⃣ Load previous slider positions
# -------------------------------
cursor.execute("SELECT regression_start, regression_end, mean_start, mean_end FROM coin_ranges WHERE coin=?", (selected_coin,))
row = cursor.fetchone()
if row:
    reg_start_default = pd.to_datetime(row[0], unit='s').date()
    reg_end_default = pd.to_datetime(row[1], unit='s').date()
    mean_start_default = pd.to_datetime(row[2], unit='s').date()
    mean_end_default = pd.to_datetime(row[3], unit='s').date()
else:
    reg_start_default, reg_end_default = min_date, max_date
    mean_start_default, mean_end_default = min_date, max_date

# -------------------------------
# 5️⃣ Regression slider
# -------------------------------
st.sidebar.header(f"{selected_coin} Regression Control")
regression_range = st.sidebar.slider(
    "Select regression date range",
    min_value=min_date,
    max_value=max_date,
    value=(reg_start_default, reg_end_default),
    format="YYYY-MM-DD",
    key=f"{selected_coin}_regression_range"
)
reg_start_date, reg_end_date = regression_range
reg_start_idx = (df['date'] - reg_start_date).abs().idxmin()
reg_end_idx = (df['date'] - reg_end_date).abs().idxmin()
df_reg = df.iloc[reg_start_idx:reg_end_idx+1]

X = np.arange(len(df_reg)).reshape(-1, 1)
y = df_reg['close'].values * currency_factor
reg = LinearRegression().fit(X, y)
reg_line = reg.predict(np.arange(len(df)).reshape(-1, 1))

# -------------------------------
# 6️⃣ Mean slider
# -------------------------------
st.sidebar.header(f"{selected_coin} Mean Range")
mean_range_slider = st.sidebar.slider(
    "Select mean date range",
    min_value=min_date,
    max_value=max_date,
    value=(mean_start_default, mean_end_default),
    format="YYYY-MM-DD",
    key=f"{selected_coin}_mean_range"
)
mean_start_date, mean_end_date = mean_range_slider
mean_start_idx = (df['date'] - mean_start_date).abs().idxmin()
mean_end_idx = (df['date'] - mean_end_date).abs().idxmin()
df_mean_range = df.iloc[mean_start_idx:mean_end_idx+1]
mean_range = df_mean_range['close'].mean() * currency_factor

# -------------------------------
# 7️⃣ Save slider positions to DB
# -------------------------------
cursor.execute("""
INSERT INTO coin_ranges (coin, regression_start, regression_end, mean_start, mean_end)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(coin) DO UPDATE SET
regression_start=excluded.regression_start,
regression_end=excluded.regression_end,
mean_start=excluded.mean_start,
mean_end=excluded.mean_end
""", (selected_coin,
      int(pd.Timestamp(reg_start_date).timestamp()),
      int(pd.Timestamp(reg_end_date).timestamp()),
      int(pd.Timestamp(mean_start_date).timestamp()),
      int(pd.Timestamp(mean_end_date).timestamp())))
conn.commit()

# -------------------------------
# 8️⃣ Plot chart
# -------------------------------
fig = px.line(df, x="timestamp", y=df['close']*currency_factor,
              labels={"close":f"Price ({currency_symbol})", "timestamp":"Date"},
              title=f"{selected_coin.upper()} Price - All Time ({currency})",
              log_y=log_scale)

fig.add_trace(go.Scatter(
    x=df['timestamp'],
    y=reg_line,
    mode='lines',
    line=dict(color='orange', dash='dash'),
    name=f"Regression ({reg_start_date} → {reg_end_date})"
))

fig.add_trace(go.Scatter(
    x=[df['timestamp'].iloc[reg_start_idx], df['timestamp'].iloc[reg_end_idx]],
    y=[df['close'].iloc[reg_start_idx]*currency_factor, df['close'].iloc[reg_end_idx]*currency_factor],
    mode='markers',
    marker=dict(color=['orange', 'darkorange'], size=20),
    name='Regression Range'
))

fig.add_trace(go.Scatter(
    x=[df['timestamp'].iloc[mean_start_idx], df['timestamp'].iloc[mean_end_idx]],
    y=[df['close'].iloc[mean_start_idx]*currency_factor, df['close'].iloc[mean_end_idx]*currency_factor],
    mode='markers',
    marker=dict(color=['cyan', 'darkcyan'], size=12),
    name='Mean Range'
))

fig.add_hline(
    y=mean_range, line_dash="dash", line_color="yellow",
    annotation_text=f"Mean ({mean_start_date} → {mean_end_date})",
    annotation_position="top left"
)

multiplier = multipliers.get(selected_coin.upper(), 1.5)
fig.add_hline(y=mean_range * multiplier, line_dash="dot", line_color="red",
              annotation_text=f"Mean × {multiplier:.2f} = {mean_range*multiplier:.2f}",
              annotation_position="bottom left")
fig.add_hline(y=mean_range / multiplier, line_dash="dot", line_color="green",
              annotation_text=f"Mean ÷ {multiplier:.2f} = {mean_range/multiplier:.2f}",
              annotation_position="top left")

fig.update_layout(template="plotly_dark", hovermode="x unified")
fig.update_xaxes(rangeslider_visible=True)
st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# 9️⃣ Calculator
# -------------------------------
st.markdown("---")
st.header("Crypto Price Calculator")

st.write(f"Calculate values based on the {selected_coin.upper()} mean and multiplier.")
input_price = st.number_input(f"Enter {currency} price:", min_value=0.0, value=float(mean_range))
calc_multiplier = st.number_input("Multiplier:", min_value=0.0, value=float(multiplier))

calc_multiplied = input_price * calc_multiplier
calc_divided = input_price / calc_multiplier

st.write(f"**Price × Multiplier:** {calc_multiplied:.2f} {currency_symbol}")
st.write(f"**Price ÷ Multiplier:** {calc_divided:.2f} {currency_symbol}")