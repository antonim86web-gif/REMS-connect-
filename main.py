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
    .b-sistema {background-color: #f59e0b;}
    
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

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Agenda", "Documenti", "Gestione"])

# --- 5. MONITORAGGIO ---
if menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 DIARIO CLINICO: {nome.upper()}"):
            c1, c2, c3 = st.columns(3)
            r_ins = c1.selectbox("Ruolo", ["Psichiatra", "Psicologo", "Educatore", "Assistente Sociale", "Infermiere", "OSS", "Opsi"], key=f"r{p_id}")
            f_ins = c2.text_input("Firma", key=f"f{p_id}")
            u_ins = c3.selectbox("Umore", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}")
            n_ins = st.text_area("Nota Clinica", key=f"n{p_id}")
            if st.button("SALVA NOTA", key=f"btn_n{p_id}"):
                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), u_ins, n_ins, r_ins, f_ins), True); st.rerun()
            
            st.divider()
            # Visualizzazione Terapie Attuali (Sola Lettura)
            st.write("💊 **Terapie in corso:**")
            t_attuali = db_run("SELECT farmaco, dosaggio FROM terapie WHERE p_id=?", (p_id,))
            if t_attuali:
                st.caption(", ".join([f"{t[0]} ({t[1]})" for t in t_attuali]))
            else: st.caption("Nessuna terapia registrata.")

            note = db_run("SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=? ORDER BY row_id DESC", (p_id,))
            if note:
                html = '<table class="clinica-table"><thead><tr><th>DATA</th><th>UMORE</th><th>OP</th><th>NOTA</th></tr></thead><tbody>'
                for d, um, tx, ru, fi in note:
                    r_cl = "row-agitato" if um == "Agitato" else ("row-log" if "[CAMBIO" in tx else "row-stabile")
                    html += f'<tr class="{r_cl}"><td>{d}</td><td>{um}</td><td>{ru} ({fi})</td><td>{tx}</td></tr>'
                st.markdown(html + '</tbody></table>', unsafe_allow_html=True)

# --- 6. AREA EQUIPE ---
elif menu == "Equipe":
    st.subheader("👥 Area Professionale Equipe")
    figura = st.selectbox("Seleziona Figura Professionale", ["Psichiatra", "Psicologo", "Educatore", "Assistente Sociale", "Infermiere", "OSS", "Opsi"])
    st.divider()

    if figura == "Psichiatra":
        st.markdown("### 📋 Area Medica e Psichiatrica")
        tabs = st.tabs(["Cambio Terapia", "Relazioni Cliniche"])
        
        with tabs[0]:
            st.write("#### 💊 Gestione Farmacologica")
            paz = db_run("SELECT * FROM pazienti ORDER BY nome")
            if paz:
                sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz], key="sel_psi_p")
                p_id = [p[0] for p in paz if p[1] == sel_p][0]
                
                # Form inserimento
                with st.expander("➕ AGGIUNGI / VARIA FARMACO"):
                    f_nome = st.text_input("Nome Farmaco")
                    f_dose = st.text_input("Dosaggio (es. 2mg 1-0-1)")
                    f_med = st.text_input("Medico Prescrittore", value="Dr. " + st.session_state.get('last_sign', ""))
                    if st.button("CONFERMA VARIAZIONE"):
                        if f_nome and f_dose:
                            db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", 
                                   (p_id, f_nome, f_dose, date.today().strftime("%d/%m/%Y"), f_med), True)
                            # Log automatico nel monitoraggio
                            log_msg = f"[CAMBIO TERAPIA] Inserito: {f_nome} ({f_dose}), Medico: {f_med}"
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                                   (p_id, datetime.now().strftime("%d/%m/%y %H:%M"), "Stabile", log_msg, "Psichiatra", f_med), True)
                            st.success("Terapia aggiornata e log salvato."); st.rerun()
                
                st.write("**Schema Terapeutico Attuale:**")
                ter_list = db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=?", (p_id,))
                for fa, do, da, me, rid in ter_list:
                    c1, c2 = st.columns([4, 1])
                    c1.warning(f"**{fa}** - {do} (Prescritta il {da} da {me})")
                    if c2.button("Elimina", key=f"del_t_{rid}"):
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True); st.rerun()

    elif figura == "Educatore":
        st.markdown("### 🎨 Area Educativa")
        tabs = st.tabs(["Gestione Soldi", "Progetti (PEI)"])
        with tabs[0]:
            st.write("#### 💰 Contabilità Pazienti")
            paz = db_run("SELECT * FROM pazienti ORDER BY nome")
            if paz:
                sel_p = st.selectbox("Seleziona Paziente", [p[1] for p in paz], key="sel_edu_p")
                p_id = [p[0] for p in paz if p[1] == sel_p][0]
                movimenti = db_run("SELECT importo, tipo FROM soldi WHERE p_id=?", (p_id,))
                saldo = sum([m[0] if m[1] == "Entrata" else -m[0] for m in movimenti])
                st.markdown(f'<div class="saldo-box"><h5>SALDO DISPONIBILE</h5><h2>€ {saldo:.2f}</h2></div>', unsafe_allow_html=True)
                # Form Soldi (già implementato)
                with st.expander("➕ REGISTRA MOVIMENTO"):
                    tipo_m = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                    imp_m = st.number_input("Importo (€)", min_value=0.0, step=0.50)
                    desc_m = st.text_input("Causale")
                    f_m = st.text_input("Firma Educatore")
                    if st.button("SALVA"):
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), desc_m, imp_m, tipo_m, f_m), True); st.rerun()

    else: st.info(f"Funzioni per **{figura}** in fase di configurazione.")

# --- 7. AGENDA ---
elif menu == "Agenda":
    st.subheader("📅 Agenda Eventi")
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        with st.expander("Nuovo Evento"):
            ps = st.selectbox("Paziente", [p[1] for p in paz])
            ts = st.selectbox("Tipo", ["Uscita", "Udienza", "Visita", "Permesso"])
            if st.button("AGGIUNGI"):
                pid = [p[0] for p in paz if p[1] == ps][0]
                db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (pid, ts, str(date.today()), "", ""), True); st.rerun()
    for t, d, r, pn, rid in db_run("SELECT a.tipo, a.d_ora, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora DESC"):
        st.markdown(f'<div class="card"><b>{d}</b> | {pn} | {t.upper()}</div>', unsafe_allow_html=True)

# --- 8. DOCUMENTI & GESTIONE ---
elif menu == "Documenti":
    st.subheader("📂 Archivio Documentale")
    # ... codice file uploader ...
elif menu == "Gestione":
    if st.session_state.role == "admin":
        nuovo = st.text_input("Aggiungi Paziente")
        if st.button("AGGIUNGI"):
            if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
        for pid, pnome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
            st.write(f"👤 {pnome}")
