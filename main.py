import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; margin-bottom: 20px; font-weight: bold;}
    .clinica-table {width: 100%; border-collapse: collapse; font-size: 0.9rem; background-color: white;}
    .clinica-table th {background-color: #1e3a8a; color: white; padding: 10px; text-align: left;}
    .clinica-table td {padding: 8px; border: 1px solid #e2e8f0; vertical-align: top;}
    
    /* Colori Righe Diario */
    .row-stabile {background-color: #ffffff; border-left: 5px solid #10b981 !important;}
    .row-alert {background-color: #fffbeb !important; border-left: 5px solid #f59e0b !important; font-weight: bold;} /* Per Cambi Terapia */
    .row-med {background-color: #f0fdf4 !important; border-left: 5px solid #22c55e !important;}
    .row-parziale {background-color: #fff7ed !important; border-left: 5px solid #f97316 !important;}
    .row-rifiuto {background-color: #fef2f2 !important; border-left: 5px solid #dc2626 !important;}
    
    .badge-alert {background-color: #f59e0b; color: white; padding: 3px 7px; border-radius: 4px; font-size: 0.7rem;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, data TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS parametri (p_id INTEGER, data TEXT, pa TEXT, fc TEXT, sao2 TEXT, tc TEXT, glic TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
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
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Agenda", "Documenti", "Gestione"])

# --- 5. MONITORAGGIO ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO CLINICO: {nome.upper()}"):
            c1, c2, c3 = st.columns(3)
            r_ins = c1.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Psicologo", "Educatore", "Assistente Sociale", "OSS", "Opsi"], key=f"r{p_id}")
            f_ins = c2.text_input("Firma", key=f"f{p_id}")
            u_ins = c3.selectbox("Umore", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}")
            n_ins = st.text_area("Nota Clinica", key=f"n{p_id}")
            if st.button("SALVA NOTA", key=f"btn_n{p_id}"):
                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), u_ins, n_ins, r_ins, f_ins), True); st.rerun()
            
            note = db_run("SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                html = '<table class="clinica-table"><thead><tr><th>DATA</th><th>STATO</th><th>OP</th><th>NOTA</th></tr></thead><tbody>'
                for d, um, tx, ru, fi in note:
                    if "[CAMBIO TERAPIA]" in tx: r_cl = "row-alert"
                    elif "[SOMM]" in tx: r_cl = "row-med"
                    elif "[PARZIALE]" in tx: r_cl = "row-parziale"
                    elif "[RIFIUTATA]" in tx: r_cl = "row-rifiuto"
                    else: r_cl = "row-stabile"
                    
                    html += f'<tr class="{r_cl}"><td>{d}</td><td>{um}</td><td>{ru} ({fi})</td><td>{tx}</td></tr>'
                st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# --- 6. AREA EQUIPE (Sincronizzazione Real-Time) ---
elif menu == "Equipe":
    st.subheader("👥 Area Professionale Equipe")
    figura = st.selectbox("Seleziona Figura", ["Psichiatra", "Infermiere", "Educatore", "Psicologo", "Assistente Sociale", "OSS", "Opsi"])
    st.divider()

    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        sel_p = st.selectbox("Paziente in carico", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]

        if figura == "Psichiatra":
            st.markdown("### 📋 Area Medica (Prescrizione)")
            with st.form("form_terapia"):
                f_n = st.text_input("Nome Farmaco")
                f_d = st.text_input("Dosaggio/Orari")
                f_m = st.text_input("Medico Prescrittore")
                if st.form_submit_button("CONFERMA E AGGIORNA LIVE"):
                    if f_n and f_d:
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", (p_id, f_n, f_d, date.today().strftime("%d/%m/%Y"), f_m), True)
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                               (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", f"⚠️ [CAMBIO TERAPIA] Inserito {f_n} ({f_d})", "Psichiatra", f_m), True)
                        st.success("Terapia aggiornata. L'infermiere vedrà le modifiche istantaneamente."); st.rerun()

        elif figura == "Infermiere":
            st.markdown("### 💉 Area Infermieristica (Somministrazione)")
            t1, t2 = st.tabs(["💊 Somministrazione Live", "📈 Parametri Vitali"])
            
            with t1:
                st.write("#### Schema Terapeutico Attivo (Aggiornato ora)")
                # Qui l'infermiere legge SEMPRE l'ultimo stato del DB
                terapie = db_run("SELECT farmaco, dosaggio, medico, row_id FROM terapie WHERE p_id=?", (p_id,))
                if terapie:
                    for f, d, m, rid in terapie:
                        with st.container():
                            c1, c2, c3 = st.columns([3, 4, 1])
                            c1.markdown(f"**{f}**\n<br><small>Prescritto da: {m}</small>", unsafe_allow_html=True)
                            esito = c2.segmented_control("Esito Assunzione", ["Assunta", "Parziale", "Rifiutata"], key=f"e_{rid}")
                            if c3.button("✅", key=f"ok_{rid}"):
                                if esito:
                                    prefix = "[SOMM]" if esito == "Assunta" else (f"[{esito.upper()}]")
                                    log = f"{prefix} Farmaco: {f} ({d})"
                                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                           (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", log, "Infermiere", "Firma"), True)
                                    st.rerun()
                else: st.info("Nessuna terapia attiva per questo paziente.")

        elif figura == "Educatore":
            st.markdown("### 💰 Gestione Soldi")
            # (Codice gestione soldi già implementato)

    else: st.warning("Nessun paziente trovato. Aggiungine uno in Gestione.")

# --- ALTRE SEZIONI ---
elif menu == "Gestione":
    if st.session_state.role == "admin":
        nuovo = st.text_input("Aggiungi Paziente")
        if st.button("SALVA"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
