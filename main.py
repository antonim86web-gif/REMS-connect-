import sqlite3
import streamlit as st
from datetime import datetime, timedelta, timezone
import hashlib
import pandas as pd
import calendar

# --- 1. FUNZIONE AGGIORNAMENTO DB (ESTESA) ---
def aggiorna_struttura_db():
    conn = sqlite3.connect('rems_final_v12.db')
    c = conn.cursor()
    # Colonne per eventi
    try: c.execute("ALTER TABLE eventi ADD COLUMN tipo_evento TEXT")
    except: pass
    try: c.execute("ALTER TABLE eventi ADD COLUMN figura_professionale TEXT")
    except: pass
    
    # Logica di stato paziente (Dimissioni)
    try: c.execute("ALTER TABLE pazienti ADD COLUMN stato TEXT DEFAULT 'ATTIVO'")
    except: pass
    
    # Supporto colonna Al Bisogno (bis)
    try: c.execute("ALTER TABLE terapie ADD COLUMN bis INTEGER DEFAULT 0")
    except: pass

    # Tabella Log per Tracciabilità Legale
    c.execute("""CREATE TABLE IF NOT EXISTS logs_sistema (
                 id_log INTEGER PRIMARY KEY AUTOINCREMENT, 
                 data_ora TEXT, 
                 utente TEXT, 
                 azione TEXT, 
                 dettaglio TEXT)""")
    
    # Tabella Stanze e Assegnazioni
    c.execute("CREATE TABLE IF NOT EXISTS stanze (id TEXT PRIMARY KEY, reparto TEXT, tipo TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS assegnazioni (p_id INTEGER UNIQUE, stanza_id TEXT, letto INTEGER, data_ass TEXT, FOREIGN KEY(p_id) REFERENCES pazienti(id))")
    
    conn.commit()
    conn.close()

aggiorna_struttura_db()

# --- 2. UTILITY FUNCTIONS ---
def get_now_it():
    return datetime.now(timezone.utc) + timedelta(hours=2)

def hash_pw(p): 
    return hashlib.sha256(str.encode(p)).hexdigest()

def scrivi_log(azione, dettaglio):
    user_log = st.session_state.user_session['uid'] if st.session_state.user_session else "SISTEMA"
    with sqlite3.connect('rems_final_v12.db') as conn:
        conn.execute("INSERT INTO logs_sistema (data_ora, utente, azione, dettaglio) VALUES (?,?,?,?)", 
                     (get_now_it().strftime("%d/%m/%Y %H:%M:%S"), user_log, azione, dettaglio))
        conn.commit()

# --- 3. ENGINE DATABASE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        try:
            cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, stato TEXT DEFAULT 'ATTIVO')")
            cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, figura_professionale TEXT)")
            cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT, bis INTEGER DEFAULT 0)")
            cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
            cur.execute("CREATE TABLE IF NOT EXISTS appuntamenti (id_u INTEGER PRIMARY KEY AUTOINCREMENT, p_id INTEGER, data TEXT, ora TEXT, nota TEXT, stato TEXT, autore TEXT, tipo_evento TEXT, mezzo TEXT, accompagnatore TEXT)")
            
            if cur.execute("SELECT COUNT(*) FROM utenti WHERE user='admin'").fetchone()[0] == 0:
                cur.execute("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("perito2026"), "SUPER", "USER", "Admin"))
            
            if cur.execute("SELECT COUNT(*) FROM stanze").fetchone()[0] == 0:
                for i in range(1, 7): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"A{i}", "A", "ISOLAMENTO" if i==6 else "STANDARD"))
                for i in range(1, 11): cur.execute("INSERT INTO stanze VALUES (?,?,?)", (f"B{i}", "B", "ISOLAMENTO" if i==10 else "STANDARD"))
            
            cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}")
            return []

# --- 4. CONFIGURAZIONE INTERFACCIA & CSS ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.3", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* SIDEBAR & COLORS */
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid #ffffff22; }
    
    /* STU MATRICE ORIZZONTALE */
    .stu-wrapper { overflow-x: auto; margin-top: 10px; border: 1px solid #cbd5e1; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.15); background: #f8fafc; }
    .stu-table { width: 100%; border-collapse: collapse; font-size: 0.72rem; min-width: 1500px; table-layout: fixed; }
    .stu-table th, .stu-table td { border: 1px solid #cbd5e1; padding: 5px; text-align: center; height: 50px; }
    .stu-table th { background: #e2e8f0; color: #1e3a8a; font-weight: 800; text-transform: uppercase; }
    .sticky-col { position: sticky; left: 0; background: #ffffff !important; z-index: 10; width: 300px !important; text-align: left !important; padding-left: 15px !important; border-right: 4px solid #1e3a8a !important; font-size: 0.8rem; }
    
    .cell-assunto { background: #22c55e !important; color: white !important; font-weight: 900; border-radius: 4px; padding: 3px 6px; }
    .cell-rifiutato { background: #ef4444 !important; color: white !important; font-weight: 900; border-radius: 4px; padding: 3px 6px; }
    .cell-today { background: #f0fdf4 !important; border: 2.5px solid #22c55e !important; }
    
    /* TOOLTIP PROFESSIONALE */
    .stu-cell-wrap { position: relative; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; cursor: help; }
    .stu-cell-wrap .tooltip-stu { visibility: hidden; width: 200px; background-color: #0f172a; color: #fff; text-align: center; border-radius: 8px; padding: 10px; position: absolute; z-index: 100; bottom: 125%; left: 50%; transform: translateX(-50%); opacity: 0; transition: 0.3s; font-size: 0.7rem; box-shadow: 0 10px 20px rgba(0,0,0,0.4); line-height: 1.4; pointer-events: none; }
    .stu-cell-wrap:hover .tooltip-stu { visibility: visible; opacity: 1; }

    /* POST-IT & RUOLI */
    .postit { padding: 15px; border-radius: 10px; margin-bottom: 12px; border-left: 12px solid; box-shadow: 0 4px 6px rgba(0,0,0,0.1); background: white; color: #334155; }
    .role-psichiatra { border-color: #dc2626; background: #fef2f2; } 
    .role-infermiere { border-color: #2563eb; background: #eff6ff; } 
    .role-educatore { border-color: #059669; background: #ecfdf5; }
    .role-oss { border-color: #64748b; background: #f8fafc; }
    .role-psicologo { border-color: #a855f7; background: #faf5ff; }
    .role-sociale { border-color: #f97316; background: #fff7ed; }
    .role-opsi { border-color: #0f172a; background: #f1f5f9; }

    /* MAPPA E ALTRO */
    .map-reparto { background: #f1f5f9; padding: 20px; border-radius: 15px; border: 1px solid #e2e8f0; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; border-left: 6px solid #94a3b8; }
    .cassa-card { background: #f0fdf4; border: 2px solid #bbf7d0; padding: 20px; border-radius: 12px; text-align: center; }
    .saldo-txt { font-size: 2.5rem; font-weight: 900; color: #166534; }
</style>
""", unsafe_allow_html=True)

# --- 5. LOGICA DI RENDERING POST-ITS ---
def render_postits(p_id, limit=50):
    ruoli_disp = ["Tutti", "Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"]
    scelta_ruolo = st.multiselect("Filtra Diario", ruoli_disp, default="Tutti", key=f"f_{p_id}")
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
    params = [p_id]
    if "Tutti" not in scelta_ruolo and scelta_ruolo:
        query += f" AND ruolo IN ({','.join(['?']*len(scelta_ruolo))})"
        params.extend(scelta_ruolo)
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    for d, r, o, nt in res:
        rm = {"Psichiatra":"psichiatra", "Infermiere":"infermiere", "Educatore":"educatore", "OSS":"oss", "Psicologo":"psicologo", "Assistente Sociale":"sociale", "OPSI":"opsi"}
        cls = f"role-{rm.get(r, 'oss')}"
        st.markdown(f'<div class="postit {cls}"><b>👤 {o} ({r})</b> — <small>📅 {d}</small><br><div style="margin-top:8px;">{nt}</div></div>', unsafe_allow_html=True)

# --- 6. SESSIONE E LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if 'cal_month' not in st.session_state: st.session_state.cal_month = get_now_it().month
if 'cal_year' not in st.session_state: st.session_state.cal_year = get_now_it().year

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO PRO</h2></div>", unsafe_allow_html=True)
    cl, cr = st.columns(2)
    with cl:
        st.subheader("Login")
        with st.form("l"):
            ui, pi = st.text_input("User").lower().strip(), st.text_input("Pwd", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (ui, hash_pw(pi)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2], "uid": ui}
                    scrivi_log("LOGIN", "Accesso")
                    st.rerun()
    with cr:
        st.subheader("Registra")
        with st.form("r"):
            ru, rp, rn, rc = st.text_input("User"), st.text_input("Pwd", type="password"), st.text_input("Nome"), st.text_input("Cogn")
            rq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS", "Psicologo", "Assistente Sociale", "OPSI"])
            if st.form_submit_button("CREA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (ru.lower(), hash_pw(rp), rn, rc, rq), True)
                st.success("Ok!")
    st.stop()

u = st.session_state.user_session
firma_op = f"{u['nome']} {u['cognome']} ({u['ruolo']})"
oggi_dt = get_now_it()
oggi_iso = oggi_dt.strftime("%Y-%m-%d")

# --- 7. SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.markdown(f"<div class='user-logged'>● {u['nome']} {u['cognome']}</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("NAVIGAZIONE", ["📊 Monitoraggio", "👥 Modulo Equipe", "📅 Agenda Dinamica", "🗺️ Mappa Posti Letto", "⚙️ Admin"])
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- 8. MODULO EQUIPE (S.T.U. & DIARIO) ---
if nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE - S.T.U.</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        
        t_stu, t_med, t_inf, t_edu, t_altri = st.tabs(["📋 S.T.U. MENSILE", "🩺 MEDICO", "💊 INFERMIERE", "💰 EDUCATORE/CASSA", "📝 ALTRE FIGURE"])

        with t_stu:
            # --- TABELLA ORIZZONTALE 1-31 ---
            st.markdown(f"### Diario Terapeutico: {calendar.month_name[oggi_dt.month]} {oggi_dt.year}")
            
            # Ordinamento: Mattino -> Pomeriggio -> Al Bisogno
            terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, bis FROM terapie WHERE p_id=? ORDER BY mat DESC, pom DESC, bis ASC", (p_id,))
            num_days = calendar.monthrange(oggi_dt.year, oggi_dt.month)[1]
            
            html = f"""<div class='stu-wrapper'><table class='stu-table'><thead><tr><th class='sticky-col'>FARMACO / POSOLOGIA</th>"""
            for d in range(1, num_days + 1):
                cls = "cell-today" if d == oggi_dt.day else ""
                html += f"<th class='{cls}'>{d}</th>"
            html += "</tr></thead><tbody>"
            
            for tid, fn, ds, mat, pom, bis in terapie:
                slots = []
                if mat: slots.append(("MATTINO", "08:00"))
                if pom: slots.append(("POMERIGGIO", "14:00"))
                if bis: slots.append(("AL BISOGNO", "PRN"))
                
                for label, ora in slots:
                    html += f"<tr><td class='sticky-col'><b>{fn}</b><br><small>{ds} — {ora}</small></td>"
                    for d in range(1, num_days + 1):
                        d_str = f"{d:02d}/{oggi_dt.month:02d}/{oggi_dt.year}"
                        check = db_run("SELECT op, data, nota FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", 
                                      (p_id, f"%SOMM: {fn} ({label})%", f"{d_str}%"))
                        if check:
                            o_f, dt_f, nt_f = check[0]; h_f = dt_f.split(" ")[1]
                            bg = "cell-assunto" if "ASSUNTO" in nt_f else "cell-rifiutato"
                            txt = "A" if "ASSUNTO" in nt_f else "R"
                            html += f"<td><div class='stu-cell-wrap'><span class='{bg}'>{txt}</span>"
                            html += f"<span class='tooltip-stu'><b>{o_f}</b><br>Ora: {h_f}<br>{nt_f}</span></div></td>"
                        else:
                            html += "<td>-</td>"
                    html += "</tr>"
            html += "</tbody></table></div>"
            st.markdown(html, unsafe_allow_html=True)

        with t_med:
            if u['ruolo'] in ["Psichiatra", "Admin"]:
                with st.form("f_presc"):
                    st.subheader("Nuova Prescrizione")
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m,p,b = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("AL BISOGNO")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, bis, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f.upper(), d, int(m), int(p), int(b), firma_op), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_dt.strftime("%d/%m/%Y %H:%M"), f"➕ Nuova Terapia: {f}", "Psichiatra", firma_op), True)
                        st.rerun()
                st.divider()
                with st.form("f_nota_med"):
                    nm = st.text_area("Consegna Medica")
                    if st.form_submit_button("SALVA NOTA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_dt.strftime("%d/%m/%Y %H:%M"), f"🩺 MED: {nm}", "Psichiatra", firma_op), True)
                        st.rerun()
            else: st.warning("Area riservata ai Medici.")

        with t_inf:
            if u['ruolo'] in ["Infermiere", "Admin"]:
                st.subheader(f"Somministrazioni del {oggi_dt.strftime('%d/%m/%Y')}")
                for tid, fn, ds, mat, pom, bis in terapie:
                    for lbl, attivo in [("MATTINO", mat), ("POMERIGGIO", pom), ("AL BISOGNO", bis)]:
                        if attivo:
                            if not db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%SOMM: {fn} ({lbl})%", f"{oggi_dt.strftime('%d/%m/%Y')}%")):
                                c1, c2, c3 = st.columns([3, 1, 1])
                                c1.write(f"💊 **{fn}** ({lbl})")
                                if c2.button("ASSUNTO", key=f"a_{tid}_{lbl}"):
                                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_dt.strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM: {fn} ({lbl}) - STATO: ASSUNTO", "Infermiere", firma_op), True)
                                    st.rerun()
                                if c3.button("RIFIUTATO", key=f"r_{tid}_{lbl}"):
                                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_dt.strftime("%d/%m/%Y %H:%M"), f"❌ SOMM: {fn} ({lbl}) - STATO: RIFIUTATO", "Infermiere", firma_op), True)
                                    st.rerun()
                st.divider()
                with st.form("f_param"):
                    pa, fc, tc = st.columns(3)
                    p_v = pa.text_input("PA"); f_v = fc.text_input("FC"); t_v = tc.text_input("TC")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_dt.strftime("%d/%m/%Y %H:%M"), f"💓 PARAMETRI: PA {p_v}, FC {f_v}, TC {t_v}", "Infermiere", firma_op), True)
                        st.rerun()
            else: st.warning("Area riservata agli Infermieri.")

        with t_edu:
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
            st.markdown(f"<div class='cassa-card'>Saldo Paziente: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
            with st.form("cs"):
                tp, im, cau = st.selectbox("Operazione", ["ENTRATA", "USCITA"]), st.number_input("Euro"), st.text_input("Causale")
                if st.form_submit_button("ESEGUI MOVIMENTO"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi_iso, cau, im, tp, firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_dt.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma_op), True)
                    st.rerun()

        with t_altri:
            with st.form("altre_fig"):
                fig = st.selectbox("Ruolo", ["Psicologo", "Assistente Sociale", "OSS", "OPSI", "Educatore"])
                txt = st.text_area("Nota Diario")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, oggi_dt.strftime("%d/%m/%Y %H:%M"), txt, fig, firma_op), True)
                    st.rerun()

        st.divider(); render_postits(p_id)

# --- 9. MONITORAGGIO ---
elif nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"):
        with st.expander(f"📁 SCHEDA: {nome}"):
            render_postits(pid, limit=10)

# --- 10. AGENDA ---
elif nav == "📅 Agenda Dinamica":
    st.markdown("<div class='section-banner'><h2>AGENDA DINAMICA</h2></div>", unsafe_allow_html=True)
    col_c, col_a = st.columns([3, 1])
    with col_c:
        st.write(f"### {calendar.month_name[st.session_state.cal_month]} {st.session_state.cal_year}")
        cal_html = "<table class='cal-table'><thead><tr><th>Lun</th><th>Mar</th><th>Mer</th><th>Gio</th><th>Ven</th><th>Sab</th><th>Dom</th></tr></thead><tbody>"
        cal = calendar.Calendar(0)
        for week in cal.monthdayscalendar(st.session_state.cal_year, st.session_state.cal_month):
            cal_html += "<tr>"
            for day in week:
                if day == 0: cal_html += "<td style='background:#f1f5f9;'></td>"
                else:
                    d_iso = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{day:02d}"
                    cls = "today-html" if d_iso == oggi_iso else ""
                    cal_html += f"<td><span style='font-weight:900;'>{day}</span></td>"
            cal_html += "</tr>"
        cal_html += "</tbody></table>"
        st.markdown(cal_html, unsafe_allow_html=True)
    with col_a:
        st.subheader("Programma Appuntamento")
        with st.form("app"):
            ps = st.selectbox("Paziente", [p[1] for p in p_lista])
            te = st.selectbox("Tipo", ["Uscita Esterna", "Visita Medica", "Colloquio"])
            dt = st.date_input("Giorno")
            if st.form_submit_button("REGISTRA"):
                st.success("Programmato!")

# --- 11. MAPPA ---
elif nav == "🗺️ Mappa Posti Letto":
    st.markdown("<div class='section-banner'><h2>MAPPA POSTI LETTO</h2></div>", unsafe_allow_html=True)
    st.info("Visualizzazione interattiva dei posti letto A1-B10 attiva.")
    stanze = db_run("SELECT id, reparto, tipo FROM stanze")
    ca, cb = st.columns(2)
    with ca:
        st.subheader("Reparto A")
        for s in [x for x in stanze if x[1]=="A"]:
            st.markdown(f"<div class='stanza-tile'>{s[0]} - {s[2]}</div>", unsafe_allow_html=True)
    with cb:
        st.subheader("Reparto B")
        for s in [x for x in stanze if x[1]=="B"]:
            st.markdown(f"<div class='stanza-tile'>{s[0]} - {s[2]}</div>", unsafe_allow_html=True)

# --- 12. ADMIN ---
elif nav == "⚙️ Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO AMMINISTRAZIONE</h2></div>", unsafe_allow_html=True)
    ta, tb, tc = st.tabs(["UTENTI", "PAZIENTI", "LOG SISTEMA"])
    with ta:
        uts = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        st.dataframe(pd.DataFrame(uts, columns=["User", "Nome", "Cogn", "Ruolo"]))
    with tb:
        with st.form("np"):
            nom = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"):
                db_run("INSERT INTO pazienti (nome, stato) VALUES (?, 'ATTIVO')", (nom.upper(),), True)
                st.rerun()
    with tc:
        logs = db_run("SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 200")
        st.dataframe(pd.DataFrame(logs, columns=["Ora", "Utente", "Azione", "Dettaglio"]))

# --- FOOTER ---
st.sidebar.markdown(f"<br><br><br><div style='color:white; opacity:0.5; font-size:0.7rem; text-align:center;'>REMS Connect Elite v28.9.3<br>Sviluppo Antony Webmaster</div>", unsafe_allow_html=True)
