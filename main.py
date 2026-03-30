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
    .card {padding: 12px; margin: 5px 0; border-radius: 8px; background: #f8fafc; border-left: 5px solid #64748b; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}
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

# --- 4. NAVIGAZIONE (Rimosso 'Gestione Soldi' dal menu principale) ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Agenda", "Terapie", "Documenti", "Gestione"])

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

# --- 6. AREA EQUIPE ---
elif menu == "Equipe":
    st.subheader("👥 Area Professionale Equipe")
    figura = st.selectbox("Seleziona Figura Professionale", ["Psichiatra", "Psicologo", "Educatore", "Assistente Sociale", "Infermiere", "OSS", "Opsi"])
    
    st.divider()

    if figura == "Educatore":
        st.markdown("### 🎨 Area Educativa")
        tabs = st.tabs(["Gestione Soldi", "Progetti (PEI)", "Attività"])
        
        with tabs[0]: # Spostata qui la gestione soldi
            st.write("#### 💰 Contabilità Pazienti")
            paz = db_run("SELECT * FROM pazienti ORDER BY nome")
            if paz:
                sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz], key="sel_s_edu")
                p_id = [p[0] for p in paz if p[1] == sel_p][0]
                
                movimenti = db_run("SELECT importo, tipo FROM soldi WHERE p_id=?", (p_id,))
                saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movimenti])
                
                st.markdown(f'<div class="saldo-box"><h5>SALDO DISPONIBILE</h5><h2 style="color:#1e3a8a;">€ {saldo:.2f}</h2></div>', unsafe_allow_html=True)
                
                with st.expander("➕ REGISTRA NUOVA OPERAZIONE"):
                    c1, c2 = st.columns(2)
                    tipo_m = c1.radio("Tipo Movimento", ["Entrata", "Uscita"])
                    imp_m = c2.number_input("Importo (€)", min_value=0.0, step=0.50)
                    desc_m = st.text_input("Causale")
                    f_m = st.text_input("Firma Educatore")
                    if st.button("SALVA MOVIMENTO"):
                        if desc_m and f_m:
                            db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)",
                                   (p_id, date.today().strftime("%d/%m/%Y"), desc_m, imp_m, tipo_m, f_m), True)
                            st.success("Registrato!"); st.rerun()

                st.divider()
                storico = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
                if storico:
                    html_s = '<table class="clinica-table"><thead><tr><th>DATA</th><th>DESCRIZIONE</th><th>ENTRATA</th><th>USCITA</th><th>OP</th></tr></thead><tbody>'
                    for d, ds, im, tp, op in storico:
                        en = f"€ {im:.2f}" if tp == "Entrata" else ""
                        us = f"€ {im:.2f}" if tp == "Uscita" else ""
                        html_s += f'<tr><td>{d}</td><td>{ds}</td><td class="entrata">{en}</td><td class="uscita">{us}</td><td>{op}</td></tr>'
                    st.markdown(html_s + '</tbody></table>', unsafe_allow_html=True)
        
        with tabs[1]:
            st.info("Sezione PEI in fase di sviluppo.")
            
    elif figura == "Psichiatra":
        st.write("📋 *Funzioni Psichiatriche: Relazioni e Piani Clinici.*")
    elif figura == "Psicologo":
        st.write("🧠 *Funzioni Psicologiche: Colloqui e Test.*")
    elif figura == "Assistente Sociale":
        st.write("🏠 *Funzioni Sociali: Rapporti con il territorio.*")
    elif figura == "Infermiere":
        st.write("💉 *Funzioni Infermieristiche: Somministrazione e Parametri.*")
    elif figura == "OSS":
        st.write("🧼 *Funzioni OSS: Igiene e monitoraggio base.*")
    elif figura == "Opsi":
        st.write("🛡️ *Funzioni Opsi: Sicurezza e Vigilanza.*")

# --- 7. AGENDA ---
elif menu == "Agenda":
    st.subheader("📅 Agenda")
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        with st.expander("Nuovo Evento"):
            ps = st.selectbox("Paziente", [p[1] for p in paz])
            ts = st.selectbox("Tipo", ["Uscita", "Udienza", "Visita", "Permesso"])
            ds = st.date_input("Data")
            if st.button("AGGIUNGI"):
                pid = [p[0] for p in paz if p[1] == ps][0]
                db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (pid, ts, str(ds), "", ""), True); st.rerun()
    for t, d, r, pn, rid in db_run("SELECT a.tipo, a.d_ora, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora DESC"):
        st.markdown(f'<div class="card"><b>{d}</b> | {pn} | {t.upper()}</div>', unsafe_allow_html=True)

# --- 8. TERAPIE ---
elif menu == "Terapie":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"💊 TERAPIA: {nome.upper()}"):
            for fa, do, da, me, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=?", (p_id,)):
                st.info(f"**{fa}** - {do}")

# --- 9. DOCUMENTI ---
elif menu == "Documenti":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        sel_p = st.selectbox("Paziente", [p[1] for p in paz])
        pid = [p[0] for p in paz if p[1] == sel_p][0]
        up = st.file_uploader("Carica File")
        if up and st.button("SALVA"):
            db_run("INSERT INTO documenti (p_id, nome_doc, file_blob, data) VALUES (?,?,?,?)", (pid, up.name, up.read(), str(date.today())), True); st.rerun()

# --- 10. GESTIONE ---
elif menu == "Gestione":
    if st.session_state.role == "admin":
        nuovo = st.text_input("Nuovo Paziente")
        if st.button("AGGIUNGI"):
            if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
        for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
            st.write(f"👤 {pnome}")
