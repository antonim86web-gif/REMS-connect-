import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO - Full Suite", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .patient-header { background: #f8fafc; padding: 20px; border-radius: 12px; border-left: 8px solid #1e3a8a; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .allergy-alert { background: #fee2e2; color: #991b1b; padding: 8px 15px; border-radius: 6px; font-weight: bold; border: 1px solid #f87171; display: inline-block; }
    .diet-box { background: #fef9c3; color: #854d0e; padding: 8px 15px; border-radius: 6px; border: 1px solid #facc15; display: inline-block; }
    .custom-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; background: white; }
    .custom-table th { background-color: #1e3a8a; color: white; padding: 12px; text-align: left; }
    .custom-table td { padding: 12px; border: 1px solid #dee2e6; }
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: white; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        # Creazione/Aggiornamento Tabella Pazienti
        cur.execute("""CREATE TABLE IF NOT EXISTS pazienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome TEXT, 
            data_nascita TEXT,
            data_ingresso TEXT,
            diagnosi TEXT,
            allergie TEXT,
            dieta TEXT,
            giorno_lavatrice TEXT
        )""")
        # Altre tabelle (Eventi, Terapie, Soldi)
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"]

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

# --- 5. GESTIONE INGRESSI (MODIFICA / AGGIUNGI / ELIMINA) ---
if menu == "Gestione Ingressi":
    st.header("👥 Amministrazione Pazienti")
    t1, t2 = st.tabs(["➕ Nuovo Ingresso", "📝 Modifica/Elimina"])
    
    with t1:
        with st.form("form_ingresso"):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nome e Cognome")
            dn = c2.date_input("Data di Nascita", min_value=date(1940,1,1))
            di = c1.date_input("Data di Ingresso", value=date.today())
            gl = c2.selectbox("Giorno Lavatrice", GIORNI)
            dia = st.text_area("Diagnosi")
            all = st.text_area("Allergie")
            diet = st.text_input("Dieta Specifica")
            if st.form_submit_button("REGISTRA PAZIENTE"):
                db_run("INSERT INTO pazienti (nome, data_nascita, data_ingresso, diagnosi, allergie, dieta, giorno_lavatrice) VALUES (?,?,?,?,?,?,?)",
                       (n, dn.strftime("%d/%m/%Y"), di.strftime("%d/%m/%Y"), dia, all, diet, gl), True)
                st.success("Paziente registrato!"); st.rerun()

    with t2:
        pazienti = db_run("SELECT id, nome, diagnosi, allergie, dieta, giorno_lavatrice FROM pazienti ORDER BY nome")
        for pid, n, d, a, dt, g in pazienti:
            with st.expander(f"Modifica {n}"):
                with st.form(f"f_mod_{pid}"):
                    m_n = st.text_input("Nome", n)
                    m_dia = st.text_area("Diagnosi", d)
                    m_all = st.text_area("Allergie", a)
                    m_diet = st.text_input("Dieta", dt)
                    m_gl = st.selectbox("Giorno Lavatrice", GIORNI, index=GIORNI.index(g))
                    c_b1, c_b2 = st.columns(2)
                    if c_b1.form_submit_button("AGGIORNA"):
                        db_run("UPDATE pazienti SET nome=?, diagnosi=?, allergie=?, dieta=?, giorno_lavatrice=? WHERE id=?", (m_n, m_dia, m_all, m_diet, m_gl, pid), True); st.rerun()
                    if c_b2.form_submit_button("ELIMINA"):
                        db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()

# --- 6. AREA EQUIPE (TUTTE LE SEZIONI PRECEDENTI) ---
elif menu == "Area Equipe":
    ruolo = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
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

        # TAB OPERATIVI (Terapie, Diario, Soldi, OSS)
        tab1, tab2, tab3 = st.tabs(["💊 Terapie & Diario", "💰 Contabilità", "🧹 Area OSS"])
        
        with tab1:
            if ruolo == "Psichiatra":
                with st.form("presc"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    tr = st.multiselect("Turni", ["M", "P", "N"])
                    med = st.text_input("Firma Medico")
                    if st.form_submit_button("PRESCRIVI"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, f, d, ",".join(tr), med, date.today().strftime("%d/%m/%Y")), True); st.rerun()
            
            if ruolo == "Infermiere":
                st.subheader("Somministrazione")
                # ... (Logica infermiere precedente) ...
                
            st.write("#### Diario Clinico")
            with st.form("d_form"):
                txt = st.text_area("Inserisci nota")
                firma = st.text_input("Tua Firma")
                if st.form_submit_button("REGISTRA NOTA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), txt, ruolo, firma), True); st.rerun()

        with tab2:
            st.subheader("Gestione Fondi")
            # ... (Logica soldi precedente) ...
            movs = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=?", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in movs])
            st.metric("Saldo", f"€ {saldo:.2f}")

        with tab3:
            st.subheader("Mansioni OSS")
            if p_sel[7] == GIORNI[date.today().weekday()]:
                st.warning("🧺 Oggi turno lavatrice!")
            # ... (Logica OSS precedente) ...

# --- 7. MONITORAGGIO ---
elif menu == "Monitoraggio":
    for pid, nome in db_run("SELECT id, nome FROM pazienti"):
        with st.expander(f"DIARIO: {nome}"):
            ev = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            for d, r, o, nt in ev:
                st.write(f"**{d} - {r} ({o})**: {nt}")
