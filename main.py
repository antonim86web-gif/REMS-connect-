import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. CONFIGURAZIONE PAGINA E CSS PROFESSIONALE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .main-title {text-align: center; color: #1e3a8a; font-weight: bold; margin-bottom:20px;}
    
    /* DIARIO CLINICO: STILE PULITO */
    .diario-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Inter', sans-serif;
        background: white;
    }
    .diario-table th {
        background-color: #f1f5f9;
        color: #475569;
        padding: 12px;
        text-align: left;
        border-bottom: 2px solid #e2e8f0;
        font-size: 0.8rem;
        text-transform: uppercase;
    }
    .diario-table td {
        padding: 10px 12px;
        border-bottom: 1px solid #f1f5f9;
        vertical-align: middle;
        font-size: 0.85rem;
    }
    .diario-table tr:hover { background-color: #f8fafc; }

    /* BADGES RUOLI */
    .badge {
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 700;
        color: white;
        display: inline-block;
    }
    .bg-psichiatra { background-color: #ef4444; }
    .bg-infermiere { background-color: #3b82f6; }
    .bg-educatore  { background-color: #10b981; }
    .bg-oss        { background-color: #f59e0b; }

    .card-box { border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 8px; background: white; }
    .saldo-box { padding: 15px; border-radius: 8px; background-color: #eff6ff; text-align: center; border: 1px solid #3b82f6; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE DATABASE CON CONTROLLO DUPLICATI ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, turni TEXT, medico TEXT, data_prescr TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS soldi (p_id INTEGER, data TEXT, desc TEXT, importo REAL, tipo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        # Logica Anti-Duplicato per gli eventi
        if "INSERT INTO eventi" in query:
            check = cur.execute("SELECT 1 FROM eventi WHERE id=? AND data=? AND nota=? AND op=?", 
                                (params[0], params[1], params[3], params[5])).fetchone()
            if check: return None # Salta l'inserimento se identico
            
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
            if pwd in ["rems2026", "admin2026"]:
                st.session_state.auth = True
                st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
menu = st.sidebar.radio("NAVIGAZIONE", ["Monitoraggio", "Equipe", "Gestione"])

# --- 5. LOGICA SEZIONI ---

if menu == "Gestione":
    st.header("⚙️ Gestione")
    t1, t2 = st.tabs(["➕ Aggiungi", "🗑️ Elimina"])
    with t1:
        with st.form("add_p"):
            n = st.text_input("Nome e Cognome")
            if st.form_submit_button("REGISTRA"):
                if n: db_run("INSERT INTO pazienti (nome) VALUES (?)", (n,), True); st.rerun()
    with t2:
        p_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_list:
            sel = st.selectbox("Seleziona", [p[1] for p in p_list])
            id_d = [p[0] for p in p_list if p[1] == sel][0]
            if st.button("ELIMINA DEFINITIVAMENTE"):
                db_run("DELETE FROM pazienti WHERE id=?", (id_d,), True); st.rerun()

elif menu == "Equipe":
    ruolo = st.sidebar.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti:
        p_nome = st.selectbox("Seleziona Paziente", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == p_nome][0]
        st.divider()

        if ruolo == "Psichiatra":
            st.subheader("📋 Medico")
            med_f = st.text_input("Firma Medico")
            with st.expander("➕ Nuova Terapia"):
                with st.form("p_form"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m, p, n = c1.checkbox("M"), c2.checkbox("P"), c3.checkbox("N")
                    if st.form_submit_button("PRESCRIVI"):
                        if med_f:
                            ts = ",".join([s for s, b in zip(["M","P","N"], [m,p,n]) if b])
                            db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, turni, medico, data_prescr) VALUES (?,?,?,?,?,?)", (p_id, f, d, ts, med_f, date.today().strftime("%d/%m/%Y")), True); st.rerun()
            
            ta = db_run("SELECT data_prescr, farmaco, dosaggio, turni, medico, row_id FROM terapie WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            for da, fa, ds, tu, me, rid in ta:
                st.markdown(f"<div class='card-box'><b>{fa} {ds}</b> ({tu}) - <i>{me}</i></div>", unsafe_allow_html=True)
                if st.button("Sospendi", key=f"s_{rid}"):
                    if med_f:
                        db_run("DELETE FROM terapie WHERE row_id=?", (rid,), True)
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"❌ SOSPESO: {fa}", "Psichiatra", med_f), True); st.rerun()

        elif ruolo == "Infermiere":
            st.subheader("💉 Infermieri")
            inf_f = st.text_input("Firma Infermiere")
            t1, t2, t3 = st.tabs(["💊 Terapia", "📊 Parametri", "📝 Consegna"])
            with t1:
                t_s = st.selectbox("Turno", ["Mattina", "Pomeriggio", "Notte"])
                ter = db_run("SELECT farmaco, dosaggio, turni, row_id FROM terapie WHERE p_id=?", (p_id,))
                for f, d, tu_p, rid in ter:
                    if tu_p and t_s[0] in tu_p:
                        c_a, c_b = st.columns([3,1])
                        es = c_a.radio(f"{f} ({d})", ["Assunta", "Rifiutata"], key=rid, horizontal=True)
                        if c_b.button("Salva", key=f"b_{rid}"):
                            if inf_f:
                                db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"[{t_s[0]}] {f} -> {es}", "Infermiere", inf_f), True); st.rerun()
            with t2:
                with st.form("par"):
                    c1,c2,c3,c4 = st.columns(4)
                    pa = c1.text_input("PA (es: 120/80)")
                    fc = c2.number_input("FC", 0, 200)
                    sat = c3.number_input("SpO2", 0, 100)
                    tc = c4.number_input("TC", 34.0, 42.0, 36.5)
                    if st.form_submit_button("REGISTRA"):
                        if inf_f:
                            db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📊 PA:{pa} FC:{fc} SpO2:{sat}% TC:{tc}°", "Infermiere", inf_f), True); st.rerun()
            with t3:
                txt = st.text_area("Nota di turno")
                if st.button("INVIA"):
                    if inf_f and txt:
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"📝 {txt}", "Infermiere", inf_f), True); st.rerun()

        elif ruolo == "Educatore":
            st.subheader("💰 Cassa")
            ed_f = st.text_input("Firma Educatore")
            mov = db_run("SELECT data, desc, importo, tipo, op FROM soldi WHERE p_id=? ORDER BY row_id DESC", (p_id,))
            saldo = sum([m[2] if m[3] == "Entrata" else -m[2] for m in mov])
            st.markdown(f'<div class="saldo-box">Disponibilità: € {saldo:.2f}</div>', unsafe_allow_html=True)
            with st.form("money"):
                tp = st.radio("Tipo", ["Entrata", "Uscita"], horizontal=True)
                im = st.number_input("Euro", 0.0)
                ds = st.text_input("Causale")
                if st.form_submit_button("REGISTRA"):
                    if ed_f:
                        db_run("INSERT INTO soldi (p_id, data, desc, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, date.today().strftime("%d/%m/%Y"), ds, im, tp, ed_f), True); st.rerun()

        elif ruolo == "OSS":
            st.subheader("🧹 OSS")
            with st.form("oss"):
                c1,c2 = st.columns(2)
                o1, o2, o3 = c1.checkbox("Camera"), c1.checkbox("Refettorio"), c1.checkbox("Sala Fumo")
                o4, o5 = c2.checkbox("Cortile"), c2.checkbox("Lavatrice")
                oss_f = st.text_input("Firma")
                if st.form_submit_button("CONFERMA"):
                    if oss_f:
                        ms = [t for b,t in zip([o1,o2,o3,o4,o5], ["Camera","Refettorio","Sala Fumo","Cortile","Lavatrice"]) if b]
                        db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m/%Y %H:%M"), "Stabile", f"🧹 Pulizie: {', '.join(ms)}", "OSS", oss_f), True); st.rerun()

# --- MONITORAGGIO: VISUALIZZAZIONE PROFESSIONALE ---
elif menu == "Monitoraggio":
    st.header("📊 Diario Clinico Integrato")
    p_mon = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    
    for pid, nome in p_mon:
        with st.expander(f"👤 {nome.upper()}", expanded=True):
            log = db_run("SELECT data, ruolo, op, nota FROM eventi WHERE id=? ORDER BY row_id DESC", (pid,))
            if log:
                html = "<table class='diario-table'><thead><tr><th width='15%'>DATA</th><th width='10%'>RUOLO</th><th width='15%'>OPERATORE</th><th width='60%'>NOTA</th></tr></thead><tbody>"
                for d, r, o, n in log:
                    cls = f"bg-{r.lower()}"
                    html += f"<tr><td><b>{d}</b></td><td><span class='badge {cls}'>{r.upper()}</span></td><td><i>{o}</i></td><td>{n}</td></tr>"
                st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
            else:
                st.info("Nessun dato registrato.")
