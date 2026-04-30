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
    cols = ["ID", "Dátum", "Meno", "Hodnota", "Počet", "Litre"]
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(DB_FILE)
    df["Dátum"] = df["Dátum"].astype(str)
    df["Hodnota"] = pd.to_numeric(df["Hodnota"], errors='coerce').fillna(0).astype(int)
    return df[[c for c in cols if c in df.columns]]

# --- MOTOR PRE DYNAMICKÝ PREPOČET (3-MIESTNE POČÍTADLO) ---
def recalculate_logic(df):
    if df.empty:
        return df
    
    # Kľúčová zmena: Zoradenie len podľa Dátumu a Hodnoty (vzostupne)
    df = df.sort_values(by=["Dátum", "Hodnota"]).reset_index(drop=True)
    
    new_counts = []
    for i in range(len(df)):
        if i == 0:
            new_counts.append(0) 
        else:
            aktualna = int(df.at[i, "Hodnota"])
            predchadzajuca = int(df.at[i-1, "Hodnota"])
            
            # Pravidlo pre pretečenie: ak ideme z vysokej hodnoty (>900) na nízku
            if aktualna < predchadzajuca:
                if predchadzajuca > 900 and aktualna < 100:
                    # Výpočet cez pretečenie (napr. 990 -> 10: (1000 - 990) + 10 = 20)
                    rozdiel = (1000 - predchadzajuca) + aktualna
                else:
                    # Ak je to len chyba (nižšie číslo bez pretečenia), zapíšeme 0
                    rozdiel = 0
            else:
                rozdiel = aktualna - predchadzajuca
                
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
    
    c1, c2 = st.columns(2)
    with c1: d_z = st.date_input("Dátum", date.today(), key=f"d_{k}")
    with c2: vyb = st.selectbox("Meno", ["---"] + zoznam_mien + ["+ Nové meno"], key=f"s_{k}")
    
    f_name = st.text_input("✍️ Meno nového lyžiara:", key=f"n_{k}").strip() if vyb == "+ Nové meno" else vyb

    st.divider()
    
    ch1, ch2 = st.columns(2)
    with ch1:
        # Nastavené na 3 miesta (0-999)
        hodn = st.number_input("Stav počítadla (posledné 3 číslice)", 0, 999, step=1, key=f"v_{k}", format="%03d")
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
                "Meno": f_name, 
                "Hodnota": hodn, 
                "Počet": 0, 
                "Litre": litrov
            }
            # Pridáme nový záznam a spustíme logiku zoradenia a prepočtu
            reset_and_save(pd.concat([st.session_state.df_logs, pd.DataFrame([novy])], ignore_index=True))

# --- HISTÓRIA ---
st.divider()
st.subheader("🕒 História")

zvoleny_den = st.date_input("Zobraziť deň:", date.today())
s_datum = zvoleny_den.strftime("%Y-%m-%d")

f_df = st.session_state.df_logs.copy()
# Radenie v prehľade: najnovšie (najvyššie hodnoty) hore
f_df = f_df.sort_values(by=["Dátum", "Hodnota"], ascending=[False, False])
f_df["Zmazať"] = False

mask = f_df["Dátum"] == s_datum
if not f_df[mask].empty:
    ed_df = st.data_editor(
        f_df[mask][["Meno", "Hodnota", "Počet", "Litre", "Zmazať"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Hodnota": st.column_config.NumberColumn(format="%03d")
        }
    )
    
    if st.button("💾 ULOŽIŤ ZMENY"):
        ostatne = f_df[~mask].drop(columns=["Zmazať"])
        upravene = ed_df[ed_df["Zmazať"] == False].drop(columns=["Zmazať"])
        upravene["Dátum"] = s_datum
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
