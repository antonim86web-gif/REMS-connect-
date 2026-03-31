import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .patient-header { background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 8px solid #1e3a8a; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
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
        
        # Creazione tabella base se non esiste
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        
        # AUTO-RIPARAZIONE: Aggiunge le colonne mancanti se il DB è vecchio (Smartphone Fix)
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
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
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

# --- 5. GESTIONE INGRESSI (NUOVA SEZIONE COMPLETA) ---
if menu == "Gestione Ingressi":
    st.header("👥 Gestione Anagrafica Pazienti")
    t1, t2 = st.tabs(["➕ Nuovo Ingresso", "📝 Modifica/Elimina"])
    
    with t1:
        with st.form("f_ing"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nome e Cognome")
            dn = c2.date_input("Data di Nascita", value=date(1980,1,1))
            di = c1.date_input("Data Ingresso", value=date.today())
            gl = c2.selectbox("Giorno Lavatrice", GIORNI)
            dia = st.text_area("Diagnosi Clinica")
            all = st.text_area("Allergie / Intolleranze")
            diet = st.text_input("Dieta (es. Iposodica, Libera)")
            if st.form_submit_button("REGISTRA PAZIENTE"):
                db_run("INSERT INTO pazienti (nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice) VALUES (?,?,?,?,?,?,?)",
                       (n, dn.strftime("%d/%m/%Y"), di.strftime("%d/%m/%Y"), dia, all, diet, gl), True)
                st.success("Paziente registrato correttamente!"); st.rerun()

    with t2:
        paz = db_run("SELECT id, nome, diagnosi, allergie, dieta, giorno_lavatrice FROM pazienti ORDER BY nome")
        for pid, n, d, a, dt, g in paz:
            with st.expander(f"Modifica dati di {n}"):
                with st.form(f"m_{pid}"):
                    m_n = st.text_input("Nome", n)
                    m_dia = st.text_area("Diagnosi", d)
                    m_all = st.text_area("Allergie", a)
                    m_diet = st.text_input("Dieta", dt)
                    m_gl = st.selectbox("Lavatrice", GIORNI, index=GIORNI.index(g))
                    c_b1, c_b2 = st.columns(2)
                    if c_b1.form_submit_button("AGGIORNA"):
                        db_run("UPDATE pazienti SET nome=?, diagnosi=?, allergie=?, dieta=?, giorno_lavatrice=? WHERE id=?", (m_n, m_dia, m_all, m_diet, m_gl, pid), True); st.rerun()
                    if c_b2.form_submit_button("🗑️ ELIMINA"):
                        db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()

# --- 6. AREA EQUIPE ---
elif menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    p_lista = db_run("SELECT id, nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice FROM pazienti ORDER BY nome")
    
    if p_lista:
        sel_n = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_sel = [x for x in p_lista if x[1] == sel_n][0]
        p_id = p_sel[0]

        # INTESTAZIONE CLINICA (Sempre visibile)
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

        # --- SEZIONI OPERATIVE ---
        if figura == "Psichiatra":
            st.subheader("💊 Gestione Terapie")
            # ... (Logica Psichiatra) ...
            with st.form("p_f"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                tm, tp, tn = st.columns(3)[0].checkbox("M"), st.columns(3)[1].checkbox("P"), st.columns(3)[2].checkbox("N")
                med = st.text_input("Medico")
                if st.form_submit_button("REGISTRA"):
                    t_l = [s for s, b in zip(["M", "P", "N"], [tm, tp, tn]) if b]
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                           (p_id, f, d, ",".join(t_l), med, datetime.now().strftime("%d/%m/%y %H:%M")), True); st.rerun()

        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione")
            # ... (Logica Infermiere) ...
            
        elif figura == "Educatore":
            st.subheader("💰 Contabilità")
            storico = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([s[2] if s[3] == "Entrata" else -s[2] for s in storico])
            st.markdown(f'<div class="saldo-box"><h2>Saldo: € {saldo:.2f}</h2></div>', unsafe_allow_html=True)
            with st.expander("Nuovo Movimento"):
                # Form contabilità come prima...
                pass

        elif figura == "OSS":
            st.subheader("🧹 Mansioni OSS")
            if p_sel[7] == GIORNI[date.today().weekday()]: st.warning("🧺 TURNO LAVATRICE!")
            # Form OSS come prima...

# --- MONITORAGGIO ---
elif menu == "Monitoraggio":
    for pid, nome, g in db_run("SELECT id, nome, giorno_lavatrice FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            note = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if note:
                h = "<table class='custom-table'><tr><th>DATA</th><th>RUOLO</th><th>NOTA</th></tr>"
                for d, ru, op, nt in note:
                    h += f"<tr><td>{d}</td><td>{ru} ({op})</td><td>{nt}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
