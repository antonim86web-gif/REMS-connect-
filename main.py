import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- 1. AGGIORNAMENTO STRUTTURA DATABASE (MIGRAZIONE DINAMICA) ---
def inizializza_db():
    conn = sqlite3.connect('rems_final_v12.db', check_same_thread=False)
    c = conn.cursor()
    # Creazione Tabelle Core
    c.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE)")
    c.execute("CREATE TABLE IF NOT EXISTS eventi (id_u INTEGER PRIMARY KEY AUTOINCREMENT, id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS terapie (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS cassa (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))")
    
    # Check per colonne legacy o nuove
    try: c.execute("ALTER TABLE eventi ADD COLUMN tipo_evento TEXT")
    except: pass
    
    # Popolamento iniziale Utenti
    if c.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
        pw_admin = hashlib.sha256(str.encode("perito2026")).hexdigest()
        c.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", pw_admin, "SUPER", "USER", "Admin"))
    
    # Popolamento iniziale Stanze (Reparto A e B)
    if c.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
        for i in range(1, 7): c.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "LOCK-UP" if i==6 else "STANDARD"))
        for i in range(1, 11): c.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "LOCK-UP" if i==10 else "STANDARD"))
    
    conn.commit()
    conn.close()

inizializza_db()

# --- 2. UTILITY & SECURITY ---
def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def get_now_it(): return datetime.now(timezone.utc) + timedelta(hours=2)

def db_run(query, params=(), commit=False):
    with sqlite3.connect('rems_final_v12.db', check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore Query: {e}")
            return []

# --- 3. CSS CUSTOM (STILE ELITE PRO) ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* Sidebar & Background */
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 2px solid #334155; }
    [data-testid="stSidebar"] * { color: #f8fafc !important; }
    .sidebar-title { color: #38bdf8 !important; font-size: 1.8rem; font-weight: 800; text-align: center; border-bottom: 2px solid #334155; padding-bottom: 15px; margin-bottom: 20px; }
    
    /* Banner & Cards */
    .section-banner { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 25px; border-radius: 15px; text-align: center; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3); margin-bottom: 30px; }
    .stButton>button { border-radius: 8px; font-weight: 600; transition: all 0.3s; }
    
    /* Post-it & Diario */
    .postit { padding: 18px; border-radius: 10px; margin-bottom: 15px; border-left: 12px solid; box-shadow: 0 4px 6px rgba(0,0,0,0.05); background: white; color: #1e293b; }
    .postit-header { font-weight: 800; font-size: 0.8rem; display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    
    .role-psichiatra { border-color: #ef4444; background: #fff1f2; }
    .role-infermiere { border-color: #3b82f6; background: #eff6ff; }
    .role-educatore { border-color: #10b981; background: #ecfdf5; }
    .role-oss { border-color: #64748b; background: #f8fafc; }
    .role-psicologo { border-color: #a855f7; background: #faf5ff; }
    
    /* Mappa Stanze */
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; border-top: 6px solid #94a3b8; transition: 0.3s; }
    .stanza-lockup { border-top-color: #dc2626 !important; background: #fef2f2; }
    .stanza-piena { background: #f1f5f9; border-top-color: #1e3a8a; }
    .letto-slot { font-size: 0.85rem; padding: 5px; border-radius: 5px; margin: 2px 0; background: #f8fafc; border: 1px dashed #cbd5e1; }
    .letto-occupato { background: #dcfce7; border-style: solid; border-color: #22c55e; font-weight: 700; }
    
    /* Tooltip Agenda */
    .event-tag-html { font-size: 0.7rem; background: #3b82f6; color: white; padding: 3px 6px; border-radius: 4px; margin-bottom: 4px; position: relative; cursor: pointer; }
    .event-tag-html .tooltip-text { visibility: hidden; width: 200px; background: #1e293b; color: #fff; text-align: left; padding: 10px; border-radius: 8px; position: absolute; z-index: 100; bottom: 125%; left: 0; opacity: 0; transition: 0.3s; box-shadow: 0 10px 15px rgba(0,0,0,0.2); pointer-events: none; }
    .event-tag-html:hover .tooltip-text { visibility: visible; opacity: 1; }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNZIONE RENDER DIARIO ---
def render_postits(p_id, limit=60):
    st.markdown("### 📋 Diario Clinico Integrato")
    filtro = st.multiselect("Filtra per figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"], key=f"filter_{p_id}")
    
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
    params = [p_id]
    if filtro:
        query += f" AND ruolo IN ({','.join(['?']*len(filtro))})"
        params.extend(filtro)
    
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    for d, r, o, nt in res:
        cls_map = {"Psichiatra":"psichiatra", "Infermiere":"infermiere", "Educatore":"educatore", "OSS":"oss", "Psicologo":"psicologo", "OPSI":"opsi"}
        cls = f"role-{cls_map.get(r, 'oss')}"
        st.markdown(f'''
            <div class="postit {cls}">
                <div class="postit-header"><span>👤 {o}</span> <span>🕒 {d}</span></div>
                <div style="font-size: 0.95rem;">{nt}</div>
            </div>
        ''', unsafe_allow_html=True)

# --- 5. GESTIONE LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'month' not in st.session_state: st.session_state.month = get_now_it().month
if 'year' not in st.session_state: st.session_state.year = get_now_it().year

if not st.session_state.user:
    st.markdown("<div class='section-banner'><h1>🏥 REMS CONNECT PRO v28.9</h1><p>Sistema Gestionale per Residenze per l'Esecuzione delle Misure di Sicurezza</p></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Autenticazione")
        with st.form("l_f"):
            u_i = st.text_input("Username").lower()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                val = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if val:
                    st.session_state.user = {"nome": val[0][0], "cognome": val[0][1], "ruolo": val[0][2], "uid": u_i}
                    st.rerun()
                else: st.error("Accesso Negato")
    with c2:
        st.subheader("Registrazione Operatore")
        with st.form("r_f"):
            ru, rp, rn, rc = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Nome"), st.text_input("Cognome")
            rq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (ru.lower(), hash_pw(rp), rn, rc, rq), True)
                st.success("Operatore registrato!")
    st.stop()

# --- 6. VARIABILI DI SESSIONE ---
usr = st.session_state.user
firma = f"{usr['nome']} {usr['cognome']} ({usr['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")

# --- 7. SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>REMS-CONNECT</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div style='text-align:center; color:#10b981; font-weight:800; margin-bottom:20px;'>● {usr['nome'].upper()} {usr['cognome'].upper()}</div>", unsafe_allow_html=True)

nav = st.sidebar.radio("MENU PRINCIPALE", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto", "⚙️ Amministrazione"])

if st.sidebar.button("CHIUDI SESSIONE"):
    st.session_state.user = None
    st.rerun()

# --- 8. LOGICA NAVIGAZIONE ---

if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in pazienti:
        with st.expander(f"📂 CARTELLA CLINICA: {nome}"):
            render_postits(pid)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>OPERATIVITÀ EQUIPE MULTIDISCIPLINARE</h2></div>", unsafe_allow_html=True)
    curr_r = usr['ruolo'] if usr['ruolo'] != "Admin" else st.selectbox("Modalità Ruolo:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
    
    p_list = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if not p_list: st.warning("Nessun paziente in anagrafica."); st.stop()
    
    p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_list])
    p_id = [p[0] for p in p_list if p[1] == p_sel][0]
    now_str = get_now_it().strftime("%d/%m/%Y %H:%M")

    # LOGICA PSICHIATRA
    if curr_r == "Psichiatra":
        t1, t2, t3 = st.tabs(["💊 TERAPIA", "📝 NOTE MEDICHE", "📊 STORICO"])
        with t1:
            with st.form("t_f"):
                f, d = st.text_input("Farmaco"), st.text_input("Dosaggio")
                c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("PRESCRIVI"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now_str, f"➕ NUOVA PRESCRIZIONE: {f} {d}", "Psichiatra", firma), True)
                    st.rerun()
            st.write("---")
            for tid, tf, td in db_run("SELECT id_u, farmaco, dose FROM terapie WHERE p_id=?", (p_id,)):
                st.write(f"💊 {tf} - {td}")
                if st.button("SOSPENDE", key=f"del_t_{tid}"):
                    db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now_str, f"🚫 SOSPESO FARMACO: {tf}", "Psichiatra", firma), True)
                    st.rerun()
        with t2:
            with st.form("m_n_f"):
                nota_m = st.text_area("Consegna Medica / Osservazioni Cliniche", height=150)
                if st.form_submit_button("REGISTRA NOTA MEDICA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now_str, f"👨‍⚕️ NOTA MEDICA: {nota_m}", "Psichiatra", firma), True)
                    st.rerun()

    # LOGICA INFERMIERE
    elif curr_r == "Infermiere":
        t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONE", "💓 PARAMETRI", "📝 CONSEGNE"])
        with t1:
            terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            col1, col2, col3 = st.columns(3)
            turni = [("MATTINA", 3, "☀️"), ("POMERIGGIO", 4, "🌤️"), ("NOTTE", 5, "🌙")]
            for i, (tn, idx, ico) in enumerate(turni):
                with [col1, col2, col3][i]:
                    st.subheader(f"{ico} {tn}")
                    for f in [x for x in terapie if x[idx]]:
                        if st.button(f"OK {f[1]}", key=f"s_{f[0]}_{tn}"):
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now_str, f"✔️ SOMMINISTRATO ({tn}): {f[1]} {f[2]}", "Infermiere", firma), True)
                            st.success(f"{f[1]} somministrato")
        with t2:
            with st.form("p_f"):
                pa, fc, tc, sat = st.text_input("PA"), st.text_input("FC"), st.text_input("TC"), st.text_input("SatO2")
                if st.form_submit_button("SALVA PARAMETRI"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now_str, f"💓 PARAMETRI: PA {pa} | FC {fc} | TC {tc} | Sat {sat}", "Infermiere", firma), True)
                    st.rerun()
        with t3:
            with st.form("i_c_f"):
                nota_i = st.text_area("Consegna Infermieristica")
                if st.form_submit_button("SALVA CONSEGNA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now_str, f"📝 CONSEGNA: {nota_i}", "Infermiere", firma), True)
                    st.rerun()

    # LOGICA EDUCATORE
    elif curr_r == "Educatore":
        t1, t2 = st.tabs(["💰 CASSA", "📝 ATTIVITÀ"])
        with t1:
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
            st.markdown(f"<div style='background:#f0fdf4; padding:20px; border-radius:10px; text-align:center; border:2px solid #22c55e;'><small>SALDO ATTUALE</small><h2 style='color:#166534; margin:0;'>€ {saldo:.2f}</h2></div>", unsafe_allow_html=True)
            with st.form("c_f"):
                tipo_c = st.selectbox("Movimento", ["USCITA", "ENTRATA"])
                imp = st.number_input("Euro", min_value=0.0)
                cau = st.text_input("Causale")
                if st.form_submit_button("ESEGUI MOVIMENTO"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi_iso, cau, imp, tipo_c, firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now_str, f"💰 {tipo_c}: €{imp} - {cau}", "Educatore", firma), True)
                    st.rerun()
        with t2:
            with st.form("e_a_f"):
                txt_e = st.text_area("Nota Educativa")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now_str, f"🎨 ATTIVITÀ: {txt_e}", "Educatore", firma), True)
                    st.rerun()

    # LOGICA OSS / OPSI
    elif curr_r in ["OSS", "OPSI"]:
        with st.form("o_f"):
            tipo_o = "🧹 IGIENE/ASSISTENZA" if curr_r=="OSS" else "🛡️ SORVEGLIANZA"
            txt_o = st.text_area(f"Nota {curr_r}")
            if st.form_submit_button("SALVA NOTA"):
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now_str, f"{tipo_o}: {txt_o}", curr_r, firma), True)
                st.rerun()

    st.divider()
    render_postits(p_id)

elif nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA SCADENZE</h2></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c1: 
        if st.button("⬅️ Mese Prec."): st.session_state.month -= 1; st.rerun()
    with c2: 
        st.markdown(f"<h3 style='text-align:center;'>{calendar.month_name[st.session_state.month]} {st.session_state.year}</h3>", unsafe_allow_html=True)
    with c3: 
        if st.button("Mese Succ. ➡️"): st.session_state.month += 1; st.rerun()

    # Calcolo Appuntamenti
    s_d = f"{st.session_state.year}-{st.session_state.month:02d}-01"
    e_d = f"{st.session_state.year}-{st.session_state.month:02d}-31"
    apps = db_run("SELECT a.data, p.nome, a.ora, a.tipo_evento, a.nota FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.data BETWEEN ? AND ? AND a.stato='PROGRAMMATO'", (s_d, e_d))
    
    mappa = {}
    for d_a, p_n, h_a, t_a, n_a in apps:
        g = int(d_a.split("-")[2])
        if g not in mappa: mappa[g] = []
        mappa[g].append(f'<div class="event-tag-html">📌 {p_n}<span class="tooltip-text"><b>{t_a}</b> ({h_a})<br>{n_a}</span></div>')

    # Render Calendario HTML
    cal_html = "<table width='100%' style='border-collapse: collapse; table-layout: fixed; background:white; border-radius:15px; overflow:hidden;'><tr>"
    for d_n in ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"]: cal_html += f"<th style='padding:15px; background:#f1f5f9; color:#1e3a8a;'>{d_n}</th>"
    cal_html += "</tr>"
    
    for week in calendar.Calendar(0).monthdayscalendar(st.session_state.year, st.session_state.month):
        cal_html += "<tr>"
        for day in week:
            if day == 0: cal_html += "<td style='background:#f8fafc; border:1px solid #e2e8f0;'></td>"
            else:
                is_today = "background:#dcfce7;" if f"{st.session_state.year}-{st.session_state.month:02d}-{day:02d}" == oggi_iso else ""
                cal_html += f"<td style='height:120px; vertical-align:top; border:1px solid #e2e8f0; padding:5px; {is_today}'><b style='color:#64748b;'>{day}</b><br>{''.join(mappa.get(day, []))}</td>"
        cal_html += "</tr>"
    st.markdown(cal_html + "</table>", unsafe_allow_html=True)
    
    with st.expander("➕ REGISTRA NUOVO APPUNTAMENTO / USCITA"):
        with st.form("n_a_f"):
            p_l = db_run("SELECT id, nome FROM pazienti")
            p_a = st.selectbox("Paziente", [p[1] for p in p_l])
            pid_a = [p[0] for p in p_l if p[1]==p_a][0]
            d_a, h_a = st.date_input("Data"), st.time_input("Ora")
            t_a, n_a = st.selectbox("Tipo", ["Uscita Esterna", "Visita Familiare", "Udienza Tribunale", "Visita Specialistica"]), st.text_area("Note")
            if st.form_submit_button("REGISTRA APPUNTAMENTO"):
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore, tipo_evento) VALUES (?,?,?,?,'PROGRAMMATO',?,?)", (pid_a, str(d_a), str(h_a)[:5], n_a, firma, t_a), True)
                st.rerun()

elif nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>TABELLONE VISIVO OCCUPAZIONE POSTI LETTO</h2></div>", unsafe_allow_html=True)
    
    stanze = db_run("SELECT id, reparto, tipo FROM stanze")
    assegnazioni = db_run("SELECT p.nome, a.stanza_id, a.letto, p.id FROM pazienti p JOIN assegnazioni a ON p.id = a.p_id")
    occ = {(sid, l): (nome, pid) for nome, sid, l, pid in assegnazioni}
    
    col_a, col_b = st.columns(2)
    for i, rep in enumerate(["A", "B"]):
        with [col_a, col_b][i]:
            st.markdown(f"<div class='reparto-title' style='text-align:center; padding:10px; background:#1e3a8a; color:white; border-radius:10px; margin-bottom:15px;'>REPARTO {rep}</div>", unsafe_allow_html=True)
            st_grid = st.columns(2)
            for idx, (sid, srep, stip) in enumerate([s for s in stanze if s[1]==rep]):
                with st_grid[idx % 2]:
                    is_lock = "stanza-lockup" if stip == "LOCK-UP" else ""
                    st.markdown(f"<div class='stanza-tile {is_lock}'><div style='font-weight:900; color:#1e3a8a;'>Stanza {sid} <small style='color:#ef4444;'>{stip}</small></div>", unsafe_allow_html=True)
                    for l in [1, 2]:
                        p_info = occ.get((sid, l))
                        cls_l = "letto-occupato" if p_info else ""
                        nome_p = p_info[0] if p_info else "Libero"
                        st.markdown(f"<div class='letto-slot {cls_l}'>L{l}: {nome_p}</div>", unsafe_allow_html=True)
                    st.markdown("</div><br>", unsafe_allow_html=True)

    with st.expander("🔄 GESTIONE SPOSTAMENTI E TRASFERIMENTI"):
        with st.form("move_f"):
            p_l = db_run("SELECT id, nome FROM pazienti")
            p_m = st.selectbox("Paziente da spostare", [p[1] for p in p_l])
            pm_id = [p[0] for p in p_l if p[1]==p_m][0]
            s_l = db_run("SELECT id FROM stanze")
            s_m = st.selectbox("Nuova Stanza", [s[0] for s in s_list] if 's_list' in locals() else [s[0] for s in s_l])
            l_m = st.selectbox("Letto", [1, 2])
            motivo = st.text_input("Motivo dello spostamento")
            if st.form_submit_button("CONFERMA TRASFERIMENTO"):
                db_run("INSERT OR REPLACE INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)", (pm_id, s_m, l_m, oggi_iso), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pm_id, now_str, f"🔄 TRASFERIMENTO: Spostato in Stanza {s_m} (L{l_m}). Motivo: {motivo}", usr['ruolo'], firma), True)
                st.success("Paziente trasferito con successo.")
                st.rerun()

elif nav == "⚙️ Amministrazione":
    st.markdown("<div class='section-banner'><h2>GESTIONE ANAGRAFICA E SISTEMA</h2></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["👥 ANAGRAFICA PAZIENTI", "🔐 SICUREZZA"])
    with t1:
        with st.form("new_p"):
            n_p = st.text_input("Nome e Cognome Paziente").upper()
            if st.form_submit_button("AGGIUNGI A REGISTRO"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (n_p,), True)
                st.success("Paziente inserito.")
                st.rerun()
        st.write("---")
        for pid, pnm in db_run("SELECT id, nome FROM pazienti"):
            c_a, c_b = st.columns([0.8, 0.2])
            c_a.write(f"**{pnm}** (ID: {pid})")
            if c_b.button("ELIMINA", key=f"del_p_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                st.rerun()
