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
    
    .row-stabile {background-color: #ffffff; border-left: 5px solid #10b981 !important;}
    .row-report {background-color: #f0f9ff !important; border-left: 5px solid #0ea5e9 !important; font-weight: bold;}
    .row-med {background-color: #f0fdf4 !important; border-left: 5px solid #22c55e !important;}
    .row-rifiuto {background-color: #fef2f2 !important; border-left: 5px solid #dc2626 !important;}
    
    .saldo-box {padding: 15px; border-radius: 10px; background-color: #f8fafc; text-align: center; border: 2px solid #1e3a8a; margin-bottom: 15px;}
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
            # (Inserimento note standard rimosso per brevità, resta lo storico)
            note = db_run("SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                html = '<table class="clinica-table"><thead><tr><th>DATA</th><th>STATO</th><th>OP</th><th>NOTA</th></tr></thead><tbody>'
                for d, um, tx, ru, fi in note:
                    r_cl = "row-report" if "[REPORT]" in tx else ("row-med" if "[SOMM]" in tx else "row-stabile")
                    html += f'<tr class="{r_cl}"><td>{d}</td><td>{um}</td><td>{ru} ({fi})</td><td>{tx}</td></tr>'
                st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# --- 6. AREA EQUIPE ---
elif menu == "Equipe":
    st.subheader("👥 Area Professionale Equipe")
    figura = st.selectbox("Seleziona Figura", ["Psichiatra", "Infermiere", "Educatore", "Psicologo", "Assistente Sociale", "OSS", "Opsi"])
    st.divider()

    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        sel_p = st.selectbox("Paziente", [p[1] for p in paz])
        p_id = [p[0] for p in paz if p[1] == sel_p][0]

        if figura == "Infermiere":
            st.markdown("### 💉 Area Infermieristica")
            inf_nome = st.text_input("Nome Infermiere in turno", key="inf_name_live")
            
            t1, t2 = st.tabs(["💊 Somministrazione & Report", "📈 Parametri"])
            
            with t1:
                st.info("Convalida i farmaci per generare automaticamente il report giornaliero.")
                terapie = db_run("SELECT farmaco, dosaggio, row_id FROM terapie WHERE p_id=?", (p_id,))
                
                if terapie:
                    for f, d, rid in terapie:
                        with st.container():
                            c1, c2, c3 = st.columns([3, 3, 2])
                            c1.markdown(f"**{f}** - {d}")
                            esito = c2.selectbox("Stato", ["Assunta", "Parziale", "Rifiutata"], key=f"e_{rid}")
                            if c3.button("CONVALIDA", key=f"ok_{rid}"):
                                if not inf_nome:
                                    st.error("Inserire il nome dell'infermiere!")
                                else:
                                    ora_attuale = datetime.now().strftime("%H:%M")
                                    data_attuale = datetime.now().strftime("%d/%m/%Y")
                                    # Generazione Report
                                    log_report = f"[REPORT SOMMINISTRAZIONE] Ore {ora_attuale}: Farmaco {f} ({d}) -> Stato: {esito}. Operatore: {inf_nome}"
                                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                           (p_id, f"{data_attuale} {ora_attuale}", "Stabile", log_report, "Infermiere", inf_nome), True)
                                    st.success(f"Report generato per {f}")
                                    st.rerun()
                
                st.divider()
                if st.button("VISUALIZZA REPORT ODIERNO"):
                    oggi = datetime.now().strftime("%d/%m/%Y")
                    rep = db_run("SELECT data, nota, op FROM eventi WHERE id=? AND nota LIKE '%[REPORT]%' AND data LIKE ?", (p_id, f"%{oggi}%"))
                    if rep:
                        st.table(pd.DataFrame(rep, columns=["Data/Ora", "Dettaglio Somministrazione", "Infermiere"]))
                    else: st.warning("Nessuna somministrazione registrata oggi.")

        elif figura == "Educatore":
            st.markdown("### 🎨 Area Educativa")
            # FIX GESTIONE SOLDI
            st.write("#### 💰 Gestione Contabilità")
            movimenti = db_run("SELECT importo, tipo FROM soldi WHERE p_id=?", (p_id,))
            saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movimenti])
            
            st.markdown(f'<div class="saldo-box"><h5>SALDO ATTUALE</h5><h2 style="color:#1e3a8a;">€ {saldo:.2f}</h2></div>', unsafe_allow_html=True)
            
            with st.expander("📝 Registra Movimento"):
                c1, c2 = st.columns(2)
                t_mov = c1.radio("Tipo", ["Entrata", "Uscita"])
                i_mov = c2.number_input("Importo (€)", min_value=0.0, step=1.0)
                d_mov = st.text_input("Causale")
                f_mov = st.text_input("Firma Educatore", key="f_edu_cash")
                if st.button("SALVA TRANSAZIONE"):
                    if d_mov and f_mov:
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)",
                               (p_id, date.today().strftime("%d/%m/%Y"), d_mov, i_mov, t_mov, f_mov), True)
                        st.success("Movimento salvato correttamente!"); st.rerun()

        elif figura == "Psichiatra":
            # (Codice gestione terapie psichiatra)
            st.write("Gestione Terapie Mediche")

    else: st.warning("Aggiungi un paziente nella sezione Gestione.")

# --- SEZIONI STANDARD ---
elif menu == "Gestione":
    if st.session_state.role == "admin":
        nuovo = st.text_input("Aggiungi Paziente")
        if st.button("SALVA"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
