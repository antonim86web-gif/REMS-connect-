import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold;}
    .patient-header { background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 8px solid #1e3a8a; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .allergy-alert { background: #fee2e2; color: #991b1b; padding: 8px 15px; border-radius: 6px; font-weight: bold; border: 1px solid #f87171; display: inline-block; }
    .diet-box { background: #fef9c3; color: #854d0e; padding: 8px 15px; border-radius: 6px; border: 1px solid #facc15; display: inline-block; }
    .custom-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; background: white; }
    .custom-table th { background-color: #1e3a8a; color: white; padding: 12px; text-align: left; }
    .custom-table td { padding: 12px; border: 1px solid #dee2e6; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE (CON AUTO-RIPARAZIONE PER SMARTPHONE) ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        
        # Creazione tabella base
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        
        # Verifica ed estensione automatica delle colonne (Risolve l'errore Sqlite3)
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
    pwd = st.text_input("Codice Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]: st.session_state.auth = True; st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Gestione Ingressi", "Area Equipe", "Monitoraggio"])

# --- 5. SEZIONE INGRESSI ---
if menu == "Gestione Ingressi":
    st.header("👥 Amministrazione Pazienti")
    t1, t2 = st.tabs(["➕ Nuovo Ingresso", "📝 Modifica/Elimina"])
    
    with t1:
        with st.form("f_ing"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nome e Cognome")
            dn = c2.date_input("Data di Nascita", value=date(1980,1,1))
            di = c1.date_input("Data Ingresso", value=date.today())
            gl = c2.selectbox("Giorno Lavatrice", GIORNI)
            dia = st.text_area("Diagnosi")
            all = st.text_area("Allergie")
            diet = st.text_input("Dieta")
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO pazienti (nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice) VALUES (?,?,?,?,?,?,?)",
                       (n, dn.strftime("%d/%m/%Y"), di.strftime("%d/%m/%Y"), dia, all, diet, gl), True)
                st.success("Registrato!"); st.rerun()

    with t2:
        paz = db_run("SELECT id, nome, diagnosi, allergie, dieta, giorno_lavatrice FROM pazienti ORDER BY nome")
        for pid, n, d, a, dt, g in paz:
            with st.expander(f"Gestisci {n}"):
                with st.form(f"m_{pid}"):
                    m_n = st.text_input("Nome", n); m_d = st.text_area("Diagnosi", d)
                    m_a = st.text_area("Allergie", a); m_dt = st.text_input("Dieta", dt)
                    m_g = st.selectbox("Lavatrice", GIORNI, index=GIORNI.index(g))
                    if st.form_submit_button("AGGIORNA"):
                        db_run("UPDATE pazienti SET nome=?, diagnosi=?, allergie=?, dieta=?, giorno_lavatrice=? WHERE id=?", (m_n, m_d, m_a, m_dt, m_g, pid), True); st.rerun()
                    if st.form_submit_button("ELIMINA PAZIENTE"):
                        db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()

# --- 6. AREA EQUIPE ---
elif menu == "Area Equipe":
    ruolo = st.sidebar.selectbox("Tuo Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    p_lista = db_run("SELECT id, nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice FROM pazienti ORDER BY nome")
    
    if p_lista:
        sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p = [x for x in p_lista if x[1] == sel][0]
        
        st.markdown(f"""
        <div class="patient-header">
            <h3>{p[1].upper()}</h3>
            <p>Nato il: <b>{p[2]}</b> | Ingresso: <b>{p[3]}</b> | Lavatrice: <b>{p[7]}</b></p>
            <p><i>Diagnosi: {p[4]}</i></p>
            <div style="margin-top:10px;">
                <span class="allergy-alert">⚠️ Allergie: {p[5]}</span> &nbsp;
                <span class="diet-box">🍽️ Dieta: {p[6]}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        t1, t2, t3 = st.tabs(["📝 Clinica", "💰 Contabilità", "🧹 OSS"])
        
        with t1:
            if ruolo == "Psichiatra":
                with st.expander("Prescrivi Terapia"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    if st.button("SALVA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data_prescr) VALUES (?,?,?,?)", (p[0], f, d, date.today().strftime("%d/%m/%Y")), True); st.rerun()
            
            with st.form("nota"):
                n_t = st.text_area("Inserisci nota diario")
                f_t = st.text_input("Firma")
                if st.form_submit_button("REGISTRA NOTA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p[0], datetime.now().strftime("%d/%m/%y %H:%M"), n_t, ruolo, f_t), True); st.rerun()

        with t2:
            st.subheader("Gestione Soldi")
            storico = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p[0],))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in storico])
            st.metric("Saldo Attuale", f"€ {saldo:.2f}")
            with st.expander("Nuovo Movimento"):
                tipo = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                imp = st.number_input("Importo €", min_value=0.0)
                cau = st.text_input("Causale")
                if st.button("CONFERMA"):
                    db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo) VALUES (?,?,?,?,?)", (p[0], date.today().strftime("%d/%m/%Y"), cau, imp, tipo), True); st.rerun()

        with t3:
            if p[7] == GIORNI[date.today().weekday()]: st.warning("🧺 TURNO LAVATRICE")
            if st.button("REGISTRA PULIZIA STANZA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p[0], datetime.now().strftime("%H:%M"), "Pulizia Stanza", "OSS", "Sistema"), True); st.success("Fatto")

# --- 7. MONITORAGGIO ---
elif menu == "Monitoraggio":
    paz_m = db_run("SELECT id, nome FROM pazienti")
    for pid, nome in paz_m:
        with st.expander(f"DIARIO: {nome}"):
            ev = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            for d, r, o, nt in ev:
                st.write(f"**[{d}] {r} ({o})**: {nt}")
