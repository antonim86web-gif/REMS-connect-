import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE PAGINA E CSS UNIFICATO ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    .custom-table { width: 100%; border-collapse: collapse; background: white; margin-bottom: 20px; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
    .custom-table th { background-color: #1e293b; color: white; padding: 12px; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .custom-table td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; font-size: 0.85rem; color: #334155; }
    .custom-table tr:hover { background-color: #f8fafc; }
    .badge { padding: 4px 10px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; color: white; display: inline-block; text-transform: uppercase; }
    .bg-psichiatra { background-color: #ef4444; }
    .bg-infermiere { background-color: #3b82f6; }
    .bg-educatore  { background-color: #10b981; }
    .bg-oss        { background-color: #f59e0b; }
    .bg-appuntamento { background-color: #8b5cf6; }
    .bg-sistema { background-color: #64748b; }
    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 10px; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (p_id INTEGER, data TEXT, ora TEXT, tipo TEXT, dettagli TEXT, scorta TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        if query: cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>REMS CONNECT PRO</h1>", unsafe_allow_html=True)
    with st.form("login"):
        pwd = st.text_input("Codice Accesso", type="password")
        if st.form_submit_button("ENTRA"):
            if pwd in ["rems2026"]:
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Appuntamenti", "Gestione"])

# --- 5. LOGICA SEZIONI ---

if menu == "Appuntamenti":
    st.header("📅 Agenda Appuntamenti ed Uscite")
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti:
        p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == p_nome][0]
        with st.expander("➕ Inserisci Nuovo Appuntamento", expanded=True):
            with st.form("form_app"):
                c1, c2 = st.columns(2)
                d_app = c1.date_input("Data", date.today(), format="DD/MM/YYYY")
                o_app = c2.time_input("Ora", datetime.now().time())
                tipo = st.selectbox("Tipologia", ["Visita Specialistica", "Udienza Tribunale", "Permesso Premio", "Colloquio Familiari", "Altro"])
                op_acc = st.text_input("Operatore Accompagnatore")
                det = st.text_area("Luogo / Note")
                if st.form_submit_button("PROGRAMMA USCITA"):
                    if op_acc:
                        db_run("INSERT INTO appuntamenti (p_id, data, ora, tipo, dettagli, scorta) VALUES (?,?,?,?,?,?)", (p_id, d_app.strftime("%d/%m/%Y"), o_app.strftime("%H:%M"), tipo, det, op_acc), True)
                        db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📅 USCITA: {tipo} - Accompagna: {op_acc} ({det})", "Sistema", "Agenda"), True)
                        st.rerun()
        
        apps = db_run("SELECT data, ora, tipo, dettagli, scorta, row_id FROM appuntamenti WHERE p_id=? ORDER BY row_id DESC", (p_id,))
        if apps:
            html = "<table class='custom-table'><tr><th>DATA</th><th>ORA</th><th>TIPO</th><th>DETTAGLI</th><th>ACCOMPAGNATORE</th><th>AZIONE</th></tr>"
            for da, ora, ti, de, sc, rid in apps:
                html += f"<tr><td>{da}</td><td>{ora}</td><td><b>{ti}</b></td><td>{de}</td><td>{sc}</td><td>"
                st.markdown(html, unsafe_allow_html=True)
                if st.button("ELIMINA", key=f"del_a_{rid}"): db_run("DELETE FROM appuntamenti WHERE row_id=?", (rid,), True); st.rerun()
                html = ""
            st.markdown("</table>", unsafe_allow_html=True)

elif menu == "Equipe":
    ruolo = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti:
        p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == p_nome][0]
        
        if ruolo == "Psichiatra":
            st.subheader("📋 Area Medica")
            med_f = st.text_input("Firma Medico")
            with st.expander("➕ Nuova Prescrizione"):
                with st.form("p_form"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m, p, n = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
                    if st.form_submit_button("SALVA"):
                        ts = ",".join([s for s, b in zip(["M","P","N"], [m,p,n]) if b])
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, f, d, ts, med_f, date.today().strftime("%d/%m/%Y")), True); st.rerun()
            
            ta = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            if ta:
                html = "<table class='custom-table'><tr><th>DATA</th><th>FARMACO</th><th>DOSE</th><th>TURNI</th><th>MEDICO</th><th>AZIONE</th></tr>"
                for da, fa, ds, tu, me, rid in ta:
                    html += f"<tr><td>{da}</td><td><b>{fa}</b></td><td>{ds}</td><td>{tu}</td><td>{me}</td><td>"
                    st.markdown(html, unsafe_allow_html=True)
                    if st.button("SOSPENDI", key=f"s_{rid}"):
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"❌ SOSPESO: {fa}", "Psichiatra", med_f), True); st.rerun()
                    html = ""
                st.markdown("</table>", unsafe_allow_html=True)

        elif ruolo == "Infermiere":
            inf_f = st.text_input("Firma Infermiere")
            t1, t2, t3 = st.tabs(["💊 Terapia", "📊 Parametri", "📝 Consegne"])
            with t1:
                c_d, c_t = st.columns(2)
                d_s, t_s = c_d.date_input("Data", date.today(), format="DD/MM/YYYY"), c_t.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                ter = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                for f, d, tu_p, rid in ter:
                    if tu_p and t_s[0] in tu_p:
                        st.markdown(f"<div class='card-box'><b>{f}</b> ({d})", unsafe_allow_html=True)
                        ce, cn, cb = st.columns([2,2,1])
                        es = ce.radio("Esito", ["Assunta", "Rifiutata", "Parziale"], key=f"e_{rid}", horizontal=True)
                        nt = cn.text_input("Note", key=f"n_{rid}")
                        if cb.button("REGISTRA", key=f"b_{rid}"):
                            if inf_f: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, f"{d_s.strftime('%d/%m/%Y')} {datetime.now().strftime('%H:%M')}", "Stabile", f"[{t_s[0]}] {f} -> {es} {nt}", "Infermiere", inf_f), True); st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
            with t2:
                with st.form("pv"):
                    c1,c2,c3,c4 = st.columns(4)
                    pa, fc, sa, tc = c1.text_input("PA"), c2.number_input("FC", 0), c3.number_input("SpO2", 0), c4.number_input("TC", 34.0, 42.0, 36.5)
                    if st.form_submit_button("SALVA PV"):
                        if inf_f: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO2:{sa}% TC:{tc}", "Infermiere", inf_f), True); st.rerun()
            with t3:
                c_d, c_t = st.columns(2)
                d_c, t_c = c_d.date_input("Data", date.today(), format="DD/MM/YYYY", key="dci"), c_t.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"], key="tci")
                txt = st.text_area("Consegna")
                if st.button("SALVA CONSEGNA"):
                    if inf_f and txt: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, f"{d_c.strftime('%d/%m/%Y')} {datetime.now().strftime('%H:%M')}", "Stabile", f"📝 [CONS {t_c.upper()}] {txt}", "Infermiere", inf_f), True); st.rerun()

        elif ruolo == "Educatore":
            ed_f = st.text_input("Firma Educatore")
            mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in mov])
            st.metric("SALDO CASSA", f"€ {saldo:.2f}")
            with st.form("cash"):
                tp, im, ds = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True), st.number_input("€", 0.0), st.text_input("Causale")
                if st.form_submit_button("REGISTRA MOVIMENTO"):
                    if ed_f: db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, ed_f), True); st.rerun()
            if mov:
                html = "<table class='custom-table'><tr><th>DATA</th><th>CAUSALE</th><th>ENTRATA</th><th>USCITA</th><th>OP</th></tr>"
                for d, ds, im, tp, op in mov:
                    e, u = (f"€ {im:.2f}", "") if tp == "Entrata" else ("", f"€ {im:.2f}")
                    html += f"<tr><td>{d}</td><td>{ds}</td><td style='color:green;font-weight:bold'>{e}</td><td style='color:red;font-weight:bold'>{u}</td><td>{op}</td></tr>"
                st.markdown(html + "</table>", unsafe_allow_html=True)

        elif ruolo == "OSS":
            oss_f = st.text_input("Firma OSS")
            t_o1, t_o2 = st.tabs(["🧼 Mansioni", "📝 Consegne"])
            with t_o1:
                c_d, c_t = st.columns(2)
                d_o, t_o = c_d.date_input("Data", date.today(), format="DD/MM/YYYY", key="do"), c_t.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"], key="to")
                with st.form("om"):
                    m1, m2, m3, m4 = st.checkbox("Camera"), st.checkbox("Refettorio"), st.checkbox("Sala Fumo"), st.checkbox("Lavanderia")
                    if st.form_submit_button("REGISTRA PULIZIE"):
                        sel = [t for b,t in zip([m1,m2,m3,m4], ["Camera","Refettorio","Sala Fumo","Lavanderia"]) if b]
                        if oss_f and sel: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, f"{d_o.strftime('%d/%m/%Y')} {datetime.now().strftime('%H:%M')}", "Stabile", f"🧹 Pulizie: {', '.join(sel)}", "OSS", oss_f), True); st.rerun()
            with t_o2:
                c_d, c_t = st.columns(2)
                d_c, t_c = c_d.date_input("Data", date.today(), format="DD/MM/YYYY", key="dco"), c_t.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"], key="tco")
                txt = st.text_area("Nota OSS")
                if st.button("SALVA CONSEGNA OSS"):
                    if oss_f and txt: db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, f"{d_c.strftime('%d/%m/%Y')} {datetime.now().strftime('%H:%M')}", "Stabile", f"📝 [CONS OSS {t_c.upper()}] {txt}", "OSS", oss_f), True); st.rerun()

elif menu == "Monitoraggio":
    st.header("📊 Diario Clinico Unificato")
    p_mon = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_mon:
        with st.expander(f"👤 {nome.upper()}", expanded=True):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if log:
                html = "<table class='custom-table'><thead><tr><th>DATA / ORA</th><th>RUOLO</th><th>OPERATORE</th><th>NOTA CLINICA</th></tr></thead><tbody>"
                for d, r, o, n in log:
                    cls = "bg-appuntamento" if "📅" in n else f"bg-{r.lower()}"
                    html += f"<tr><td><b>{d}</b></td><td><span class='badge {cls}'>{r.upper()}</span></td><td><i>{o}</i></td><td>{n}</td></tr>"
                st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
            else: st.info("Nessuna attività registrata.")

elif menu == "Gestione":
    st.header("⚙️ Configurazione")
    with st.form("add_p"):
        nuovo = st.text_input("Nome e Cognome Paziente")
        if st.form_submit_button("AGGIUNGI PAZIENTE"):
            if nuovo: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), True); st.rerun()
    
    p_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        st.subheader("Pazienti Attivi")
        html = "<table class='custom-table'><tr><th>ID</th><th>NOME PAZIENTE</th><th>AZIONE</th></tr>"
        for idx, nome in p_list:
            html += f"<tr><td>{idx}</td><td>{nome}</td><td>"
            st.markdown(html, unsafe_allow_html=True)
            if st.button("ELIMINA", key=f"dp_{idx}"): db_run("DELETE FROM pazienti WHERE id=?", (idx,), True); st.rerun()
            html = ""
        st.markdown("</table>", unsafe_allow_html=True)
