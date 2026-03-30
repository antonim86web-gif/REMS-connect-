import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .patient-header { background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 8px solid #1e3a8a; margin-bottom: 25px; border: 1px solid #e2e8f0; }
    .allergy-alert { background: #fee2e2; color: #991b1b; padding: 8px 15px; border-radius: 6px; font-weight: bold; border: 1px solid #f87171; display: inline-block; }
    .diet-box { background: #fef9c3; color: #854d0e; padding: 8px 15px; border-radius: 6px; border: 1px solid #facc15; display: inline-block; }
    .custom-table {width: 100%; border-collapse: collapse; font-size: 0.85rem; background: white;}
    .custom-table th {background-color: #1e3a8a; color: white; padding: 10px; text-align: left; border: 1px solid #dee2e6;}
    .custom-table td {padding: 10px; border: 1px solid #dee2e6; vertical-align: middle;}
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: #ffffff; }
    .saldo-box { padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; margin-bottom:15px; }
    .entrata { color: #10b981; font-weight: bold; }
    .uscita { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE CON AUTO-RIPARAZIONE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        
        # Creazione tabella base
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        
        # FIX PER SMARTPHONE: Aggiunta automatica colonne se mancano
        cur.execute("PRAGMA table_info(pazienti)")
        esistenti = [col[1] for col in cur.fetchall()]
        nuove = {
            "data_nascita": "TEXT", "data_ingresso": "TEXT", "diagnosi": "TEXT",
            "allergie": "TEXT", "dieta": "TEXT", "giorno_lavatrice": "TEXT"
        }
        for col, tipo in nuove.items():
            if col not in esistenti:
                cur.execute(f"ALTER TABLE pazienti ADD COLUMN {col} {tipo}")
        
        # Altre tabelle
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Codice Accesso", type="password")
        if st.form_submit_button("ENTRA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Gestione Ingressi"])

# --- 5. GESTIONE INGRESSI (Aggiunta/Modifica/Elimina) ---
if menu == "Gestione Ingressi":
    st.subheader("⚙️ Gestione Pazienti")
    t1, t2 = st.tabs(["➕ Nuovo Paziente", "📝 Modifica/Elimina"])
    
    with t1:
        with st.form("add_p"):
            n = st.text_input("Nome e Cognome")
            dn = st.date_input("Data di Nascita", value=date(1980,1,1))
            di = st.date_input("Data Ingresso", value=date.today())
            dia = st.text_area("Diagnosi")
            all = st.text_area("Allergie")
            diet = st.text_input("Dieta")
            gl = st.selectbox("Lavatrice", GIORNI)
            if st.form_submit_button("SALVA"):
                db_run("INSERT INTO pazienti (nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice) VALUES (?,?,?,?,?,?,?)",
                       (n, dn.strftime("%d/%m/%Y"), di.strftime("%d/%m/%Y"), dia, all, diet, gl), True)
                st.rerun()
    
    with t2:
        paz = db_run("SELECT id, nome FROM pazienti")
        for pid, nome in paz:
            c1, c2 = st.columns([3,1])
            c1.write(nome)
            if c2.button("Elimina", key=f"del_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
                st.rerun()

# --- 6. EQUIPE (LOGICA CHE HAI COPIATO) ---
elif menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    paz_data = db_run("SELECT id, nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice FROM pazienti ORDER BY nome")
    
    if paz_data:
        sel_p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in paz_data])
        p_sel = [x for x in paz_data if x[1] == sel_p_nome][0]
        p_id = p_sel[0]

        # INTESTAZIONE CLINICA DETTAGLIATA
        st.markdown(f"""
        <div class="patient-header">
            <h3>{p_sel[1].upper()}</h3>
            <p>Nato il: <b>{p_sel[2]}</b> | Ingresso: <b>{p_sel[3]}</b> | Lavatrice: <b>{p_sel[7]}</b></p>
            <p><i>Diagnosi: {p_sel[4]}</i></p>
            <div style="margin-top:10px;">
                <span class="allergy-alert">⚠️ Allergie: {p_sel[5]}</span> &nbsp;
                <span class="diet-box">🍽️ Dieta: {p_sel[6]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if figura == "Psichiatra":
            # ... (Tua logica Psichiatra) ...
            st.subheader("📋 Gestione Terapie")
            with st.form("p_f"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                med = st.text_input("Medico")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, medico, data_prescr) VALUES (?,?,?,?,?)", 
                           (p_id, f, d, med, date.today().strftime("%d/%m/%Y")), True); st.rerun()

        elif figura == "Educatore":
            # ... (Tua logica Educatore/Contabilità) ...
            st.subheader("💰 Gestione Contabilità")
            storico = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([s[2] if s[3] == "Entrata" else -s[2] for s in storico])
            st.markdown(f'<div class="saldo-box"><h2>Saldo: € {saldo:.2f}</h2></div>', unsafe_allow_html=True)
            # (Resto della logica contabilità...)

# --- 7. MONITORAGGIO ---
elif menu == "Monitoraggio":
    for p_id, nome, dn, di, diag, all, diet, gl in db_run("SELECT * FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            st.write(f"**Diagnosi:** {diag}")
            st.write(f"**Allergie:** {all}")
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                h = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note:
                    h += f"<tr><td>{d}</td><td>{ru} ({op})</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
