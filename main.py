import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; margin-bottom: 20px; font-weight: bold; font-family: sans-serif;}
    .clinica-table {width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 0.9rem; margin-top: 10px; background-color: white;}
    .clinica-table th {background-color: #1e3a8a; color: white; padding: 12px; text-align: left; border: 1px solid #e2e8f0;}
    .clinica-table td {padding: 10px; border: 1px solid #e2e8f0; vertical-align: top;}
    
    .row-agitato {background-color: #fef2f2 !important; border-left: 5px solid #ef4444 !important;}
    .row-stabile {background-color: #ffffff; border-left: 5px solid #10b981 !important;}
    .row-log {background-color: #fffbeb !important; font-style: italic; border-left: 5px solid #f59e0b !important;}

    .badge {padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; color: white; display: inline-block;}
    .b-stabile {background-color: #10b981;}
    .b-agitato {background-color: #ef4444;}
    
    .saldo-box {padding: 20px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; margin-bottom: 20px;}
    .entrata {color: #10b981; font-weight: bold;}
    .uscita {color: #ef4444; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, data TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS documenti (p_id INTEGER, nome_doc TEXT, file_blob BLOB, data TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Codice Accesso", type="password")
        if st.form_submit_button("ENTRA"):
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.session_state.role = "admin" if pwd == "admin2026" else "user"
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Gestione Soldi", "Agenda", "Terapie", "Documenti", "Gestione"])

# --- 5. MONITORAGGIO ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO: {nome.upper()}"):
            c1, c2, c3 = st.columns(3)
            r_ins = c1.selectbox("Ruolo", ["Psichiatra", "Psicologo", "Educatore", "Assistente Sociale", "Infermiere", "OSS", "Opsi"], key=f"r{p_id}")
            f_ins = c2.text_input("Firma", key=f"f{p_id}")
            u_ins = c3.selectbox("Umore", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}")
            n_ins = st.text_area("Nota Clinica", key=f"n{p_id}")
            if st.button("SALVA NOTA", key=f"btn_n{p_id}"):
                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), u_ins, n_ins, r_ins, f_ins), True); st.rerun()
            
            note = db_run("SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                html = '<table class="clinica-table"><thead><tr><th>DATA</th><th>UMORE</th><th>OP</th><th>NOTA</th></tr></thead><tbody>'
                for d, um, tx, ru, fi in note:
                    r_cl = "row-agitato" if um == "Agitato" else "row-stabile"
                    html += f'<tr class="{r_cl}"><td>{d}</td><td>{um}</td><td>{ru} ({fi})</td><td>{tx}</td></tr>'
                st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# --- 6. SEZIONE EQUIPE (NUOVA) ---
elif menu == "Equipe":
    st.subheader("👥 Area Professionale Equipe")
    figura = st.selectbox("Seleziona Figura Professionale", ["Psichiatra", "Psicologo", "Educatore", "Assistente Sociale", "Infermiere", "OSS", "Opsi"])
    
    st.info(f"Accesso Area: **{figura.upper()}**")
    
    # Switch per le diverse figure
    if figura == "Psichiatra":
        st.write("📋 *Funzioni: Relazioni Cliniche, Valutazione Rischio, Piani Terapeutici.*")
    elif figura == "Psicologo":
        st.write("🧠 *Funzioni: Colloqui Individuali, Test Psicometrici, Supporto Psicologico.*")
    elif figura == "Educatore":
        st.write("🎨 *Funzioni: Progetti Educativi (PEI), Attività di Gruppo, Riabilitazione.*")
    elif figura == "Assistente Sociale":
        st.write("🏠 *Funzioni: Rapporti con il territorio, Dimissioni protette, Contatti Familiari.*")
    elif figura == "Infermiere":
        st.write("💉 *Funzioni: Parametri Vitali, Somministrazione Terapia, Medicazioni.*")
    elif figura == "OSS":
        st.write("🧼 *Funzioni: Igiene Personale, Supporto ai Pasti, Monitoraggio Comportamentale.*")
    elif figura == "Opsi":
        st.write("🛡️ *Funzioni: Vigilanza, Sicurezza, Accompagnamenti.*")

# --- 7. GESTIONE SOLDI ---
elif menu == "Gestione Soldi":
    st.subheader("💰 Gestione Contabilità")
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]
        movimenti = db_run("SELECT importo, tipo FROM soldi WHERE p_id=?", (p_id,))
        saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movimenti])
        st.markdown(f'<div class="saldo-box"><h5>SALDO ATTUALE</h5><h2>€ {saldo:.2f}</h2></div>', unsafe_allow_html=True)
        # Form per movimenti (già presente)

# --- (ALTRE SEZIONI RIMANENTI) ---
elif menu == "Agenda":
    st.subheader("📅 Agenda")
    # ... codice agenda esistente ...

elif menu == "Terapie":
    st.subheader("💊 Terapie")
    # ... codice terapie esistente ...

elif menu == "Documenti":
    st.subheader("📂 Documentazione")
    # ... codice documenti esistente ...

elif menu == "Gestione":
    st.subheader("⚙️ Amministrazione")
    # ... codice gestione esistente ...
