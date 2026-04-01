import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd

# --- FUNZIONE ORARIO ITALIA (UTC+2) ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v28.7 (INTEGRALE) ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.7", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    .stButton>button[kind="secondary"] { background-color: #22c55e !important; color: white !important; border: none !important; width: 100%; font-weight: 700; }
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-psicologo { background-color: #faf5ff; border-color: #a855f7; }
    .role-sociale { background-color: #fff7ed; border-color: #f97316; }
    .role-opsi { background-color: #f1f5f9; border-color: #0f172a; border-style: dashed; }

    .app-card { background-color: #fffbeb; border: 1px solid #fef3c7; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 6px solid #d97706; color: #1e293b; }
    .therapy-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .turn-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; }
    .mat-style { color: #d97706; } .pom-style { color: #2563eb; } .not-style { color: #4338ca; }
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
    
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .reparto-title { text-align: center; color: #1e3a8a; font-weight: 900; text-transform: uppercase; margin-bottom: 15px; border-bottom: 2px solid #1e3a8a33; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; }
    .stanza-header { font-weight: 800; font-size: 0.8rem; color: #475569; margin-bottom: 5px; border-bottom: 1px solid #eee; }
    .letto-slot { font-size: 0.8rem; color: #1e293b; padding: 2px 0; }
    .stanza-occupata { border-left-color: #22c55e; background-color: #f0fdf4; }
    .stanza-piena { border-left-color: #2563eb; background-color: #eff6ff; }
    .stanza-isolamento { border-left-color: #ef4444; background-color: #fef2f2; border-width: 2px; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        # FIX OPERATIONAL ERROR: Reset strutturale se le colonne non corrispondono
        try:
            cur.execute("SELECT user, pwd, nome, cognome, qualifica FROM utenti LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("DROP TABLE IF EXISTS utenti")
        
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))")
        
        if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
            for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
            for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            conn.commit()
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def render_postits(p_id=None, limit=50, filter_role=None):
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE 1=1"
    params = []
    if p_id: query += " AND id=?"; params.append(p_id)
    if filter_role: query += " AND ruolo=?"; params.append(filter_role)
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    for d, r, o, nt in res:
        role_map = {"Psichiatra":"psichiatra", "Infermiere":"infermiere", "Educatore":"educatore", "OSS":"oss", "Psicologo":"psicologo", "Assistente Sociale":"sociale", "OPSI":"opsi"}
        cls = f"role-{role_map.get(r, 'oss')}"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div>{nt}</div></div>', unsafe_allow_html=True)

# --- SESSIONE E LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO PRO</h2></div>", unsafe_allow_html=True)
    c_l, c_r = st.columns(2)
    with c_l:
        st.subheader("Login")
        with st.form("login_main"):
            u_i = st.text_input("Username").lower().strip()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    st.rerun()
                else: st.error("Errore login: Credenziali errate o utente non creato.")
    with c_r:
        st.subheader("Registrazione")
        with st.form("reg_main"):
            ru = st.text_input("Scegli Username").lower().strip()
            rp = st.text_input("Scegli Password", type="password")
            rn = st.text_input("Nome")
            rc = st.text_input("Cognome")
            rq = st.selectbox("Qualifica Professionale", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI", "Admin"])
            if st.form_submit_button("REGISTRA NUOVO UTENTE"):
                if ru and rp and rn and rc:
                    esistente = db_run("SELECT user FROM utenti WHERE user=?", (ru,))
                    if esistente: st.error("Username già in uso.")
                    else:
                        db_run("INSERT INTO utenti (user, pwd, nome, cognome, qualifica) VALUES (?,?,?,?,?)", (ru, hash_pw(rp), rn.capitalize(), rc.capitalize(), rq), True)
                        st.success(f"Profilo {rq} creato correttamente! Ora puoi accedere.")
                else: st.warning("Compila tutti i campi.")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)
opts = ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Appuntamenti", "🗺️ Mappa Posti Letto"]
if u['ruolo'] == "Admin": opts.append("⚙️ Admin")
nav = st.sidebar.radio("NAVIGAZIONE", opts)
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- MODULO MAPPA ---
if nav == "🗺️ Mappa Posti Letto":
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
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 Trasferimento in {dsid} L{dl}. Motivo: {mot}", u['ruolo'], firma_op), True)
                st.rerun()

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

elif nav == "📅 Appuntamenti":
    st.markdown("<div class='section-banner'><h2>GESTIONE APPUNTAMENTI</h2></div>", unsafe_allow_html=True)
    t_new, t_agenda = st.tabs(["➕ PROGRAMMA", "📋 AGENDA"])
    with t_new:
        with st.form("f_new_app"):
            p_l = db_run("SELECT id, nome FROM pazienti")
            if p_l:
                ps = st.selectbox("Paziente", [p[1] for p in p_l]); pid = [p[0] for p in p_l if p[1]==ps][0]; d, h = st.date_input("Data"), st.time_input("Ora"); n = st.text_input("Causale")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore) VALUES (?,?,?,?,'PROGRAMMATO',?)", (pid, str(d), str(h)[:5], n, firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid, get_now_it().strftime("%d/%m/%Y %H:%M"), f"📅 Appuntamento: {n} il {d}", u['ruolo'], firma_op), True); st.rerun()
    with t_agenda:
        agenda = db_run("SELECT a.id_u, a.data, a.ora, p.nome, a.nota FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.stato='PROGRAMMATO'")
        for aid, adt, ahr, apn, ant in agenda:
            st.markdown(f"<div class='app-card'>📅 {adt} {ahr} - <b>{apn}</b>: {ant}</div>", unsafe_allow_html=True)
            if st.button("FATTO", key=f"app_{aid}"): db_run("UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?", (aid,), True); st.rerun()

elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO ADMIN</h2></div>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["UTENTI", "PAZIENTI", "LOG EVENTI"])
    with tab1:
        for us, un, uc, uq in db_run("SELECT user, nome, cognome, qualifica FROM utenti"):
            c1, c2 = st.columns([0.8, 0.2]); c1.write(f"**{un} {uc}** ({uq})")
            if c2.button("ELIMINA", key=f"d_{us}"): db_run("DELETE FROM utenti WHERE user=?", (us,), True); st.rerun()
    with tab2:
        with st.form("np"):
            np = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
        for pid, pn in db_run("SELECT id, nome FROM pazienti"):
            c1, c2 = st.columns([0.8, 0.2]); c1.write(pn)
            if c2.button("ELIMINA", key=f"dp_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid,), True); st.rerun()
    with tab3:
        st.subheader("Cancellazione Selettiva Log")
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
