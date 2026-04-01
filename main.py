import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- FUNZIONE ORARIO ITALIA (UTC+2) ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v31.2 (INTEGRALE PORTATILE) ---
st.set_page_config(page_title="REMS Connect ELITE PRO v31.2", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .sidebar-footer { color: #ffffff !important; font-size: 0.8rem; text-align: center; margin-top: 20px; opacity: 0.8; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    
    /* AGENDA TABELLARE BLOCCHI GRANDI */
    .calendar-table { width: 100%; border-collapse: collapse; background-color: white; border: 2px solid #1e3a8a; }
    .calendar-table th { background-color: #1e3a8a; color: white; padding: 15px; text-transform: uppercase; font-size: 0.9rem; border: 1px solid #ffffff33; }
    .calendar-table td { border: 1px solid #cbd5e1; width: 14.28%; height: 150px; vertical-align: top; padding: 10px; position: relative; }
    .day-num-html { font-weight: 900; color: #64748b; font-size: 1.1rem; display: block; margin-bottom: 10px; border-bottom: 1px solid #f1f5f9; }
    .today-html { background-color: #f0fdf4 !important; border: 3px solid #22c55e !important; }
    .event-tag-html { background: #dbeafe; color: #1e40af; padding: 6px; border-radius: 4px; margin-bottom: 5px; font-size: 0.8rem; border-left: 4px solid #2563eb; font-weight: 600; line-height: 1.2; }
    .event-done-html { background: #f1f5f9; color: #94a3b8; border-left-color: #cbd5e1; text-decoration: line-through; }

    /* STILI CLINICI POST-IT */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-psicologo { background-color: #faf5ff; border-color: #a855f7; }
    .role-sociale { background-color: #fff7ed; border-color: #f97316; }
    .role-opsi { background-color: #f1f5f9; border-color: #0f172a; border-style: dashed; }

    .therapy-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .turn-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; }
    .mat-style { color: #d97706; } .pom-style { color: #2563eb; } .not-style { color: #4338ca; }
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
    
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .reparto-title { text-align: center; color: #1e3a8a; font-weight: 900; text-transform: uppercase; margin-bottom: 15px; border-bottom: 2px solid #1e3a8a33; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"
def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT)")
        
        if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
            cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
            conn.commit()

        if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
            for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
            for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            conn.commit()
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except: return []

def render_postits(p_id=None, limit=50, filter_role=None):
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE 1=1"
    params = []
    if p_id: query += " AND id=?"; params.append(p_id)
    if filter_role: query += " AND ruolo=?"; params.append(filter_role)
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    for d, r, o, nt in res:
        rm = {"Psichiatra":"psichiatra","Infermiere":"infermiere","Educatore":"educatore","OSS":"oss","Psicologo":"psicologo","Assistente Sociale":"sociale","OPSI":"opsi"}
        cls = f"role-{rm.get(r, 'oss')}"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div>{nt}</div></div>', unsafe_allow_html=True)

# --- SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO PRO</h2></div>", unsafe_allow_html=True)
    c_l, c_r = st.columns(2)
    with c_l:
        with st.form("login"):
            ui, pi = st.text_input("Username").lower().strip(), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (ui, hash_pw(pi)))
                if res: st.session_state.user_session = {"nome":res[0][0],"cognome":res[0][1],"ruolo":res[0][2],"uid":ui}; st.rerun()
                else: st.error("Credenziali Errate")
    with c_r:
        with st.form("reg"):
            ru, rp, rn, rc = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Nome"), st.text_input("Cognome")
            rq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("REGISTRA NUOVO UTENTE"):
                if ru and rp: db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (ru.lower(), hash_pw(rp), rn.capitalize(), rc.capitalize(), rq), True); st.success("Creato!")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)
opts = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto"]
if u['ruolo'] == "Admin": opts.append("⚙️ Admin")
nav = st.sidebar.radio("NAVIGAZIONE", opts)
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown("<br><br><br><div class='sidebar-footer'><b>Antony</b><br>Webmaster<br>ver. 31.2 Platinum</div>", unsafe_allow_html=True)

# --- 📅 MODULO AGENDA DINAMICA (TABELLARE GRANDI BLOCCHI) ---
if nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>🗓️ AGENDA MENSILE FULL SCREEN</h2></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c1: 
        if st.button("⬅️ Mese Prec."):
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1: st.session_state.cal_month=12; st.session_state.cal_year-=1
            st.rerun()
    with c2:
        mesi = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
        st.markdown(f"<h2 style='text-align:center;'>{mesi[st.session_state.cal_month-1]} {st.session_state.cal_year}</h2>", unsafe_allow_html=True)
    with c3:
        if st.button("Mese Succ. ➡️"):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12: st.session_state.cal_month=1; st.session_state.cal_year+=1
            st.rerun()

    cm, cs = st.columns([4, 1.2])
    with cm:
        start = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-01"
        end = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-31"
        evs = db_run("SELECT a.data, a.ora, p.nome, a.nota, a.stato, a.id_u FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data BETWEEN ? AND ?", (start, end))
        mev = {}
        for d,o,p,n,s,idu in evs:
            g = int(d.split("-")[2])
            if g not in mev: mev[g] = []
            mev[g].append({"o":o,"p":p,"n":n,"s":s,"id":idu})

        gh = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
        cal_obj = calendar.Calendar(0)
        weeks = cal_obj.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month)
        
        html = "<table class='calendar-table'><thead><tr>"
        for h in gh: html += f"<th>{h}</th>"
        html += "</tr></thead><tbody>"
        
        for week in weeks:
            html += "<tr>"
            for d in week:
                if d == 0:
                    html += "<td style='background:#f8fafc;'></td>"
                else:
                    cur_date = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{d:02d}"
                    cls = "today-html" if cur_date == oggi_iso else ""
                    day_events = "".join([f"<div class='event-tag-html {'event-done-html' if e['s']=='COMPLETATO' else ''}'><b>{e['o']}</b> {e['p']}</div>" for e in mev.get(d, [])])
                    html += f"<td class='{cls}'><span class='day-num-html'>{d}</span>{day_events}</td>"
            html += "</tr>"
        html += "</tbody></table>"
        st.markdown(html, unsafe_allow_html=True)

    with cs:
        with st.form("n_a"):
            st.subheader("Nuovo")
            pl = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
            sp = st.selectbox("Paziente", [p[1] for p in pl])
            sd, stm, sn = st.date_input("Data"), st.time_input("Ora"), st.text_input("Causale")
            if st.form_submit_button("PROGRAMMA"):
                pid = [p[0] for p in pl if p[1]==sp][0]
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore) VALUES (?,?,?,?,'PROGRAMMATO',?)", (pid, str(sd), str(stm)[:5], sn, firma_op), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📅 Appuntamento: {sn}", u['ruolo'], firma_op), True); st.rerun()
        st.divider()
        for a in [e for g in mev.values() for e in g if e['s']=='PROGRAMMATO']:
            c_a, c_b = st.columns([3,1])
            c_a.write(f"**{a['p']}** {a['o']}")
            if c_b.button("OK", key=f"f{a['id']}"): db_run("UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?", (a['id'],), True); st.rerun()

# --- MODULO MAPPA ---
elif nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>TABELLONE VISIVO POSTI LETTO</h2></div>", unsafe_allow_html=True)
    stanze_db = db_run("SELECT id, reparto, tipo FROM stanze ORDER BY id")
    paz_db = db_run("SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p LEFT JOIN assegnazioni a ON p.id = a.p_id")
    mappa = {s[0]: {'rep': s[1], 'tipo': s[2], 'letti': {1: None, 2: None}} for s in stanze_db}
    for pid, pnome, sid, letto in paz_db:
        if sid in mappa: mappa[sid]['letti'][letto] = {'id': pid, 'nome': pnome}
    c_a, c_b = st.columns(2)
    for r_code, col_obj in [("A", c_a), ("B", c_b)]:
        with col_obj:
            st.markdown(f"<div class='map-reparto'><div class='reparto-title'>Reparto {r_code}</div><div class='stanza-grid'>", unsafe_allow_html=True)
            for s_id, s_info in {k:v for k,v in mappa.items() if v['rep']==r_code}.items():
                p_count = len([v for v in s_info['letti'].values() if v])
                cls = "stanza-isolamento" if s_info['tipo']=="ISOLAMENTO" and p_count>0 else ("stanza-piena" if p_count==2 else ("stanza-occupata" if p_count==1 else ""))
                st.markdown(f"<div class='stanza-tile {cls}'><div class='stanza-header'>{s_id} <small>{s_info['tipo']}</small></div>", unsafe_allow_html=True)
                for l in [1, 2]:
                    p = s_info['letti'][l]
                    st.markdown(f"<div class='letto-slot'>L{l}: <b>{p['nome'] if p else 'Libero'}</b></div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)
    with st.expander("Sposta Paziente"):
        p_list = db_run("SELECT id, nome FROM pazienti")
        sel_p = st.selectbox("Paziente", [p[1] for p in p_list], index=None)
        if sel_p:
            pid = [p[0] for p in p_list if p[1]==sel_p][0]
            posti_liberi = [f"{sid}-L{l}" for sid, si in mappa.items() for l, po in si['letti'].items() if not po]
            dest = st.selectbox("Destinazione", posti_liberi)
            mot = st.text_input("Motivo")
            if st.button("ESEGUI") and mot:
                dsid, dl = dest.split("-L")
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True)
                db_run("INSERT INTO assegnazioni VALUES (?,?,?,?)", (pid, dsid, int(dl), get_now_it().strftime("%Y-%m-%d")), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 Trasferimento in {dsid} L{dl}. Motivo: {mot}", u['ruolo'], firma_op), True); st.rerun()

elif nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"📁 SCHEDA PAZIENTE: {nome}"): render_postits(pid)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>", unsafe_allow_html=True)
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": ruolo_corr = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = get_now_it(); oggi = now.strftime("%d/%m/%Y")

        if ruolo_corr == "Psicologo":
            t1, t2 = st.tabs(["🧠 COLLOQUIO", "📝 TEST/VALUTAZIONE"])
            with t1:
                with st.form("f_psi"):
                    txt = st.text_area("Sintesi Colloquio Clinico")
                    if st.form_submit_button("SALVA NOTA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧠 {txt}", "Psicologo", firma_op), True); st.rerun()
            with t2:
                with st.form("f_test"):
                    test_n = st.text_input("Nome Test / Scala"); test_r = st.text_area("Risultato/Osservazioni")
                    if st.form_submit_button("REGISTRA VALUTAZIONE"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📊 TEST {test_n}: {test_r}", "Psicologo", firma_op), True); st.rerun()
        elif ruolo_corr == "Assistente Sociale":
            t1, t2 = st.tabs(["🤝 RETE TERRITORIALE", "🏠 PROGETTO POST-DIMISSIONE"])
            with t1:
                with st.form("f_soc"):
                    cont = st.text_input("Ente/Contatto"); txt = st.text_area("Esito colloquio")
                    if st.form_submit_button("SALVA ATTIVITÀ"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🤝 CONTATTO {cont}: {txt}", "Assistente Sociale", firma_op), True); st.rerun()
            with t2:
                with st.form("f_prog"):
                    prog = st.text_area("Aggiornamento Progetto di Reinserimento")
                    if st.form_submit_button("AGGIORNA PROGETTO"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🏠 PROGETTO: {prog}", "Assistente Sociale", firma_op), True); st.rerun()
        elif ruolo_corr == "OPSI":
            t1, t2 = st.tabs(["🛡️ VIGILANZA", "🚨 SEGNALAZIONE CRITICITÀ"])
            with t1:
                with st.form("f_opsi"):
                    cond = st.multiselect("Stato ambiente:", ["Tranquillo", "Agitato", "Ispezione camera"]); nota = st.text_input("Note")
                    if st.form_submit_button("REGISTRA TURNO"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🛡️ VIGILANZA: {', '.join(cond)} | {nota}", "OPSI", firma_op), True); st.rerun()
            with t2:
                with st.form("f_crit"):
                    tipo = st.selectbox("Livello Criticità", ["BASSO", "MEDIO", "ALTO"]); dett = st.text_area("Dettaglio")
                    if st.form_submit_button("INVIA SEGNALAZIONE"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🚨 CRITICITÀ {tipo}: {dett}", "OPSI", firma_op), True); st.rerun()
        elif ruolo_corr == "Psichiatra":
            t1, t2 = st.tabs(["➕ Nuova Prescrizione", "📝 Gestione Terapie"])
            with t1:
                with st.form("f_ps"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"➕ Prescritto: {f} {d}", "Psichiatra", firma_op), True); st.rerun()
            with t2:
                for tid, fn, ds, m_v, p_v, n_v in db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,)):
                    with st.expander(f"Modifica: {fn}"):
                        with st.form(key=f"m_{tid}"):
                            nf, nd = st.text_input("Farmaco", fn), st.text_input("Dose", ds); cc1,cc2,cc3 = st.columns(3); nm,np,nn = cc1.checkbox("MAT",bool(m_v)),cc2.checkbox("POM",bool(p_v)),cc3.checkbox("NOT",bool(n_v))
                            if st.form_submit_button("AGGIORNA"): db_run("UPDATE terapie SET farmaco=?, dose=?, mat=?, pom=?, nott=? WHERE id_u=?", (nf, nd, int(nm), int(np), int(nn), tid), True); st.rerun()
                            if st.form_submit_button("SOSPENDE"): db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()
        elif ruolo_corr == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 TERAPIA", "💓 PARAMETRI", "📝 CONSEGNE"])
            with t1:
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                cols = st.columns(3); turni = [("MAT", 3, "mat-style", "☀️"), ("POM", 4, "pom-style", "🌤️"), ("NOT", 5, "not-style", "🌙")]
                for i, (t_n, t_idx, t_css, t_ico) in enumerate(turni):
                    with cols[i]:
                        for f in [x for x in terapie if x[t_idx]]:
                            check = db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%SOMM ({t_n}): {f[1]}%", f"{oggi}%"))
                            if not check:
                                st.markdown(f"<div class='therapy-container'><div class='turn-header {t_css}'>{t_ico} {t_n}</div><b>{f[1]}</b><br>{f[2]}</div>", unsafe_allow_html=True)
                                if st.button(f"CONFERMA", key=f"ok_{f[0]}_{t_n}"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({t_n}): {f[1]}", "Infermiere", firma_op), True); st.rerun()
            with t2:
                with st.form("vit"):
                    pa,fc,sat,tc,gl=st.text_input("PA"),st.text_input("FC"),st.text_input("SatO2"),st.text_input("TC"),st.text_input("Glicemia")
                    if st.form_submit_button("REGISTRA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💓 PA:{pa} FC:{fc} Sat:{sat} TC:{tc} Gl:{gl}", "Infermiere", firma_op), True); st.rerun()
            with t3:
                with st.form("ni"):
                    txt = st.text_area("Consegna Clinica"); 
                    if st.form_submit_button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt, "Infermiere", firma_op), True); st.rerun()
        elif ruolo_corr == "OSS":
            with st.form("oss_f"):
                mans = st.multiselect("Mansioni:", ["Igiene", "Cambio", "Pulizia", "Letto"]); txt = st.text_area("Note")
                if st.form_submit_button("REGISTRA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {txt}", "OSS", firma_op), True); st.rerun()
        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 CASSA", "📝 CONSEGNA EDUCATIVA"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,)); saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("cs"):
                    tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi, cau, im, tp, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True); st.rerun()
            with t2:
                with st.form("edu_cons"):
                    txt_edu = st.text_area("Osservazioni Educative")
                    if st.form_submit_button("SALVA CONSEGNA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📝 {txt_edu}", "Educatore", firma_op), True); st.rerun()
        st.divider(); render_postits(p_id)

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO ADMIN</h2></div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["UTENTI", "PAZIENTI", "LOG EVENTI"])
    with tab1:
        for us, un, uc, uq in db_run("SELECT user, nome, cognome, qualifica FROM utenti"):
            c1, c2 = st.columns([0.8, 0.2]); c1.write(f"**{un} {uc}** ({uq})")
            if us != "admin":
                if c2.button("ELIMINA", key=f"d_{us}"): db_run("DELETE FROM utenti WHERE user=?", (us,), True); st.rerun()
            else: c2.markdown("🔒 *Protetto*")
    with tab2:
        with st.form("np"):
            np_val = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np_val.upper(),), True); st.rerun()
        for pid, pn in db_run("SELECT id, nome FROM pazienti"):
            c1, c2 = st.columns([0.8, 0.2]); c1.write(pn)
            if c2.button("ELIMINA", key=f"dp_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True); st.rerun()
    with tab3:
        lista_p = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        filtro_p = st.selectbox("Filtra per Paziente:", ["TUTTI"] + [p[1] for p in lista_p])
        query_log = "SELECT e.id_u, e.data, e.ruolo, e.op, e.nota, p.nome FROM eventi e JOIN pazienti p ON e.id = p.id"
        params_log = []
        if filtro_p != "TUTTI": query_log += " WHERE p.nome = ?"; params_log.append(filtro_p)
        tutti_log = db_run(query_log + " ORDER BY e.id_u DESC", tuple(params_log))
        if st.button("🚨 RESET TOTALE LOG"): db_run("DELETE FROM eventi", (), True); st.rerun()
        st.divider()
        for lid, ldt, lru, lop, lnt, lpnome in tutti_log:
            cl1, cl2 = st.columns([0.85, 0.15])
            cl1.write(f"[{ldt}] **{lpnome}** - **{lru}** ({lop}): {lnt}")
            if cl2.button("🗑️", key=f"del_log_{lid}"): db_run("DELETE FROM eventi WHERE id_u=?", (lid,), True); st.rerun()
