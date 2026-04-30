import streamlit as st
import pandas as pd
from datetime import datetime, date, time
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
    # Zabezpečíme, aby ID bolo číslo kvôli sortovaniu
    df["ID"] = df["ID"].astype(int)
    return df[cols]

# --- MOTOR PRE DYNAMICKÝ PREPOČET ---
def recalculate_all_data(df):
    if df.empty:
        return df
    
    # 1. Oprava chýbajúcich ID (ak niekto pridal riadok v tabuľke manuálne)
    if df["ID"].isnull().any() or (df["ID"] == 0).any():
        for idx in df.index:
            if pd.isnull(df.at[idx, "ID"]) or df.at[idx, "ID"] == 0:
                # Vytvoríme ID z dátumu a času daného riadku
                try:
                    dt_str = f"{df.at[idx, 'Dátum']} {df.at[idx, 'Čas']}"
                    dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                    df.at[idx, "ID"] = int(dt_obj.timestamp())
                except:
                    df.at[idx, "ID"] = int(datetime.now().timestamp())

    # 2. Zoradenie podľa času (Vloženie medzi riadky)
    df = df.sort_values(by=["Dátum", "Čas", "ID"]).reset_index(drop=True)
    
    # 3. Prepočet minút
    new_counts = []
    for i in range(len(df)):
        if i == 0:
            new_counts.append(0) 
        else:
            try:
                aktualna = int(df.at[i, "Hodnota"])
                predchadzajuca = int(df.at[i-1, "Hodnota"])
                rozdiel = aktualna - predchadzajuca
                if rozdiel < 0: rozdiel += 10000
                new_counts.append(rozdiel)
            except:
                new_counts.append(0)
            
    df["Počet"] = new_counts
    return df

# --- INICIALIZÁCIA ---
if 'df_logs' not in st.session_state:
    st.session_state.df_logs = get_data()

if 'form_reset_key' not in st.session_state:
    st.session_state.form_reset_key = 0

def reset_and_save(df):
    df = recalculate_all_data(df)
    df.to_csv(DB_FILE, index=False)
    st.session_state.df_logs = df
    st.session_state.form_reset_key += 1
    st.rerun()

zoznam_mien = load_names()

st.title("⛷️ Minúty 2026")

# --- FORMULÁR (Štandardný zápis) ---
with st.container(border=True):
    st.subheader("➕ Nový záznam")
    k = st.session_state.form_reset_key
    
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1: dat_z = st.date_input("Dátum", date.today(), key=f"d_{k}")
    with c2: cas_z = st.time_input("Čas", datetime.now().time(), key=f"t_{k}")
    with c3: vyb_m = st.selectbox("Meno", ["---"] + zoznam_mien + ["+ Nové meno"], key=f"s_{k}")
    
    f_name = ""
    if vyb_m == "+ Nové meno":
        f_name = st.text_input("✍️ Napíš meno:", key=f"nm_{k}").strip()
    else:
        f_name = vyb_m

    ch1, ch2 = st.columns(2)
    with ch1: akt_h = st.number_input("Stav počítadla", 0, 9999, step=1, key=f"v_{k}")
    with ch2:
        st.write("⛽ Tankovanie")
        t20, t40 = st.checkbox("20 L", key=f"t2_{k}"), st.checkbox("40 L", key=f"t4_{k}")

    if st.button("🚀 ULOŽIŤ ZÁZNAM", use_container_width=True, type="primary"):
        if f_name in ["---", ""]:
            st.error("⚠️ Vyber meno!")
        else:
            if vyb_m == "+ Nové meno": save_new_name(f_name)
            l = (20 if t20 else 0) + (40 if t40 else 0)
            c_dt = datetime.combine(dat_z, cas_z)
            n_riadok = {"ID": int(c_dt.timestamp()), "Dátum": dat_z.strftime("%Y-%m-%d"), "Čas": cas_z.strftime("%H:%M"), "Meno": f_name, "Hodnota": akt_h, "Počet": 0, "Litre": l}
            reset_and_save(pd.concat([st.session_state.df_logs, pd.DataFrame([n_riadok])], ignore_index=True))

# --- HISTÓRIA (Teraz s možnosťou pridávať riadky priamo v tabuľke) ---
st.divider()
st.subheader("🕒 História a rýchle opravy")
st.write("💾 *Tip: Ak chceš vložiť chýbajúci záznam, klikni na tlačidlo pod tabuľkou, vyplň ho a daj Uložiť.*")

z_dat = st.date_input("Filter dňa:", date.today(), key="h_cal")
s_dat = z_dat.strftime("%Y-%m-%d")

# Príprava dát pre editor
f_df = st.session_state.df_logs.copy()
f_df = f_df.sort_values(by=["Dátum", "Čas", "ID"], ascending=False)
f_df["Zmazať"] = False

mask = f_df["Dátum"] == s_dat
display_cols = ["Čas", "Meno", "Hodnota", "Počet", "Litre", "Zmazať"]

# EDITOR S DYNAMICKÝMI RIADKAMI
edited_df_view = st.data_editor(
    f_df[mask][display_cols],
    use_container_width=True,
    num_rows="dynamic", # TOTO UMOŽNÍ PRIDÁVAŤ RIADKY CEZ TLAČIDLO (+)
    hide_index=True,
    key="editor"
)

if st.button("💾 ULOŽIŤ ZMENY V HISTÓRII", use_container_width=True):
    # 1. Zoberieme všetky riadky, ktoré NIE SÚ z dnešného zobrazenia (ostatné dni)
    other_days = f_df[~mask].drop(columns=["Zmazať"])
    
    # 2. Zoberieme upravené dáta z editora
    new_day_data = edited_df_view[edited_df_view["Zmazať"] == False].drop(columns=["Zmazať"])
    new_day_data["Dátum"] = s_dat # Zabezpečíme, aby mali správny dátum
    
    # 3. Spojíme a prepočítame
    reset_and_save(pd.concat([other_days, new_day_data], ignore_index=True))

# --- SUMÁR ---
st.divider()
z_mes = z_dat.strftime("%Y-%m")
df_m = st.session_state.df_logs[st.session_state.df_logs["Dátum"].str.startswith(z_mes)]
if not df_m.empty:
    sum_df = df_m.groupby("Meno")[["Počet", "Litre"]].sum().sort_values(by="Počet", ascending=False).reset_index()
    st.subheader(f"🏆 Králi mesiaca ({z_mes})")
    top_3 = sum_df.head(3)
    p = [top_3.iloc[i] if i < len(top_3) else None for i in range(3)]
    n, m = [x['Meno'] if x is not None else "" for x in p], [int(x['Počet']) if x is not None else 0 for x in p]
    pod_html = f"""<div style="display: flex; align-items: flex-end; justify-content: center; height: 100px;"><div style="text-align: center; margin: 0 5px;">{n[1]}<br><div style="background: silver; width: 40px; height: 40px;">2</div>{m[1]}m</div><div style="text-align: center; margin: 0 5px;">👑{n[0]}<br><div style="background: gold; width: 40px; height: 60px;">1</div>{m[0]}m</div><div style="text-align: center; margin: 0 5px;">{n[2]}<br><div style="background: #cd7f32; width: 40px; height: 30px;">3</div>{m[2]}m</div></div>"""
    st.markdown(pod_html, unsafe_allow_html=True)
    st.table(sum_df)

with st.sidebar:
    st.header("📥 Export")
    st.download_button("Záloha (CSV)", st.session_state.df_logs.to_csv(index=False).encode('utf-8'), "lyziari.csv", "text/csv", use_container_width=True)
