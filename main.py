import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .custom-table {width: 100%; border-collapse: collapse; font-size: 0.85rem; background: white;}
    .custom-table th {background-color: #1e3a8a; color: white; padding: 10px; text-align: left; border: 1px solid #dee2e6;}
    .custom-table td {padding: 10px; border: 1px solid #dee2e6; vertical-align: middle;}
    .badge-m { background: #dcfce7; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: bold; border: 1px solid #166534; margin-right:2px;}
    .status-ok { color: #10b981; font-weight: bold; border: 1px solid #10b981; padding: 2px 5px; border-radius: 4px; background: #f0fdf4; }
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .saldo-box { padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; font-weight: bold; font-size: 1.2rem; margin-bottom: 15px; }
    .txt-entrata { color: #10b981; font-weight: bold; }
    .txt-uscita { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT, giorno_lavatrice TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        cur.execute("PRAGMA table_info(pazienti)")
        esistenti = [col[1] for col in cur.fetchall()]
        if "giorno_lavatrice" not in esistenti:
            cur.execute("ALTER TABLE pazienti ADD COLUMN giorno_lavatrice TEXT")

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
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Gestione"])

if menu == "Equipe":
    figura = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    paz_data = db_run("SELECT id, nome, giorno_lavatrice FROM pazienti ORDER BY nome")
    
    if paz_data:
        sel_p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in paz_data])
        p_id = [p[0] for p in paz_data if p[1] == sel_p_nome][0]
        g_lav = [p[2] for p in paz_data if p[1] == sel_p_nome][0]
        st.divider()

        if figura == "Psichiatra":
            st.subheader("📋 Gestione Terapie (Prescrizione)")
            with st.form("presc_form"):
                c1, c2 = st.columns(2)
                f = c1.text_input("Farmaco")
                d = c2.text_input("Dosaggio")
                st.write("Orari Somministrazione (Turni):")
                ct1, ct2, ct3 = st.columns(3)
                tm, tp, tn = ct1.checkbox("M"), ct2.checkbox("P"), ct3.checkbox("N")
                medico = st.text_input("Medico Prescrittore")
                if st.form_submit_button("REGISTRA"):
                    t_list = [s for s, b in zip(["M", "P", "N"], [tm, tp, tn]) if b]
                    db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", 
                           (p_id, f, d, ",".join(t_list), medico, datetime.now().strftime("%d/%m/%y %H:%M")), True)
                    st.rerun()

            terapie = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if terapie:
                h = "<table class='custom-table'><tr><th>DATA</th><th>FARMACO</th><th>DOSAGGIO</th><th>TURNI</th><th>MEDICO</th></tr>"
                for da, fa, do, tu, me, rid in terapie:
                    h += f"<tr><td>{da}</td><td><b>{fa}</b></td><td>{do}</td><td><span class='badge-m'>{tu}</span></td><td>{me}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)

        elif figura == "Infermiere":
            st.subheader("💉 Somministrazione Terapia")
            t_op = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
            firma = st.text_input("Firma Infermiere")
            terapie = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
            for f, d, tu_f, rid in terapie:
                if tu_f and t_op[0] in tu_f:
                    st.markdown("<div class='card-box'>", unsafe_allow_html=True)
                    st.write(f"**{f}** ({d})")
                    # (Logica somministrazione come nel codice precedente...)
                    st.markdown("</div>", unsafe_allow_html=True)

        elif figura == "Educatore":
            st.subheader("💰 Gestione Contabilità")
            
            # Recupero movimenti
            movimenti = db_run("SELECT data, desc, importo, tipo, op, row_id FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in movimenti])
            
            st.markdown(f'<div class="saldo-box">Saldo Disponibile: € {saldo:.2f}</div>', unsafe_allow_html=True)
            
            with st.expander("📝 Registra Nuovo Movimento"):
                tipo = st.radio("Tipo Operazione", ["Entrata", "Uscita"], horizontal=True)
                importo = st.number_input("Cifra €", min_value=0.0, step=0.50)
                desc = st.text_input("Causale / Descrizione")
                op_ed = st.text_input("Firma Educatore")
                if st.button("CONFERMA TRANSAZIONE"):
                    if desc and op_ed:
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", 
                               (p_id, date.today().strftime("%d/%m/%Y"), desc, importo, tipo, op_ed), True)
                        st.rerun()
                    else: st.error("Compilare tutti i campi")

            st.write("#### 📊 Storico Movimenti")
            if movimenti:
                h = "<table class='custom-table'><tr><th>DATA</th><th>CAUSALE</th><th>ENTRATA</th><th>USCITA</th><th>OPERATORE</th></tr>"
                for d, ds, im, tp, op, rid in movimenti:
                    ent = f"<span class='txt-entrata'>€ {im:.2f}</span>" if tp == "Entrata" else ""
                    usc = f"<span class='txt-uscita'>€ {im:.2f}</span>" if tp == "Uscita" else ""
                    h += f"<tr><td>{d}</td><td>{ds}</td><td>{ent}</td><td>{usc}</td><td>{op}</td></tr>"
                st.markdown(h + "</table>", unsafe_allow_html=True)
            else:
                st.info("Nessun movimento registrato.")

        elif figura == "OSS":
            st.subheader("🧹 Mansioni OSS")
            # (Logica OSS...)

elif menu == "Monitoraggio":
    for p_id, nome, g in db_run("SELECT id, nome, giorno_lavatrice FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            # (Tabella diario...)
            pass

elif menu == "Gestione":
    st.subheader("⚙️ Amministrazione")
    n_p = st.text_input("Nome Nuovo Paziente")
    g_l = st.selectbox("Giorno Lavatrice", GIORNI)
    if st.button("SALVA"):
        db_run("INSERT INTO pazienti (nome, giorno_lavatrice) VALUES (?,?)", (n_p, g_l), True); st.rerun()
