import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Minúty 2026", layout="wide")

# --- PRIPOJENIE NA GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # Načítanie dát z Google Sheets (stĺpce A až G)
    return conn.read(ttl="0s")

def update_google_sheets(df):
    # Zapísanie celého DataFrame späť do tabuľky
    conn.update(data=df)

# --- LOGIKA PREPOČTU (Rovnaká ako predtým) ---
def recalculate_logic(df):
    if df.empty: return df
    df = df.sort_values(by=["Dátum", "Čas", "Hodnota"]).reset_index(drop=True)
    new_counts = []
    for i in range(len(df)):
        if i == 0: new_counts.append(0)
        else:
            akt, pred = int(df.at[i, "Hodnota"]), int(df.at[i-1, "Hodnota"])
            rozdiel = akt - pred
            if rozdiel < -5000: rozdiel += 10000
            elif rozdiel < 0: rozdiel = 0
            new_counts.append(rozdiel)
    df["Počet"] = new_counts
    return df

# --- NAČÍTANIE ---
df_logs = get_data()

st.title("⛷️ Minúty 2026 (Live Google DB)")

# --- FORMULÁR ---
with st.container(border=True):
    st.subheader("➕ Nový záznam")
    c1, c2, c3 = st.columns(3)
    with c1: d_z = st.date_input("Dátum", date.today())
    with c2: t_z = st.time_input("Čas", datetime.now().time())
    with c3: meno = st.text_input("Meno")
    
    hodn = st.number_input("Stav počítadla", 0, 9999, step=1)
    
    if st.button("🚀 ULOŽIŤ DO CLOUDU", use_container_width=True, type="primary"):
        if not meno:
            st.error("Zadaj meno!")
        else:
            novy = pd.DataFrame([{
                "ID": int(datetime.now().timestamp()),
                "Dátum": d_z.strftime("%Y-%m-%d"),
                "Čas": t_z.strftime("%H:%M"),
                "Meno": meno,
                "Hodnota": hodn,
                "Počet": 0,
                "Litre": 0
            }])
            df_final = pd.concat([df_logs, novy], ignore_index=True)
            df_final = recalculate_logic(df_final)
            update_google_sheets(df_final)
            st.success("Uložené do Google Sheets!")
            st.rerun()

# --- HISTÓRIA A EDITÁCIA ---
st.divider()
st.subheader("🕒 História")
if not df_logs.empty:
    # Zobraziť editor pre celú tabuľku
    edited_df = st.data_editor(df_logs, use_container_width=True, hide_index=True, num_rows="dynamic")
    
    if st.button("💾 SYNCHRONIZOVAŤ ZMENY"):
        df_recalc = recalculate_logic(edited_df)
        update_google_sheets(df_recalc)
        st.success("Všetko prepočítané a uložené!")
        st.rerun()
