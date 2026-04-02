import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect ELITE", layout="wide")

st.markdown("""
    <style>
    .scroll-giorni { 
        display: flex; overflow-x: auto; gap: 8px; padding: 15px 5px;
        background: #f8f9fa; border-radius: 10px; margin-bottom: 15px;
        border: 1px solid #e9ecef;
    }
    .quadratino {
        min-width: 40px; height: 50px; border-radius: 8px; 
        display: flex; flex-direction: column; align-items: center; 
        justify-content: center; border: 1px solid #dee2e6; background: white;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
    }
    .oggi-attivo { border: 3px solid #1e3a8a !important; background-color: #fff9c4 !important; font-weight: bold; }
    .farmaco-label { font-size: 1.2rem; font-weight: 800; color: #1e3a8a; margin-top: 15px; }
    .info-dose { color: #555; font-size: 1rem; margin-bottom: 5px; font-style: italic; }
    /* Forza il popover a non essere tagliato */
    div[data-testid="stPopover"] { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE ---
DB_NAME = "rems_final_v12.db"
def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            return cursor.fetchall()
        except Exception as e:
            st.error(f"Errore: {e}")
            return []

# --- LOGICA FIRMA ---
def registra_firma(p_id, farmaco, turno, esito):
    ora = datetime.now().strftime("%d/%m/%Y %H:%M")
    db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
           (p_id, ora, f"✔️ SOMM ({turno}): {farmaco}", "Infermiere", "Op", esito), commit=True)
    st.rerun()

# --- RENDERING SMARCAMENTO ---
def mostra_farmaci_selettivi(p_id, farmaci, turno_selezionato):
    mappa_chiavi = {
        "Mattina (08:00 - 13:00)": ["MAT", "POM"],
        "Pomeriggio/Notte (16:00 - 20:00)": ["POM", "NOT"],
        "TAB (Al Bisogno)": ["TAB"]
    }
    indici = {"MAT": 3, "POM": 4, "NOT": 5, "TAB": 6}
    
    chiavi_attive = mappa_chiavi[turno_selezionato]
    f_filtrati = []
    for f in farmaci:
        for k in chiavi_attive:
            if f[indici[k]] == 1: f_filtrati.append((f, k))

    if not f_filtrati:
        st.info("Nessuna terapia prevista per questo orario.")
        return

    oggi = datetime.now()
    giorni_mese = calendar.monthrange(oggi.year, oggi.month)[1]
    mese_corrente = oggi.strftime("%m/%Y")

    for f_data, t_key in f_filtrati:
        f_id, f_nome, f_dose = f_data[0], f_data[1], f_data[2]
        
        # Intestazione Farmaco
        st.markdown(f"<div class='farmaco-label'>{f_nome} <span style='font-size:0.8rem; color:gray;'>[{t_key}]</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='info-dose'>{f_dose}</div>", unsafe_allow_html=True)
        
        # Recupero firme
        firme = db_run("SELECT data, esito FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                       (p_id, f"%({t_key}): {f_nome}%", f"%/{mese_corrente}%"))
        firme_map = {int(d[0].split("/")[0]): d[1] for d in firme if d[1]}

        # Striscia dei giorni
        html_giorni = "<div class='scroll-giorni'>"
        for d in range(1, giorni_mese + 1):
            esito = firme_map.get(d, "")
            is_today = "oggi-attivo" if d == oggi.day else ""
            color = "green" if esito == "A" else ("red" if esito == "R" else "#888")
            bg = "#dcfce7" if esito == "A" else ("#fee2e2" if esito == "R" else "white")
            html_giorni += f"<div class='quadratino {is_today}' style='background:{bg}; color:{color};'><span style='font-size:10px;'>{d}</span><b>{esito if esito else '-'}</b></div>"
        html_giorni += "</div>"
        st.markdown(html_giorni, unsafe_allow_html=True)

        # IL POP-UP (POPOVER) PER LA FIRMA
        if oggi.day not in firme_map:
            with st.popover(f"✍️ Firma Somministrazione: {f_nome}"):
                st.write(f"Conferma per oggi ({oggi.day}/{oggi.month})")
                c1, c2 = st.columns(2)
                if c1.button("✅ ASSUNTO (A)", key=f"A_{f_id}_{t_key}", use_container_width=True):
                    registra_firma(p_id, f_nome, t_key, "A")
                if c2.button("❌ RIFIUTATO (R)", key=f"R_{f_id}_{t_key}", use_container_width=True):
                    registra_firma(p_id, f_nome, t_key, "R")
        else:
            st.success(f"Smarcato correttamente: {firme_map[oggi.day]}")
        st.divider()

# --- INTERFACCIA PRINCIPALE ---
p_data = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
if p_data:
    st.sidebar.title("🏥 REMS Menu")
    sel_p = st.sidebar.selectbox("Paziente", [p[1] for p in p_data])
    p_id = [p[0] for p in p_data if p[1] == sel_p][0]

    tab_inf, tab_med = st.tabs(["💊 REGISTRO SMARCAMENTO", "🩺 PRESCRIZIONE MEDICA"])

    with tab_inf:
        st.subheader(f"Paziente: {sel_p}")
        scelta_turno = st.selectbox("Seleziona il tuo turno", 
                                    ["Mattina (08:00 - 13:00)", 
                                     "Pomeriggio/Notte (16:00 - 20:00)", 
                                     "TAB (Al Bisogno)"])
        
        farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
        if farmaci:
            mostra_farmaci_selettivi(p_id, farmaci, scelta_turno)
        else:
            st.info("Nessuna terapia attiva.")

    with tab_med:
        with st.form("med_form"):
            st.write("### 🩺 Nuova Prescrizione")
            f = st.text_input("Nome Farmaco")
            d = st.text_input("Dosaggio")
            o = st.selectbox("Orario", ["MATTINO (08:00)", "POMERIGGIO (16:00)", "NOTTE (20:00)", "TAB (Al Bisogno)"])
            if st.form_submit_button("Registra Farmaco"):
                m, p, n, tsu = (1,0,0,0) if "MAT" in o else ((0,1,0,0) if "POM" in o else ((0,0,1,0) if "NOT" in o else (0,0,0,1)))
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, is_prn) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, tsu), commit=True)
                st.rerun()
