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
# Database setup
# -------------------------------
db_file = "crypto_prices.db"
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Create table for storing slider ranges per coin
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
# 2️⃣ Dropdown to select coin
# -------------------------------
selected_coin = st.selectbox("Select cryptocurrency to display", options=available_coins, index=0)

# -------------------------------
# 3️⃣ Load coin data
# -------------------------------
df = pd.read_sql_query(f"SELECT * FROM {selected_coin}_prices", conn)
df['timestamp'] = pd.to_datetime(df['timestamp'])
x_vals = np.arange(len(df))

timestamps_sec = df['timestamp'].astype('int64') // 1_000_000_000
min_time, max_time = int(timestamps_sec.min()), int(timestamps_sec.max())

# -------------------------------
# 4️⃣ Load previous slider positions from DB
# -------------------------------
cursor.execute("SELECT regression_start, regression_end, mean_start, mean_end FROM coin_ranges WHERE coin=?", (selected_coin,))
row = cursor.fetchone()
if row:
    reg_start_default, reg_end_default, mean_start_default, mean_end_default = row
else:
    reg_start_default, reg_end_default = min_time, max_time
    mean_start_default, mean_end_default = min_time, max_time

# -------------------------------
# 5️⃣ Regression slider (date range)
# -------------------------------
st.sidebar.header(f"{selected_coin} Regression Control (Date Range)")
regression_range_sec = st.sidebar.slider(
    "Select date range for regression",
    min_value=min_time,
    max_value=max_time,
    value=(reg_start_default, reg_end_default),
    format="YYYY-MM-DD",
    key=f"{selected_coin}_regression_range"
)
reg_start_dt = pd.to_datetime(regression_range_sec[0], unit='s')
reg_end_dt = pd.to_datetime(regression_range_sec[1], unit='s')
reg_start_idx = (df['timestamp'] - reg_start_dt).abs().idxmin()
reg_end_idx = (df['timestamp'] - reg_end_dt).abs().idxmin()
df_reg = df.iloc[reg_start_idx:reg_end_idx+1]

X = np.arange(len(df_reg)).reshape(-1, 1)
y = df_reg['close'].values
reg = LinearRegression().fit(X, y)
reg_line = reg.predict(np.arange(len(df)).reshape(-1, 1))

# -------------------------------
# 6️⃣ Mean slider (date range)
# -------------------------------
st.sidebar.header(f"{selected_coin} Range for Mean Calculation")
mean_range_sec = st.sidebar.slider(
    "Select date range for mean calculation",
    min_value=min_time,
    max_value=max_time,
    value=(mean_start_default, mean_end_default),
    format="YYYY-MM-DD",
    key=f"{selected_coin}_mean_range"
)
mean_start_dt = pd.to_datetime(mean_range_sec[0], unit='s')
mean_end_dt = pd.to_datetime(mean_range_sec[1], unit='s')
mean_start_idx = (df['timestamp'] - mean_start_dt).abs().idxmin()
mean_end_idx = (df['timestamp'] - mean_end_dt).abs().idxmin()
df_mean_range = df.iloc[mean_start_idx:mean_end_idx+1]
mean_range = df_mean_range['close'].mean()

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
""", (selected_coin, int(regression_range_sec[0]), int(regression_range_sec[1]),
      int(mean_range_sec[0]), int(mean_range_sec[1])))
conn.commit()

# -------------------------------
# 8️⃣ Plot chart
# -------------------------------
fig = px.line(df, x="timestamp", y="close",
              labels={"close":"Price (USD)", "timestamp":"Date"},
              title=f"{selected_coin.upper()} Price - All Time")

# Regression line
fig.add_trace(go.Scatter(
    x=df['timestamp'],
    y=reg_line,
    mode='lines',
    line=dict(color='orange', dash='dash'),
    name=f"Regression ({reg_start_dt.date()} → {reg_end_dt.date()})"
))

# Regression range markers
fig.add_trace(go.Scatter(
    x=[df['timestamp'].iloc[reg_start_idx]], y=[df['close'].iloc[reg_start_idx]],
    mode='markers', marker=dict(color='orange', size=20),
    name='Regression Start'
))
fig.add_trace(go.Scatter(
    x=[df['timestamp'].iloc[reg_end_idx]], y=[df['close'].iloc[reg_end_idx]],
    mode='markers', marker=dict(color='darkorange', size=20),
    name='Regression End'
))

# Mean range markers
fig.add_trace(go.Scatter(
    x=[df['timestamp'].iloc[mean_start_idx]], y=[df['close'].iloc[mean_start_idx]],
    mode='markers', marker=dict(color='cyan', size=12),
    name='Mean Range Start'
))
fig.add_trace(go.Scatter(
    x=[df['timestamp'].iloc[mean_end_idx]], y=[df['close'].iloc[mean_end_idx]],
    mode='markers', marker=dict(color='darkcyan', size=12),
    name='Mean Range End'
))

# Mean line
fig.add_hline(
    y=mean_range, line_dash="dash", line_color="yellow",
    annotation_text=f"Mean ({df['timestamp'].iloc[mean_start_idx].date()} → {df['timestamp'].iloc[mean_end_idx].date()})",
    annotation_position="top left"
)

# Hardcoded multiplier lines
multiplier = multipliers.get(selected_coin.upper(), 1.5)
fig.add_hline(
    y=mean_range * multiplier,
    line_dash="dot", line_color="red",
    annotation_text=f"Mean × {multiplier} = {mean_range*multiplier:.2f}",
    annotation_position="bottom left"
)
fig.add_hline(
    y=mean_range / multiplier,
    line_dash="dot", line_color="green",
    annotation_text=f"Mean ÷ {multiplier} = {mean_range/multiplier:.2f}",
    annotation_position="top left"
)

fig.update_layout(template="plotly_dark", hovermode="x unified")
fig.update_xaxes(rangeslider_visible=True)
st.plotly_chart(fig, use_container_width=True)