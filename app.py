import streamlit as st
import pandas as pd
from datetime import datetime, date
import os

# --- KONFIGURÁCIA ---
DB_FILE = "lyziari_data.csv"
NAMES_FILE = "Zoznam_mien.txt"

st.set_page_config(page_title="Minúty 2026", layout="wide", page_icon="⛷️")

# --- FUNKCIE PRE DÁTA ---
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
    df = pd.read_csv(DB_FILE)
    df["Dátum"] = df["Dátum"].astype(str)
    df["Hodnota"] = pd.to_numeric(df["Hodnota"], errors='coerce').fillna(0).astype(int)
    return df[cols]

# --- MOTOR PRE DYNAMICKÝ PREPOČET (S OŠETRENÍM PRETEČENIA) ---
def recalculate_logic(df):
    if df.empty:
        return df
    
    # Zoradenie: 1. Dátum, 2. Čas, 3. Hodnota
    # Toto zabezpečí správne poradie aj pri pretečení počítadla cez polnoc/cez nulu
    df = df.sort_values(by=["Dátum", "Čas", "Hodnota"]).reset_index(drop=True)
    
    new_counts = []
    for i in range(len(df)):
        if i == 0:
            new_counts.append(0) 
        else:
            aktualna = int(df.at[i, "Hodnota"])
            predchadzajuca = int(df.at[i-1, "Hodnota"])
            
            rozdiel = aktualna - predchadzajuca
            
            # DETEKCIA PRETEČENIA (napr. 9998 -> 0002)
            # Ak je nová hodnota menšia o viac ako 5000, predpokladáme, že počítadlo "pretočilo"
            if rozdiel < -5000:
                rozdiel += 10000
            elif rozdiel < 0:
                # Ak je to malý skok dozadu (chyba v zápise), dáme 0, aby to neskazilo sumár
                rozdiel = 0
                
            new_counts.append(rozdiel)
            
    df["Počet"] = new_counts
    return df

# --- INICIALIZÁCIA ---
if 'df_logs' not in st.session_state:
    st.session_state.df_logs = get_data()

if 'form_reset_key' not in st.session_state:
    st.session_state.form_reset_key = 0

def reset_and_save(df):
    df = recalculate_logic(df)
    df.to_csv(DB_FILE, index=False)
    st.session_state.df_logs = df
    st.session_state.form_reset_key += 1
    st.rerun()

zoznam_mien = load_names()

st.title("⛷️ Minúty 2026")

# --- FORMULÁR ---
with st.container(border=True):
    st.subheader("➕ Nový záznam")
    k = st.session_state.form_reset_key
    
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1: d_z = st.date_input("Dátum", date.today(), key=f"d_{k}")
    with c2: t_z = st.time_input("Čas", datetime.now().time(), key=f"t_{k}")
    with c3: vyb = st.selectbox("Meno", ["---"] + zoznam_mien + ["+ Nové meno"], key=f"s_{k}")
    
    f_name = ""
    if vyb == "+ Nové meno":
        f_name = st.text_input("✍️ Meno nového lyžiara:", key=f"n_{k}").strip()
    else:
        f_name = vyb

    st.divider()
    
    ch1, ch2 = st.columns(2)
    with ch1:
        hodn = st.number_input("Stav počítadla (4 miesta)", 0, 9999, step=1, key=f"v_{k}")
    with ch2:
        st.write("⛽ Tankovanie")
        t20, t40 = st.checkbox("20 L", key=f"t2_{k}"), st.checkbox("40 L", key=f"t4_{k}")

    if st.button("🚀 ULOŽIŤ ZÁZNAM", use_container_width=True, type="primary"):
        if f_name in ["---", ""]:
            st.error("⚠️ Zadaj meno!")
        else:
            if vyb == "+ Nové meno": save_new_name(f_name)
            litrov = (20 if t20 else 0) + (40 if t40 else 0)
            novy = {
                "ID": int(datetime.now().timestamp()), 
                "Dátum": d_z.strftime("%Y-%m-%d"), 
                "Čas": t_z.strftime("%H:%M"), 
                "Meno": f_name, 
                "Hodnota": hodn, 
                "Počet": 0, 
                "Litre": litrov
            }
            reset_and_save(pd.concat([st.session_state.df_logs, pd.DataFrame([novy])], ignore_index=True))

# --- HISTÓRIA ---
st.divider()
st.subheader("🕒 História")

zvoleny_den = st.date_input("Zobraziť deň:", date.today())
s_datum = zvoleny_den.strftime("%Y-%m-%d")

f_df = st.session_state.df_logs.copy()
f_df = f_df.sort_values(by=["Dátum", "Čas", "Hodnota"], ascending=[False, False, False])
f_df["Zmazať"] = False

mask = f_df["Dátum"] == s_datum
if not f_df[mask].empty:
    ed_df = st.data_editor(
        f_df[mask][["Čas", "Meno", "Hodnota", "Počet", "Litre", "Zmazať"]],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic"
    )
    
    if st.button("💾 ULOŽIŤ ZMENY"):
        ostatne = f_df[~mask].drop(columns=["Zmazať"])
        upravene = ed_df[ed_df["Zmazať"] == False].drop(columns=["Zmazať"])
        upravene["Dátum"] = s_datum
        # Oprava chýbajúcich stĺpcov pri manuálnom pridaní riadku
        if "ID" not in upravene.columns:
            upravene["ID"] = [int(datetime.now().timestamp()) + i for i in range(len(upravene))]
        
        reset_and_save(pd.concat([ostatne, upravene], ignore_index=True))
else:
    st.info("Žiadne dáta pre tento deň.")

# --- SUMÁR ---
z_mes = zvoleny_den.strftime("%Y-%m")
df_m = st.session_state.df_logs[st.session_state.df_logs["Dátum"].str.startswith(z_mes)]
if not df_m.empty:
    st.divider()
    sum_df = df_m.groupby("Meno")["Počet"].sum().sort_values(ascending=False).reset_index()
    st.subheader(f"🏆 Sumár za mesiac {z_mes}")
    st.table(sum_df)

with st.sidebar:
    st.header("📥 Export")
    st.download_button("Export CSV", st.session_state.df_logs.to_csv(index=False).encode('utf-8'), "lyziari.csv", "text/csv")
