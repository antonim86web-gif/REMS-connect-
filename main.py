import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- FUNZIONE AGGIORNAMENTO DB ---
def aggiorna_struttura_db():
    conn = sqlite3.connect('rems_final_v12.db')
    c = conn.cursor()
    # Supporto per lo smarcamento rapido e fasce orarie
    try: c.execute("ALTER TABLE terapie ADD COLUMN mat INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE terapie ADD COLUMN pom INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE terapie ADD COLUMN tab INTEGER DEFAULT 0") # Al bisogno
    except: pass
    try: c.execute("ALTER TABLE eventi ADD COLUMN esito TEXT") # A per Assunto, R per Rifiutato
    except: pass
    conn.commit()
    conn.close()

aggiorna_struttura_db()

# --- FUNZIONI UTILITY ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def db_run(query, params=(), commit=False):
    with sqlite3.connect('rems_final_v12.db', check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if st.session_state.user_session else "SISTEMA"
    db_run("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
           (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio), True)

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v35.0", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .user-logged { color: #00ff00 !important; font-weight: 900; text-align: center; margin-bottom: 20px; }
    .section-banner { background-color: #1e3a8a; color: white; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
    
    /* Stile Smarcamento Rapido */
    .scroll-terapia { display: flex; overflow-x: auto; gap: 5px; padding: 10px; background: #f8f9fa; border-radius: 8px; border: 1px solid #ddd; }
    .quadratino { 
        min-width: 40px; height: 50px; border: 1px solid #ccc; border-radius: 4px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        background: white; font-size: 0.7rem;
    }
    .q-oggi { border: 2px solid #22c55e !important; background: #f0fdf4 !important; }
    .esito-a { color: #166534; font-weight: bold; }
    .esito-r { color: #991b1b; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- GESTIONE SESSIONE (Codice originale omesso per brevità, assumiamo logica esistente) ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

# [INSERIRE QUI LOGICA DI LOGIN ORIGINALE]
# Per test:
if not st.session_state.user_session:
    st.session_state.user_session = {"nome": "Admin", "cognome": "Test", "ruolo": "Admin", "uid": "admin"}

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- NAVIGAZIONE SIDEBAR ---
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto"])

# --- MODULO EQUIPE (IL CUORE DELLA MODIFICA) ---
if nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>GESTIONE OPERATIVA EQUIPE</h2></div>", unsafe_allow_html=True)
    
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        # LOGICA RUOLI ADATTIVA
        ruolo_effettivo = u['ruolo']
        
        # --- TAB INTERFACCIA ---
        t_inf, t_med, t_altri = st.tabs(["💊 KEEP INFERMIERE", "🩺 CLINICA MEDICA", "👥 ALTRE FIGURE"])

        # 1. KEEP INFERMIERE
        with t_inf:
            sub_ter, sub_par, sub_con = st.tabs(["Gestione Terapia", "Parametri", "Consegne"])
            
            with sub_ter:
                turno_att = st.selectbox("Turno di Smarcamento", ["Mattina (08-13)", "Pomeriggio (16-20)", "Al Bisogno (TAB)"])
                mappa_idx = {"Mattina (08-13)": 3, "Pomeriggio (16-20)": 4, "Al Bisogno (TAB)": 5}
                
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, tab FROM terapie WHERE p_id=?", (p_id,))
                
                for tid, f_nome, f_dose, f_mat, f_pom, f_tab in terapie:
                    # Mostra solo farmaci del turno selezionato
                    val_turno = f_mat if turno_att.startswith("Mat") else (f_pom if turno_att.startswith("Pom") else f_tab)
                    
                    if val_turno == 1:
                        st.write(f"**{f_nome}** - {f_dose}")
                        
                        # Recupero firme del mese corrente
                        mese_corr = get_now_it().strftime("%m/%Y")
                        firme = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                                       (p_id, f"%SOMM: {f_nome}%", f"%/{mese_corr}%"))
                        f_map = {int(d[0].split("/")[0]): {"e": d[1], "o": d[2]} for d in firme if d[0]}

                        # Griglia quadratini (Smarcamento visivo)
                        h = "<div class='scroll-terapia'>"
                        gg_mese = calendar.monthrange(get_now_it().year, get_now_it().month)[1]
                        for g in range(1, gg_mese + 1):
                            is_oggi = "q-oggi" if g == get_now_it().day else ""
                            info = f_map.get(g)
                            esito_txt = f"<span class='esito-{info['e'].lower()}'>{info['e']}</span>" if info else ""
                            h += f"<div class='quadratino {is_oggi}'><b>{g}</b>{esito_txt}</div>"
                        h += "</div>"
                        st.markdown(h, unsafe_allow_html=True)
                        
                        c1, c2 = st.columns(2)
                        if c1.button(f"✅ Conferma {f_nome}", key=f"ok_{tid}"):
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", 
                                   (p_id, get_now_it().strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM: {f_nome}", "Infermiere", firma_op, "A"), True)
