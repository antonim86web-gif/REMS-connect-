import streamlit as st
import sqlite3
import calendar
from datetime import datetime

# --- CONFIGURAZIONE E STILE ---
st.set_page_config(page_title="REMS Connect ELITE", layout="wide")

st.markdown("""
    <style>
    .scroll-giorni { 
        display: flex; overflow-x: auto; gap: 6px; padding: 15px 8px;
        background: #f1f3f5; border-radius: 10px; margin-bottom: 10px;
    }
    .quadratino {
        min-width: 38px; height: 50px; border-radius: 6px; 
        display: flex; flex-direction: column; align-items: center; 
        justify-content: center; border: 1px solid #ced4da; background: white;
    }
    .oggi-attivo { border: 3px solid #1e3a8a !important; background-color: #fff9c4 !important; }
    .farmaco-label { font-size: 1.2rem; font-weight: 700; color: #1e3a8a; margin-top: 10px; }
    .info-dose { color: #666; font-size: 0.95rem; margin-bottom: 10px; }
    .sez-turno { background: #1e3a8a; color: white; padding: 10px; border-radius: 8px; margin-bottom: 20px; text-align: center; font-weight: bold; }
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

# --- LOGICA CORE ---
def registra_firma(p_id, farmaco, turno, esito):
    ora = datetime.now().strftime("%d/%m/%Y %H:%M")
    db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
           (p_id, ora, f"✔️ SOMM ({turno}): {farmaco}", "Infermiere", "Op", esito), commit=True)
    st.rerun()

def mostra_farmaci_selettivi(p_id, farmaci, turno_selezionato):
    # Mapping per filtrare i farmaci dal DB
    mappa_chiavi = {
        "Mattina (08:00 - 13:00)": ["MAT", "POM"], # Uniamo i due blocchi come chiesto
        "Pomeriggio/Notte (16:00 - 20:00)": ["POM", "NOT"],
        "TAB (Al Bisogno)": ["TAB"]
    }
    
    # Identifichiamo quali indici della tupla farmaco controllare
    # farmaco = (id_u, nome, dose, mat, pom, nott, is_prn)
    indici = {"MAT": 3, "POM": 4, "NOT": 5, "TAB": 6}
    
    f_filtrati = []
    chiavi_attive = mappa_chiavi[turno_selezionato]
    
    for f in farmaci:
        for k in chiavi_attive:
            if f[indici[k]] == 1:
                f_filtrati.append((f, k)) # Salviamo il farmaco e il turno specifico

    if not f_filtrati:
        st.info(f"Nessun farmaco previsto per: {turno_selezionato}")
        return

    st.markdown(f"<div class='sez-turno'>Visualizzazione: {turno_selezionato}</div>", unsafe_allow_html=True)
    
    oggi = datetime.now()
    giorni_mese = calendar.monthrange(oggi.year, oggi.month)[1]
    mese_corrente = oggi.strftime("%m/%Y")

    for f_data, t_key in f_filtrati:
        f_id, f_nome, f_dose = f_data[0], f_data[1], f_data[2]
        
        st.markdown(f"<div class='farmaco-label'>{f_nome} <small style='color:orange;'>({t_key})</small></div><div class='info-dose'>{f_dose}</div>", unsafe_allow_html=True)
        
        firme = db_run("SELECT data, esito FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                       (p_id, f"%({t_key}): {f_nome}%", f"%/{mese_corrente}%"))
        firme_map = {int(d[0].split("/")[0]): d[1] for d in firme if d[1]}

        # Striscia Giorni
        html_giorni = "<div class='scroll-giorni'>"
        for d in range(1, giorni_mese + 1):
            esito = firme_map.get(d, "")
            is_today = "oggi-attivo" if d == oggi.day else ""
            color = "green" if esito == "A" else ("red" if esito == "R" else "#888")
            bg = "#dcfce7" if esito == "A" else ("#fee2e2" if esito == "R" else "white")
            html_giorni += f"<div class='quadratino {is_today}' style='background:{bg}; color:{color};'><span style='font-size:10px;'>{d}</span><b>{esito if esito else '-'}</b></div>"
        html_giorni += "</div>"
        st.markdown(html_giorni, unsafe_allow_html=True)

        # Bottoni Firma
        if oggi.day not in firme_map:
            c1, c2, c3 = st.columns([1, 1, 1])
            if c2.button(f"✅ ASSUNTO", key=f"A_{f_id}_{t_key}", use_container_width=True):
                registra_firma(p_id, f_nome, t_key, "A")
            if c3.button(f"❌ RIFIUTATO", key=f"R_{f_id}_{t_key}", use_container_width=True):
                registra_firma(p_id, f_nome, t_key, "R")
        else:
            st.success(f"Eseguito per oggi: {firme_map[oggi.day]}")
        st.divider()

# --- INTERFACCIA ---
p_data = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
if p_data:
    sel_p = st.sidebar.selectbox("👤 PAZIENTE", [p[1] for p in p_data])
    p_id = [p[0] for p in p_data if p[1] == sel_p][0]

    tab_inf, tab_med = st.tabs(["💊 REGISTRO INFERMIERE", "🩺 AREA MEDICA"])

    with tab_inf:
        # IL NUOVO MENÙ A TENDINA PER I TURNI
        scelta_turno = st.selectbox("🕒 SELEZIONA TURNO DI LAVORO", 
                                    ["Mattina (08:00 - 13:00)", 
                                     "Pomeriggio/Notte (16:00 - 20:00)", 
                                     "TAB (Al Bisogno)"])
        
        farmaci = db_run("SELECT id_u, farmaco, dose, mat, pom, nott, is_prn FROM terapie WHERE p_id=?", (p_id,))
        if farmaci:
            mostra_farmaci_selettivi(p_id, farmaci, scelta_turno)

    with tab_med:
        with st.form("med"):
            st.write("📝 Nuova Terapia")
            f = st.text_input("Farmaco")
            d = st.text_input("Dose")
            o = st.selectbox("Orario", ["MATTINO (08:00)", "POMERIGGIO (16:00)", "NOTTE (20:00)", "TAB (Al Bisogno)"])
            if st.form_submit_button("Salva"):
                m, p, n, tsu = (1,0,0,0) if "MAT" in o else ((0,1,0,0) if "POM" in o else ((0,0,1,0) if "NOT" in o else (0,0,0,1)))
                db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, is_prn) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, n, tsu), commit=True)
                st.rerun()
