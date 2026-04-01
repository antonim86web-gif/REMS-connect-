import sqlite3
import streamlit as st
from datetime import datetime
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.6", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }

    /* TASTO LOGOUT VERDE */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #22c55e !important;
        color: white !important;
        border: 1px solid #16a34a !important;
        font-weight: bold !important;
    }

    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .postit-body { font-size: 1rem; line-height: 1.4; font-weight: 500; }
    
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-admin { background-color: #f1f5f9; border-color: #0f172a; }

    .turno-header { background: #f8fafc; padding: 10px; border-radius: 5px; border-left: 5px solid #1e3a8a; margin: 20px 0 10px 0; font-weight: bold; color: #1e3a8a; }
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2rem; font-weight: 900; color: #166534; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ENGINE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS cassa (p_id INTEGER, data TEXT, causale TEXT, importo REAL, tipo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}"); return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

# Admin di sistema
if not db_run("SELECT * FROM utenti WHERE user='admin'"):
    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("admin"), "Responsabile", "Centro", "Admin"), True)

def render_postits(p_id=None, limit=50, can_delete=False, filter_role=None):
    query = "SELECT data, ruolo, op, nota, id_u FROM eventi WHERE 1=1"
    params = []
    if p_id: query += " AND id=?"; params.append(p_id)
    if filter_role: query += " AND ruolo=?"; params.append(filter_role)
    query += " ORDER BY id_u DESC LIMIT ?"
    params.append(limit)
    res = db_run(query, tuple(params))
    if not res:
        st.info("Nessun record trovato.")
        return
    for d, r, o, nt, uid in res:
        cls = f"role-{r.lower()}"
        col_p, col_d = st.columns([0.92, 0.08])
        col_p.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div class="postit-body">{nt}</div></div>', unsafe_allow_html=True)
        if can_delete:
            if col_d.button("🗑️", key=f"del_ev_{uid}"):
                db_run("DELETE FROM eventi WHERE id_u=?", (uid,), True); st.rerun()

# --- LOGIN & REGISTRAZIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO</h2></div>", unsafe_allow_html=True)
    t_login, t_reg = st.tabs(["🔐 ACCEDI", "📝 REGISTRATI"])
    
    with t_login:
        with st.form("form_login"):
            u_i = st.text_input("Username")
            p_i = st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
                else: st.error("Credenziali errate")
                
    with t_reg:
        with st.form("form_reg"):
            new_u = st.text_input("Username")
            new_p = st.text_input("Password", type="password")
            new_n, new_c = st.text_input("Nome"), st.text_input("Cognome")
            new_q = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                if new_u and new_p and new_n:
                    check_u = db_run("SELECT user FROM utenti WHERE user=?", (new_u,))
                    if check_u: st.error("Username esistente")
                    else:
                        db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (new_u, hash_pw(new_p), new_n, new_c, new_q), True)
                        st.success("Registrazione completata! Ora puoi accedere.")
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR NAV ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
menu = ["📊 Monitoraggio", "👥 Modulo Equipe"]
if u['ruolo'] == "Admin": menu.append("⚙️ Pannello Admin")
nav = st.sidebar.radio("MENU", menu)
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- LOGICA OPERATIVA ---
def logica_equipe(p_id, ruolo_op, firma_op):
    now = datetime.now()
    adesso_str = now.strftime("%d/%m/%Y %H:%M")
    
    # Logica Reset 06:00
    if now.hour < 6: data_rif = (now.replace(hour=0, minute=0) - pd.Timedelta(days=1)).strftime("%d/%m/%Y")
    else: data_rif = now.strftime("%d/%m/%Y")
    rif_full = f"{data_rif} 06:00"

    if ruolo_op == "Psichiatra":
        t1, t2 = st.tabs(["💊 NUOVA PRESCRIZIONE", "🔄 MODIFICA"])
        with t1:
            with st.form("f_p"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"➕ Nuova Terapia: {f} {d}", "Psichiatra", firma_op), True); st.rerun()
        with t2:
            ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            for tid, fr, ds, mv, pv, nv in ter:
                cf, cm, cp, cn, cd = st.columns([3,1,1,1,1])
                cf.write(f"**{fr}**"); nm, np, nn = cm.checkbox("M", value=bool(mv), key=f"m{tid}"), cp.checkbox("P", value=bool(pv), key=f"p{tid}"), cn.checkbox("N", value=bool(nv), key=f"n{tid}")
                if nm != mv or np != pv or nn != nv: db_run("UPDATE terapie SET mat=?, pom=?, nott=? WHERE id_u=?", (int(nm), int(np), int(nn), tid), True); st.rerun()
                if cd.button("🗑️", key=f"dt{tid}"): db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()

    elif ruolo_op == "Infermiere":
        t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONE", "📝 CONSEGNE", "📊 PARAMETRI"])
        with t1:
            terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            for label, db_col in [("MAT", 3), ("POM", 4), ("NOT", 5)]:
                st.markdown(f"<div class='turno-header'>TURNO: {label}</div>", unsafe_allow_html=True)
                f_turno = [t for t in terapie if t[db_col] == 1]
                mostrati = 0
                for f in f_turno:
                    # CORREZIONE TASTO: Controllo se somministrato dopo le 06:00
                    check = db_run("SELECT id_u FROM eventi WHERE id=? AND data >= ? AND nota LIKE ? AND nota LIKE ?", (p_id, rif_full, f"%{label}%", f"%{f[1]}%"))
                    if not check:
                        mostrati += 1
                        col_i, col_b = st.columns([0.7, 0.3])
                        col_i.write(f"**{f[1]}** ({f[2]})")
                        # CHIAVE UNICA PER FORZARE SPARIZIONE
                        if col_b.button("✅ SEGNA ASSUNTA", key=f"chk_{p_id}_{f[0]}_{label}"):
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"TERAPIA {label}: {f[1]} (ASSUNTA)", "Infermiere", firma_op), True)
                            st.rerun()
                if mostrati == 0: st.caption("Terapie completate per questo turno.")
        with t2:
            with st.form("inf_con"):
                cns = st.text_area("Consegne"); (st.form_submit_button("INVIA") and db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"📝 CONSEGNA: {cns}", "Infermiere", firma_op), True) and st.rerun())
        with t3:
            with st.form("inf_par"):
                c1,c2,c3 = st.columns(3); pa, fc, sat = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("Sat%")
                if st.form_submit_button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"📊 PARAMETRI: PA {pa}, FC {fc}, Sat {sat}%", "Infermiere", firma_op), True); st.rerun()

    elif ruolo_op == "Educatore":
        t1, t2 = st.tabs(["💰 GESTIONE CASSA", "📝 CONSEGNE EDUCATIVE"])
        with t1:
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum(m[0] if m[1] == "ENTRATA" else -m[0] for m in mov)
            st.markdown(f"<div class='cassa-card'>Saldo Attuale: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
            with st.form("cs_e"):
                tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("Importo €", min_value=0.0), st.text_input("Causale")
                if st.form_submit_button("REGISTRA MOVIMENTO"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, adesso_str, cau, im, tp, firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"💰 CASSA: {tp} di {im}€ - {cau}", "Educatore", firma_op), True); st.rerun()
        with t2:
            with st.form("ed_con"):
                cns = st.text_area("Nota Educativa")
                if st.form_submit_button("INVIA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"📝 NOTA EDUC.: {cns}", "Educatore", firma_op), True); st.rerun()

    elif ruolo_op == "OSS":
        t1, t2 = st.tabs(["🧹 MANSIONI", "📝 CONSEGNE"])
        with t1:
            with st.form("oss_form"):
                mansioni = ["Pulizia Stanza", "Sale Fumo", "Refettorio", "Sala Caffè", "Cortile", "Lavatrice"]
                checks = [st.checkbox(m) for m in mansioni]
                if st.form_submit_button("REGISTRA MANSIONI"):
                    txt = ", ".join([m for v, m in zip(checks, mansioni) if v])
                    if txt: db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"🧹 MANSIONI: {txt}", "OSS", firma_op), True); st.rerun()
        with t2:
            with st.form("oss_con"):
                cns = st.text_area("Consegne OSS")
                if st.form_submit_button("INVIA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"📝 CONSEGNA OSS: {cns}", "OSS", firma_op), True); st.rerun()

    st.divider()
    st.subheader(f"I Miei Inserimenti ({ruolo_op})")
    render_postits(p_id, limit=8, filter_role=ruolo_op)

# --- NAVIGAZIONE PRINCIPALE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO COMPLETO</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"): render_postits(pid)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>AREA OPERATIVA EQUIPE</h2></div>", unsafe_allow_html=True)
    ruolo_corr, firma_corr = u['ruolo'], firma
    if u['ruolo'] == "Admin":
        ruolo_corr = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
        firma_corr = f"ADMIN as {ruolo_corr}"
    
    paz_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if paz_lista:
        p_sel = st.selectbox("Seleziona Paziente:", [p[1] for p in paz_lista])
        p_id = [p[0] for p in paz_lista if p[1] == p_sel][0]
        logica_equipe(p_id, ruolo_corr, firma_corr)

elif nav == "⚙️ Pannello Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO DI CONTROLLO</h2></div>", unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["👥 UTENTI", "🏥 PAZIENTI", "🗑️ LOG"])
    with t1:
        u_list = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        for us, no, co, qu in u_list:
            c1, c2, c3 = st.columns([3, 3, 1])
            c1.write(f"**{no} {co}** ({us})"); c2.write(f"Ruolo: *{qu}*")
            if us != 'admin' and c3.button("Elimina", key=f"du_{us}"): db_run("DELETE FROM utenti WHERE user=?", (us,), True); st.rerun()
    with t2:
        with st.form("add_p"):
            np = st.text_input("Nome e Cognome Paziente")
            if st.form_submit_button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
        p_all = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        for pid, nome in p_all:
            c1, c2 = st.columns([6, 1]); c1.write(nome)
            if c2.button("Elimina", key=f"dp_{pid}"): db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
    with t3:
        p_all = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_all:
            p_sel_log = st.selectbox("Paziente:", [p[1] for p in p_all], key="admin_log")
            pid_log = [p[0] for p in p_all if p[1] == p_sel_log][0]
            render_postits(p_id=pid_log, limit=100, can_delete=True)
