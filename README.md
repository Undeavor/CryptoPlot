# Crypto Price Dashboard (Offline)

An **offline cryptocurrency price dashboard** built with **Streamlit** to visualize historical price data for multiple coins stored in a local SQLite database. This interactive dashboard allows analysis of trends, computation of mean prices, and regression-based predictions.

---

## Features

- **Multi-Coin Support**:  
  Load all available cryptocurrencies from a local SQLite database. Select the coin to visualize via a dropdown.

- **Interactive Price Charts**:  
  Plot historical price (`close`) vs. timestamp using Plotly. Includes hover info, zoom, and a range slider for navigation.

- **Regression Analysis**:  
  Apply linear regression to a custom date range. The regression line is displayed in orange with start and end points highlighted.

- **Mean Calculation**:  
  Calculate the mean price over a selected date range. The mean line is shown in yellow, with the range start and end points marked in cyan and magenta.

- **Multiplier Lines**:  
  Hardcoded multipliers per coin allow scaling the mean to visualize thresholds or target ranges. Lines above and below the mean are displayed in red and green.

- **Interactive Sliders**:  
  Sliders control both mean and regression ranges. Slider positions are **stored in the database per coin**, persisting user selections between sessions.

- **Offline Functionality**:  
  All price data is stored locally in SQLite. No internet connection is needed for historical data analysis.

---

## Technologies Used

- **Python 3.10+**
- **Streamlit** – interactive web app framework
- **Plotly Express & Graph Objects** – interactive plotting
- **Pandas & NumPy** – data manipulation
- **SQLite** – local database for price data and slider states
- **Scikit-learn** – linear regression

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/crypto-dashboard.git
cd crypto-dashboard
```

2. Install dependencies:

```bash
pip install streamlit pandas numpy plotly scikit-learn
```

3. Launch the dashboard


```bash
streamlit run dashboard.py
```
