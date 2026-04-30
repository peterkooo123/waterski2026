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

# --- UPRAVENÝ MOTOR: RADENIE A PREPOČET (3-CIFERNÉ + PRETOČENIE) ---
def recalculate_all_logic(df):
    if df.empty:
        return df
    
    # 1. Funkcia na správne zoradenie v rámci jedného dňa
    def sort_day_group(group):
        high_vals = group[group["Hodnota"] > 900]
        low_vals = group[group["Hodnota"] < 100]
        
        # Ak je v jeden deň záznam nad 900 aj pod 100, ide o pretočenie
        if not high_vals.empty and not low_vals.empty:
            # Rozdelíme na časť pred pretočením a po pretočení
            part1 = group[group["Hodnota"] >= 100].sort_values(by="Hodnota")
            part2 = group[group["Hodnota"] < 100].sort_values(by="Hodnota")
            return pd.concat([part1, part2])
        else:
            return group.sort_values(by="Hodnota")

    # Zoradenie podľa dátumu a následne inteligentne podľa hodnoty v rámci dňa
    df = df.groupby("Dátum", group_keys=False).apply(sort_day_group).reset_index(drop=True)
    
    # 2. Prepočet minút v novom poradí
    new_counts = []
    for i in range(len(df)):
        if i == 0:
            new_counts.append(0) 
        else:
            aktualna = int(df.at[i, "Hodnota"])
            predchadzajuca = int(df.at[i-1, "Hodnota"])
            
            rozdiel = aktualna - predchadzajuca
            
            # ŠPECIÁLNE PRAVIDLO PRETOČENIA: z >900 na <100
            if predchadzajuca > 900 and aktualna < 100:
                rozdiel = (1000 - predchadzajuca) + aktualna
            elif rozdiel < 0:
                rozdiel = 0 # Ošetrenie chýb (napr. niekto zadal nižšie číslo omylom)
                
            new_counts.append(rozdiel)
            
    df["Počet"] = new_counts
    return df

# --- INICIALIZÁCIA ---
if 'df_logs' not in st.session_state:
    st.session_state.df_logs = get_data()

if 'form_reset_key' not in st.session_state:
    st.session_state.form_reset_key = 0

def reset_and_save(df):
    df = recalculate_all_logic(df)
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
    
    col1, col2 = st.columns(2)
    with col1:
        d_zápisu = st.date_input("Dátum", date.today(), key=f"d_{k}")
    with col2:
        vyber = st.selectbox("Meno", ["---"] + zoznam_mien + ["+ Nové meno"], key=f"s_{k}")
    
    f_name = ""
    if vyber == "+ Nové meno":
        f_name = st.text_input("✍️ Nové meno:", key=f"n_{k}").strip()
        if st.button("Pridať do zoznamu", key=f"bn_{k}"):
            save_new_name(f_name)
            st.rerun()
    else:
        f_name = vyber

    st.divider()
    
    col3, col4 = st.columns(2)
    with col3:
        # ZMENA: Limit na 3 miesta (0-999)
        hodnota = st.number_input("Stav počítadla (3 miesta)", 0, 999, step=1, key=f"v_{k}")
    with col4:
        st.write("⛽ Tankovanie")
        t20 = st.checkbox("20 L", key=f"t20_{k}")
        t40 = st.checkbox("40 L", key=f"t40_{k}")

    if st.button("🚀 ULOŽIŤ A ZARADIŤ", use_container_width=True, type="primary"):
        if f_name in ["---", ""]:
            st.error("⚠️ Zadaj meno!")
        else:
            litrov = (20 if t20 else 0) + (40 if t40 else 0)
            novy = {
                "ID": int(datetime.now().timestamp()), 
                "Dátum": d_zápisu.strftime("%Y-%m-%d"), 
                "Čas": datetime.now().strftime("%H:%M"), 
                "Meno": f_name, 
                "Hodnota": hodnota, 
                "Počet": 0, 
                "Litre": litrov
            }
            reset_and_save(pd.concat([st.session_state.df_logs, pd.DataFrame([novy])], ignore_index=True))

# --- HISTÓRIA (Zoradená podľa počítadla) ---
st.divider()
st.subheader("🕒 História dňa")

zvoleny_den = st.date_input("Zobraziť deň:", date.today())
s_datum = zvoleny_den.strftime("%Y-%m-%d")

# Zobrazenie v poradí, v akom sú dáta v DF (už správne zoradené motorom)
full_df = st.session_state.df_logs.copy()
full_df["Zmazať"] = False

mask = full_df["Dátum"] == s_datum
if not full_df[mask].empty:
    # V zobrazení otočíme poradie (najnovšie hore), aby sa lepšie čítalo
    view_df = full_df[mask].iloc[::-1]
    
    ed_df = st.data_editor(
        view_df[["Hodnota", "Meno", "Počet", "Litre", "Čas", "Zmazať"]],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic"
    )
    
    if st.button("💾 ULOŽIŤ ZMENY A PREPOČÍTAŤ"):
        ostatne = full_df[~mask].drop(columns=["Zmazať"])
        upravene = ed_df[ed_df["Zmazať"] == False].drop(columns=["Zmazať"])
        upravene["Dátum"] = s_datum
        
        for idx in upravene.index:
            if "Čas" not in upravene.columns or pd.isnull(upravene.at[idx, "Čas"]):
                upravene.at[idx, "Čas"] = datetime.now().strftime("%H:%M")
            if "ID" not in upravene.columns:
                upravene.at[idx, "ID"] = int(datetime.now().timestamp()) + idx

        reset_and_save(pd.concat([ostatne, upravene], ignore_index=True))
else:
    st.info("Žiadne dáta.")

# --- SUMÁR ---
z_mesiac = zvoleny_den.strftime("%Y-%m")
df_m = st.session_state.df_logs[st.session_state.df_logs["Dátum"].str.startswith(z_mesiac)]
if not df_m.empty:
    st.divider()
    sum_df = df_m.groupby("Meno")["Počet"].sum().sort_values(ascending=False).reset_index()
    st.subheader(f"🏆 Top lyžiari - {z_mesiac}")
    st.table(sum_df)
