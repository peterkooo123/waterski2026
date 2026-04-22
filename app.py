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
    
    df = pd.read_csv(DB_FILE)
    
    # Premenovanie starých názvov na nové, ak existujú
    rename_map = {"Hodnota Počítadla": "Hodnota", "Počet Minút": "Počet"}
    df = df.rename(columns=rename_map)
    
    for c in cols:
        if c not in df.columns:
            df[c] = 0
            
    df["Dátum"] = df["Dátum"].astype(str)
    return df[cols]

if 'df_logs' not in st.session_state:
    st.session_state.df_logs = get_data()

if 'zvoleny_datum' not in st.session_state:
    st.session_state.zvoleny_datum = date.today()

zoznam_mien = load_names()

st.title("⛷️ Minúty 2026")

# --- FORMULÁR PRE NOVÝ ZÁPIS ---
with st.container(border=True):
    st.subheader("➕ Nový záznam")
    col1, col2 = st.columns([1, 1])
    with col1:
        vyber = st.selectbox("Meno lyžiara", ["---"] + zoznam_mien + ["+ Nové meno"])
        meno = st.text_input("Zadaj meno nového lyžiara") if vyber == "+ Nové meno" else vyber
    with col2:
        # Ponechávame "Počítadlo" ako názov v poli, ale ukladáme do stĺpca "Hodnota"
        aktualna_hodnota = st.number_input("Stav počítadla (3 miesta)", 0, 999, step=1)
    
    col3, col4 = st.columns([1, 1])
    with col3:
        tankovanie = st.checkbox("⛽ Tankovanie")
    with col4:
        litre = st.number_input("Litre", 0.0, 500.0, step=0.1) if tankovanie else 0.0

    if st.button("🚀 ULOŽIŤ ZÁZNAM", type="primary", use_container_width=True):
        if meno == "---" or not meno:
            st.error("Zadaj meno!")
        else:
            final_name = meno.strip()
            if vyber == "+ Nové meno": 
                save_new_name(final_name)
            
            # Výpočet rozdielu (minút) oproti poslednému záznamu v pamäti
            if not st.session_state.df_logs.empty:
                posledna_hodnota = int(st.session_state.df_logs.iloc[-1]["Hodnota"])
                if aktualna_hodnota < posledna_hodnota:
                    rozdiel = (1000 - posledna_hodnota) + aktualna_hodnota
                else:
                    rozdiel = aktualna_hodnota - posledna_hodnota
            else:
                rozdiel = 0

            novy_zapis = {
                "ID": int(datetime.now().timestamp()), 
                "Dátum": date.today().strftime("%Y-%m-%d"), 
                "Čas": datetime.now().strftime("%H:%M"), 
                "Meno": final_name, 
                "Hodnota": aktualna_hodnota, 
                "Počet": rozdiel, 
                "Litre": litre
            }
            
            st.session_state.df_logs = pd.concat([st.session_state.df_logs, pd.DataFrame([novy_zapis])], ignore_index=True)
            st.session_state.df_logs.to_csv(DB_FILE, index=False)
            st.success(f"Uložené: {rozdiel} minút")
            st.rerun()

# --- HISTÓRIA (Najnovšie hore) ---
st.divider()
st.session_state.zvoleny_datum = st.date_input("Zobraziť deň:", st.session_state.zvoleny_datum, key="calendar")
str_datum = st.session_state.zvoleny_datum.strftime("%Y-%m-%d")
zvoleny_mesiac_str = st.session_state.zvoleny_datum.strftime("%Y-%m")

display_df = st.session_state.df_logs[st.session_state.df_logs["Dátum"] == str_datum].copy()

if not display_df.empty:
    # --- TÁTO ČASŤ ZABEZPEČÍ NAJNOVŠIE HORE ---
    display_df = display_df.sort_values(by="ID", ascending=False)
    
    display_df["Zmazať"] = False
    edited_df = st.data_editor(
        display_df[["Čas", "Meno", "Hodnota", "Počet", "Litre", "Zmazať"]], 
        use_container_width=True, 
        hide_index=True,
        key="editor_history"
    )
    
    if any(edited_df["Zmazať"]):
        if st.button("🔥 POTVRDIŤ VYMAZANIE", type="primary", use_container_width=True):
            to_drop = edited_df.index[edited_df["Zmazať"]]
            st.session_state.df_logs = st.session_state.df_logs.drop(to_drop)
            st.session_state.df_logs.to_csv(DB_FILE, index=False)
            st.rerun()
else:
    st.info("Žiadne záznamy pre tento deň.")

# --- SUMÁR A STUPIENOK VÍŤAZOV ---
st.divider()
df_mesiac = st.session_state.df_logs[st.session_state.df_logs["Dátum"].str.startswith(zvoleny_mesiac_str)]

if not df_mesiac.empty:
    sumar_df = df_mesiac.groupby("Meno")[["Počet", "Litre"]].sum().sort_values(by="Počet", ascending=False).reset_index()
    st.subheader(f"🏆 Králi mesiaca ({zvoleny_mesiac_str})")
    
    top_3 = sumar_df.head(3)
    p = [top_3.iloc[i] if i < len(top_3) else None for i in range(3)]
    names = [x['Meno'] if x is not None else "" for x in p]
    mins = [int(x['Počet']) if x is not None else 0 for x in p]

    podium_html = f"""
    <div style="display: flex; align-items: flex-end; justify-content: center; height: 160px; font-family: sans-serif; padding-bottom: 20px;">
        <div style="text-align: center; margin: 0 5px;"><div style="font-size: 12px;">{names[1]}</div><div style="background: #C0C0C0; width: 60px; height: 60px; border-radius: 5px 5px 0 0; color: white; font-weight: bold; display: flex; align-items: center; justify-content: center; flex-direction: column;">2.<br><small>{mins[1]}m</small></div></div>
        <div style="text-align: center; margin: 0 5px;"><div style="font-size: 14px; font-weight: bold; color: #FFD700;">👑 {names[0]}</div><div style="background: #FFD700; width: 70px; height: 90px; border-radius: 5px 5px 0 0; color: white; font-weight: bold; font-size: 20px; display: flex; align-items: center; justify-content: center; flex-direction: column;">1.<br><small>{mins[0]}m</small></div></div>
        <div style="text-align: center; margin: 0 5px;"><div style="font-size: 12px;">{names[2]}</div><div style="background: #CD7F32; width: 60px; height: 40px; border-radius: 5px 5px 0 0; color: white; font-weight: bold; display: flex; align-items: center; justify-content: center; flex-direction: column;">3.<br><small>{mins[2]}m</small></div></div>
    </div>"""
    st.markdown(podium_html, unsafe_allow_html=True)
    st.table(sumar_df)

# --- EXPORT (Sidebar) ---
with st.sidebar:
    st.header("📥 Export")
    st.download_button(f"Stiahnuť {zvoleny_mesiac_str}", df_mesiac.to_csv(index=False).encode('utf-8'), f"export_{zvoleny_mesiac_str}.csv", "text/csv", use_container_width=True)
    st.download_button("Stiahnuť VŠETKO (Záloha)", st.session_state.df_logs.to_csv(index=False).encode('utf-8'), "zaloha.csv", "text/csv", use_container_width=True)
