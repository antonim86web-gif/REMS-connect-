import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- DATABASE ENGINE & SCHEMA UPDATE ---
DB_NAME = "rems_final_v12.db"

def aggiorna_struttura_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Tabelle base
        c.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato TEXT DEFAULT 'ATTIVO')")
        c.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, figura_professionale TEXT, esito TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, mat_nuovo INTEGER DEFAULT 0, pom_nuovo INTEGER DEFAULT 0, al_bisogno INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        c.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))")
        c.execute("CREATE TABLE IF NOT EXISTS logs_sistema (id_log INTEGER PRIMARY KEY AUTOINCREMENT, data_ora TEXT, utente TEXT, azione TEXT, dettaglio TEXT)")
        
        # Inserimento Admin Default
        if c.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
            c.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hashlib.sha256(str.encode("perito2026")).hexdigest(), "SUPER", "USER", "Admin"))
        
        # Inserimento Stanze Default
        if c.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
            for i in range(1, 7): c.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
            for i in range(1, 11): c.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
        conn.commit()

aggiorna_struttura_db()

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if st.session_state.user_session else "SISTEMA"
    db_run("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
           (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio), True)

# --- CSS INTEGRALE (NON SEMPLIFICATO) ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.2", layout="wide", page_icon="🏥")
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .sidebar-footer { color: #ffffff !important; font-size: 0.8rem; text-align: center; margin-top: 20px; opacity: 0.8; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    
    .alert-sidebar { background: #ef4444; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: 800; margin: 10px 5px; border: 2px solid white; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.02);} 100% {transform: scale(1);} }

    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .cal-table th { background: #f1f5f9; padding: 10px; color: #1e3a8a; font-weight: 800; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .cal-table td { border: 1px solid #e2e8f0; vertical-align: top; height: 150px; padding: 5px; position: relative; }
    
    .scroll-giorni { display: flex; overflow-x: auto; gap: 4px; padding: 8px; background: #fdfdfd; }
    .quadratino { 
        min-width: 48px; height: 58px; border-radius: 4px; border: 1px solid #eee; 
        display: flex; flex-direction: column; align-items: center; justify-content: center; flex-shrink: 0;
    }
    .q-oggi { border: 2px solid #1e3a8a !important; background: #fffde7; }
    .q-num { font-size: 8px; color: #999; font-weight: bold; }
    .q-esito { font-size: 14px; font-weight: 900; }
    .q-op { font-size: 7px; color: #444; text-align: center; line-height: 1; margin-top: 2px; text-transform: uppercase; }

    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-psicologo { background-color: #faf5ff; border-color: #a855f7; }
    .role-sociale { background-color: #fff7ed; border-color: #f97316; }
    .role-opsi { background-color: #f1f5f9; border-color: #0f172a; border-style: dashed; }

    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
    
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .reparto-title { text-align: center; color: #1e3a8a; font-weight: 900; text-transform: uppercase; margin-bottom: 15px; border-bottom: 2px solid #1e3a8a33; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; }
    .stanza-header { font-weight: 800; font-size: 0.8rem; color: #475569; margin-bottom: 5px; border-bottom: 1px solid #eee; }
    .stanza-occupata { border-left-color: #22c55e; background-color: #f0fdf4; }
    .stanza-piena { border-left-color: #2563eb; background-color: #eff6ff; }
    .stanza-isolamento { border-left-color: #ef4444; background-color: #fef2f2; border-width: 2px; }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONI RENDERING ---
def render_postits(p_id, limit=50):
    ruoli_disp = ["Tutti", "Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"]
    scelta_ruolo = st.multiselect("Filtra Figura", ruoli_disp, default="Tutti", key=f"filt_{p_id}")
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
    params = [p_id]
    if "Tutti" not in scelta_ruolo and scelta_ruolo:
        query += f" AND ruolo IN ({','.join(['?']*len(scelta_ruolo))})"
        params.extend(scelta_ruolo)
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    for d, r, o, nt in res:
        role_map = {"Psichiatra":"psichiatra", "Infermiere":"infermiere", "Educatore":"educatore", "OSS":"oss", "Psicologo":"psicologo", "Assistente Sociale":"sociale", "OPSI":"opsi"}
        cls = f"role-{role_map.get(r, 'oss')}"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o}</span><span>📅 {d}</span></div><div>{nt}</div></div>', unsafe_allow_html=True)

# --- GESTIONE SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - LOGIN</h2></div>", unsafe_allow_html=True)
    c_l, c_r = st.columns(2)
    with c_l:
        with st.form("login"):
            u_i = st.text_input("Username").lower().strip()
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hashlib.sha256(str.encode(p_i)).hexdigest()))
                if res:
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": u_i}
                    scrivi_log("LOGIN", "Accesso")
                    st.rerun()
    with c_r:
        with st.form("reg"):
            ru, rp, rn, rc = st.text_input("User"), st.text_input("Pass", type="password"), st.text_input("Nome"), st.text_input("Cognome")
            rq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (ru.lower(), hashlib.sha256(str.encode(rp)).hexdigest(), rn, rc, rq), True)
                st.success("Registrato!")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi_iso = get_now_it().strftime("%Y-%m-%d")

# --- SIDEBAR ---
st.sidebar.markdown(f"<div class='sidebar-title'>REMS-CONNECT</div><div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto", "⚙️ Admin"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()
st.sidebar.markdown("<br><div class='sidebar-footer'>Antony ver. 28.9 Elite</div>", unsafe_allow_html=True)

# --- 🗺️ MODULO MAPPA ---
if nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>TABELLONE POSTI LETTO</h2></div>", unsafe_allow_html=True)
    stanze_db = db_run("SELECT id, reparto, tipo FROM stanze ORDER BY id")
    paz_db = db_run("SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p LEFT JOIN assegnazioni a ON p.id = a.p_id WHERE p.stato='ATTIVO'")
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
        p_list = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
        sel_p = st.selectbox("Paziente", [p[1] for p in p_list], index=None)
        if sel_p:
            pid_sel = [p[0] for p in p_list if p[1]==sel_p][0]
            posti_liberi = [f"{sid}-L{l}" for sid, si in mappa.items() for l, po in si['letti'].items() if not po]
            dest = st.selectbox("Destinazione", posti_liberi)
            mot = st.text_input("Motivo")
            if st.button("ESEGUI") and mot:
                dsid, dl = dest.split("-L")
                db_run("DELETE FROM assegnazioni WHERE p_id=?", (pid_sel,), True)
                db_run("INSERT INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)", (pid_sel, dsid, int(dl), oggi_iso), True)
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (pid_sel, get_now_it().strftime("%d/%m/%Y %H:%M"), f"🔄 SPOSTATO in {dsid}-L{dl}: {mot}", u['ruolo'], firma_op), True)
                st.rerun()

# --- 📊 MONITORAGGIO ---
elif nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO COMPLETO</h2></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"):
        with st.expander(f"📁 SCHEDA: {nome}"): render_postits(pid)

# --- 👥 MODULO EQUIPE ---
elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO PROFESSIONALE</h2></div>", unsafe_allow_html=True)
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": ruolo_corr = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = get_now_it()

        if ruolo_corr == "Psichiatra":
            t1, t2, t3 = st.tabs(["➕ Nuova Terapia", "📝 Gestione Terapie", "🩺 Consegne Mediche"])
            with t1:
                with st.form("f_t"):
                    f, d, fa = st.text_input("Farmaco"), st.text_input("Dose"), st.selectbox("Orario", ["8:13 (Mattina)", "16:20 (Pomeriggio)", "Al bisogno"])
                    if st.form_submit_button("REGISTRA"):
                        m, p, b = (1,0,0) if "8:13" in fa else ((0,1,0) if "16:20" in fa else (0,0,1))
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, m, p, b, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"➕ Prescritto: {f} {d} ({fa})", "Psichiatra", firma_op), True)
                        st.rerun()
            with t2:
                for tid, fn, ds, m, p, b in db_run("SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?", (p_id,)):
                    with st.expander(f"Modifica {fn} {ds}"):
                        with st.form(f"mod_{tid}"):
                            nf, nd = st.text_input("Farmaco", fn), st.text_input("Dose", ds)
                            if st.form_submit_button("AGGIORNA"):
                                db_run("UPDATE terapie SET farmaco=?, dose=? WHERE id_u=?", (nf, nd, tid), True)
                                st.rerun()
                            if st.form_submit_button("SOSPENDE"):
                                db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🚫 SOSPESO: {fn}", "Psichiatra", firma_op), True)
                                st.rerun()
            with t3:
                with st.form("f_m"):
                    nt = st.text_area("Nota Clinica")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🩺 MED: {nt}", "Psichiatra", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 Smarcatura", "💓 Parametri", "📝 Consegne"])
            with t1:
                turno = st.selectbox("Turno", ["8:13", "16:20", "Bisogno"])
                col = "mat_nuovo" if "8:13" in turno else ("pom_nuovo" if "16:20" in turno else "al_bisogno")
                ters = db_run(f"SELECT id_u, farmaco, dose FROM terapie WHERE p_id=? AND {col}=1", (p_id,))
                for tid, fn, ds in ters:
                    st.write(f"**{fn}** ({ds})")
                    firme = db_run("SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND nota LIKE ? AND data LIKE ?", 
                                   (p_id, f"%{fn}%", f"%({turno})%", f"%/{now.strftime('%m/%Y')}%"))
                    f_map = {int(d[0].split("/")[0]): {"e": d[1], "o": d[2].split(" ")[0]} for d in firme if d[0]}
                    h = "<div class='scroll-giorni'>"
                    for d in range(1, calendar.monthrange(now.year, now.month)[1] + 1):
                        info = f_map.get(d)
                        cl = "quadratino q-oggi" if d == now.day else "quadratino"
                        es, col_t, bg = (info['e'], "green", "#dcfce7") if info and info['e']=='A' else (("-", "#888", "white") if not info else ("R", "red", "#fee2e2"))
                        f_op = info['o'] if info else ""
                        h += f"<div class='{cl}' style='background:{bg}; color:{col_t};'><div class='q-num'>{d}</div><div class='q-esito'>{es}</div><div class='q-op'>{f_op}</div></div>"
                    st.markdown(h + "</div>", unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    if c1.button("✅ ASSUNTO", key=f"A_{tid}_{turno}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"✔️ {fn} ({turno})", "Infermiere", firma_op, "A"), True)
                        st.rerun()
                    if c2.button("❌ RIFIUTA", key=f"R_{tid}_{turno}"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"❌ RIFIUTO {fn} ({turno})", "Infermiere", firma_op, "R"), True)
                        st.rerun()
            with t2:
                with st.form("f_p"):
                    pa, fc, sa, tc = st.text_input("PA"), st.text_input("FC"), st.text_input("Sat"), st.text_input("TC")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💓 PA:{pa} FC:{fc} Sa:{sa} TC:{tc}", "Infermiere", firma_op), True)
                        st.rerun()
            with t3:
                with st.form("f_ni"):
                    nt = st.text_area("Consegna Infermieristica")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), nt, "Infermiere", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 Cassa", "📝 Consegna"])
            with t1:
                movs = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in movs)
                st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("f_c"):
                    tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€", min_value=0.0), st.text_input("Causale")
                    if st.form_submit_button("ESEGUI"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi_iso, cau, im, tp, firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True)
                        st.rerun()
            with t2:
                with st.form("f_ed"):
                    nt = st.text_area("Consegna Educativa")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📝 {nt}", "Educatore", firma_op), True)
                        st.rerun()

        elif ruolo_corr == "Psicologo":
            with st.form("f_psi"):
                tt, nt = st.text_input("Titolo/Test"), st.text_area("Note Colloquio")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧠 {tt}: {nt}", "Psicologo", firma_op), True)
                    st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("f_oss"):
                mans = st.multiselect("Mansioni", ["Igiene", "Cambio", "Pasto", "Mobilizzazione"])
                nt = st.text_input("Note")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"🧹 {', '.join(mans)} | {nt}", "OSS", firma_op), True)
                    st.rerun()

        st.divider(); render_postits(p_id)

# --- 📅 AGENDA ---
elif nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA</h2></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        m, y = st.session_state.cal_month, st.session_state.cal_year
        cal_html = f"<table class='cal-table'><thead><tr><th>L</th><th>M</th><th>M</th><th>G</th><th>V</th><th>S</th><th>D</th></tr></thead><tbody>"
        for week in calendar.Calendar(0).monthdayscalendar(y, m):
            cal_html += "<tr>"
            for d in week:
                if d == 0: cal_html += "<td style='background:#f1f5f9;'></td>"
                else:
                    cl = "today-html" if f"{y}-{m:02d}-{d:02d}" == oggi_iso else ""
                    cal_html += f"<td class='{cl}'><b>{d}</b></td>"
            cal_html += "</tr>"
        st.markdown(cal_html + "</tbody></table>", unsafe_allow_html=True)
    with c2:
        with st.form("app"):
            p_l = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'")
            p_s = st.selectbox("Paziente", [p[1] for p in p_l])
            dt, orr, nt = st.date_input("Data"), st.time_input("Ora"), st.text_input("Nota")
            if st.form_submit_button("AGGIUNGI"):
                pid = [p[0] for p in p_l if p[1]==p_s][0]
                db_run("INSERT INTO appuntamenti (p_id, data, ora, nota, stato) VALUES (?,?,?,?,'PROGRAMMATO')", (pid, str(dt), str(orr)[:5], nt), True)
                st.rerun()

# --- ⚙️ ADMIN ---
elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO DI CONTROLLO</h2></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Utenti", "Pazienti", "Logs"])
    with t1:
        uts = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        for us, no, co, qu in uts:
            st.write(f"**{no} {co}** ({qu})")
            if us != 'admin' and st.button(f"Elimina {us}", key=f"del_{us}"):
                db_run("DELETE FROM utenti WHERE user=?", (us,), True); st.rerun()
    with t2:
        with st.form("new_p"):
            np = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"):
                db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
        for pid, pno in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO'"):
            if st.button(f"Dimetti {pno}", key=f"dim_{pid}"):
                db_run("UPDATE pazienti SET stato='DIMESSO' WHERE id=?", (pid,), True); st.rerun()
    with t3:
        logs = db_run("SELECT * FROM logs_sistema ORDER BY id_log DESC LIMIT 50")
        st.table(pd.DataFrame(logs, columns=["ID", "Data", "User", "Azione", "Dettaglio"]))
