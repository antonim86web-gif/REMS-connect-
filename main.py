import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold;}
    .patient-header { background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 8px solid #1e3a8a; margin-bottom: 25px; }
    .allergy-alert { background: #fee2e2; color: #991b1b; padding: 8px 15px; border-radius: 6px; font-weight: bold; border: 1px solid #f87171; display: inline-block; }
    .diet-box { background: #fef9c3; color: #854d0e; padding: 8px 15px; border-radius: 6px; border: 1px solid #facc15; display: inline-block; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE (CON AUTO-RIPARAZIONE) ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        
        # Creazione tabella base pazienti
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        
        # AGGIORNAMENTO AUTOMATICO COLONNE (Risolve l'errore dello screenshot)
        cur.execute("PRAGMA table_info(pazienti)")
        esistenti = [col[1] for col in cur.fetchall()]
        nuove = {
            "data_nascita": "TEXT", "data_ingresso": "TEXT", "diagnosi": "TEXT",
            "allergie": "TEXT", "dieta": "TEXT", "giorno_lavatrice": "TEXT"
        }
        for col, tipo in nuove.items():
            if col not in esistenti:
                cur.execute(f"ALTER TABLE pazienti ADD COLUMN {col} {tipo}")
        
        # Tabella Terapie (Come da tua immagine 1)
        cur.execute("""CREATE TABLE IF NOT EXISTS terapie (
            row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            p_id INTEGER,
            data TEXT,
            farmaco TEXT,
            dosaggio TEXT,
            turni TEXT,
            medico TEXT
        )""")
        
        # Tabella Eventi e Soldi
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGICA DI ACCESSO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    pwd = st.text_input("Inserisci Codice Operatore", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]: st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. MENU NAVIGAZIONE ---
menu = st.sidebar.radio("MENU", ["Gestione Ingressi", "Area Clinica (Terapie)", "Diario e Monitoraggio"])

# --- 5. GESTIONE INGRESSI (Aggiunta/Modifica/Elimina) ---
if menu == "Gestione Ingressi":
    st.header("👥 Amministrazione Pazienti")
    
    with st.form("nuovo_ingresso"):
        st.subheader("Registra Nuovo Paziente")
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome e Cognome")
        d_nas = c2.date_input("Data di Nascita", value=date(1980,1,1))
        dia = st.text_area("Diagnosi")
        all = st.text_area("Allergie")
        diet = st.text_input("Dieta (es. Mediterranea)")
        gl = st.selectbox("Giorno Lavatrice", ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"])
        
        if st.form_submit_button("REGISTRA PAZIENTE"):
            db_run("""INSERT INTO pazienti (nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice) 
                      VALUES (?,?,?,?,?,?,?)""", 
                   (nome, d_nas.strftime("%d/%m/%Y"), date.today().strftime("%d/%m/%Y"), dia, all, diet, gl), True)
            st.success("Paziente registrato!")
            st.rerun()

# --- 6. AREA CLINICA (Visualizzazione Terapie Attive) ---
elif menu == "Area Clinica (Terapie)":
    pazienti = db_run("SELECT id, nome, diagnosi, allergie, dieta FROM pazienti")
    if pazienti:
        sel = st.selectbox("Seleziona Paziente", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == sel][0]
        p_info = [p for p in pazienti if p[1] == sel][0]

        # Intestazione con Allergie e Dieta
        st.markdown(f"""
        <div class="patient-header">
            <h3>{p_info[1].upper()}</h3>
            <p><b>Diagnosi:</b> {p_info[2]}</p>
            <span class="allergy-alert">⚠️ Allergie: {p_info[3]}</span>
            <span class="diet-box">🍽️ Dieta: {p_info[4]}</span>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("💊 Terapie Attive e Variazioni")
        
        # Form per aggiungere terapia
        with st.expander("➕ Aggiungi Nuova Terapia"):
            with st.form("add_terapia"):
                f = st.text_input("Farmaco")
                d = st.text_input("Dosaggio")
                t = st.text_input("Turni (es. M, P, N)")
                m = st.text_input("Medico")
                if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                    db_run("INSERT INTO terapie (p_id, data, farmaco, dosaggio, turni, medico) VALUES (?,?,?,?,?,?)",
                           (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), f, d, t, m), True)
                    st.rerun()

        # Visualizzazione Tabella (Stile Immagine 1)
        terapie = db_run("SELECT data, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=?", (p_id,))
        if terapie:
            for data, farm, dose, turni, med, rid in terapie:
                with st.container():
                    c1, c2, c3, c4, c5, c6 = st.columns([2,2,2,1,2,1])
                    c1.write(f"**DATA**\n{data}")
                    c2.write(f"**FARMACO**\n{farm}")
                    c3.write(f"**DOSAGGIO**\n{dose}")
                    c4.write(f"**TURNI**\n{turni}")
                    c5.write(f"**MEDICO**\n{med}")
                    if c6.button("Sospendi", key=f"susp_{rid}"):
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                        st.rerun()
                st.divider()
