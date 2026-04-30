import streamlit as st
import pandas as pd
from datetime import datetime, date
import os

# --- KONFIGURÁCIA ---
DB_FILE = "lyziari_data.csv"
NAMES_FILE = "Zoznam_mien.txt"

st.set_page_config(page_title="Minúty 2026", layout="wide", page_icon="⛷️")

def load_names():
    if not os.path.exists(NAMES_FILE):
        return ["Peter", "Zuzka", "Sofia"]
    with open(NAMES_FILE, "r", encoding="utf-8") as f:
        return sorted(list(set([line.strip() for line in f.readlines()])))

def save_new_name(new_name):
    if new_name.strip():
        with open(NAMES_FILE, "a", encoding="utf-8") as f:
            f.write(new_name.strip() + "\n")

def get_data():
    cols = ["ID", "Dátum", "Čas", "Meno", "Hodnota", "Počet", "Litre"]
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(DB_FILE)
        for col in cols:
            if col not in df.columns:
                df[col] = 0
        df["Hodnota"] = pd.to_numeric(df["Hodnota"], errors='coerce').fillna(0)
        df["Počet"] = pd.to_numeric(df["Počet"], errors='coerce').fillna(0)
        df["Dátum"] = df["Dátum"].astype(str)
        return df[cols]
    except:
        return pd.DataFrame(columns=cols)

def recalculate_all_logic(df):
    if df.empty: return df
    df = df.sort_values(by=["Dátum"]).reset_index(drop=True)
    def sort_day_group(group):
        high = group[group["Hodnota"] > 900]
        low = group[group["Hodnota"] < 100]
        if not high.empty and not low.empty:
            p1 = group[group["Hodnota"] >= 100].sort_values(by="Hodnota")
            p2 = group[group["Hodnota"] < 100].sort_values(by="Hodnota")
            return pd.concat([p1, p2])
        return group.sort_values(by="Hodnota")
    df = df.groupby("Dátum", group_keys=False).apply(sort_day_group).reset_index(drop=True)
    new_counts = []
    for i in range(len(df)):
        if i == 0: new_counts.append(0) 
        else:
            akt, pred = int(df.at[i, "Hodnota"]), int(df.at[i-1, "Hodnota"])
            rozdiel = akt - pred
            if pred > 900 and akt < 100: rozdiel = (1000 - pred) + akt
            elif rozdiel < 0: rozdiel = 0
            new_counts.append(rozdiel)
    df["Počet"] = new_counts
    return df

if 'df_logs' not in st.session_state:
    st.session_state.df_logs = get_data()

def reset_and_save(df):
    df = recalculate_all_logic(df)
    df.to_csv(DB_FILE, index=False)
    st.session_state.df_logs = df
    st.rerun()

st.title("⛷️ Minúty 2026")

with st.container(border=True):
    st.subheader("➕ Nový záznam")
    c1, c2, c3 = st.columns(3)
    with c1: d_z = st.date_input("Dátum", date.today())
    with c2: vyber = st.selectbox("Meno", ["---"] + load_names() + ["+ Nové meno"])
    with c3: hodn = st.number_input("Počítadlo (0-999)", 0, 999, step=1)
    
    f_name = st.text_input("✍️ Nové meno:") if vyber == "+ Nové meno" else vyber

    if st.button("🚀 ULOŽIŤ", use_container_width=True, type="primary"):
        if f_name in ["---", ""]: st.error("⚠️ Vyber meno!")
        else:
            if vyber == "+ Nové meno": save_new_name(f_name)
            novy = {"ID": int(datetime.now().timestamp()), "Dátum": d_z.strftime("%Y-%m-%d"), "Čas": datetime.now().strftime("%H:%M"), "Meno": f_name, "Hodnota": int(hodn), "Počet": 0, "Litre": 0}
            reset_and_save(pd.concat([st.session_state.df_logs, pd.DataFrame([novy])], ignore_index=True))

st.divider()
st.subheader("🕒 História dňa")
zvoleny_den = st.date_input("Filter pre deň:", date.today())
s_datum = zvoleny_den.strftime("%Y-%m-%d")
full_df = st.session_state.df_logs.copy()

if not full_df.empty:
    mask = full_df["Dátum"] == s_datum
    if not full_df[mask].empty:
        # OPRAVENÉ FORMÁTOVANIE TU:
        st.table(full_df[mask][["Čas", "Meno", "Hodnota", "Počet"]].iloc[::-1].style.format({"Hodnota": "{:.0f}", "Počet": "{:.0f}"}))
    else: st.info("Žiadne dáta.")

st.divider()
col_a, col_b = st.columns(2)
with col_a:
    z_mesiac = zvoleny_den.strftime("%Y-%m")
    st.subheader(f"📅 {z_mesiac}")
    df_m = full_df[full_df["Dátum"].str.startswith(z_mesiac)] if not full_df.empty else pd.DataFrame()
    if not df_m.empty:
        m_sum = df_m.groupby("Meno")["Počet"].sum().sort_values(ascending=False).reset_index()
        # OPRAVENÉ FORMÁTOVANIE TU:
        st.table(m_sum.style.format({"Počet": "{:.0f}"}))
    else: st.write("Žiadne dáta.")

with col_b:
    st.subheader("🏆 Celkovo")
    if not full_df.empty:
        c_sum = full_df.groupby("Meno")["Počet"].sum().sort_values(ascending=False).reset_index()
        # OPRAVENÉ FORMÁTOVANIE TU:
        st.table(c_sum.style.format({"Počet": "{:.0f}"}))

with st.sidebar:
    st.download_button("💾 Stiahnuť CSV", st.session_state.df_logs.to_csv(index=False).encode('utf-8'), "lyziari_data.csv")
