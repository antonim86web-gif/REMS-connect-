import sqlite3
import hashlib
import pandas as pd
import streamlit as st
from datetime import datetime

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

# --- STILE CSS PERSONALIZZATO ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }

    /* --- TASTI ROSSI (LOGOUT E FRECCE) --- */
    .stButton > button { width: 100%; border-radius: 8px; font-weight: 800; }
    .btn-red > div > button {
        background-color: #dc2626 !important;
        color: white !important;
        border: 2px solid #b91c1c !important;
        text-transform: uppercase;
    }
    .btn-red > div > button:hover {
        background-color: #b91c1c !important;
        border-color: #991b1b !important;
    }

    /* --- POST-IT --- */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .postit-body { font-size: 1rem; line-height: 1.4; font-weight: 500; }
    
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-admin { background-color: #f1f5f9; border-color: #0f172a; }

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

# Admin default
if not db_run("SELECT * FROM utenti WHERE user='admin'"):
    db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", ("admin", hash_pw("admin"), "Responsabile", "Centro", "Admin"), True)

def render_postits(p_id=None, limit=50, can_delete=False):
    query = "SELECT data, ruolo, op, nota, id_u FROM eventi"
    params = []
    if p_id: query += " WHERE id=?"; params.append(p_id)
    query += " ORDER BY id_u DESC LIMIT ?"
    res = db_run(query, tuple(params + [limit]))
    if not res: st.info("Nessun dato registrato."); return
    for d, r, o, nt, uid in res:
        cls = f"role-{r.lower()}"
        col_p, col_d = st.columns([0.93, 0.07])
        col_p.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div class="postit-body">{nt}</div></div>', unsafe_allow_html=True)
        if can_delete:
            if col_d.button("🗑️", key=f"del_ev_{uid}"):
                db_run("DELETE FROM eventi WHERE id_u=?", (uid,), True); st.rerun()

# --- LOGIN / REGISTRAZIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO</h2></div>", unsafe_allow_html=True)
    t_log, t_reg = st.tabs(["🔐 ACCEDI", "📝 REGISTRATI"])
    with t_log:
        with st.form("login"):
            u_i, p_i = st.text_input("User"), st.text_input("Password", type="password")
            if st.form_submit_button("ENTRA"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
                else: st.error("Accesso negato.")
    with t_reg:
        with st.form("reg"):
            nu, np = st.text_input("Username"), st.text_input("Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Ruolo", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True); st.success("Fatto! Accedi ora."); st.rerun()
    st.stop()

# --- TOP NAVIGATION (FRECCE E LOGOUT) ---
u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

col_f1, col_f2, col_spacer, col_logo = st.columns([0.1, 0.1, 0.6, 0.2])
with col_f1:
    st.markdown('<div class="btn-red">', unsafe_allow_html=True)
    if st.button("⬅️"): pass
    st.markdown('</div>', unsafe_allow_html=True)
with col_f2:
    st.markdown('<div class="btn-red">', unsafe_allow_html=True)
    if st.button("➡️"): pass
    st.markdown('</div>', unsafe_allow_html=True)
with col_logo:
    st.markdown('<div class="btn-red">', unsafe_allow_html=True)
    if st.button("LOGOUT"): st.session_state.user_session = None; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
menu = ["📊 Monitoraggio", "👥 Modulo Equipe"]
if u['ruolo'] == "Admin": menu.append("⚙️ Pannello Admin")
else: menu.append("⚙️ Sistema")
nav = st.sidebar.radio("NAVIGAZIONE", menu)

# --- LOGICA OPERATIVA ---
def logica_equipe(p_id, ruolo_op, firma_op):
    adesso = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    if ruolo_op == "Psichiatra":
        t1, t2 = st.tabs(["💊 PRESCRIZIONE", "🔄 MODIFICA TERAPIA"])
        with t1:
            with st.form("p_p"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"➕ Nuova Terapia: {f} {d}", "Psichiatra", firma_op), True); st.rerun()
        with t2:
            ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            for tid, fr, ds, mv, pv, nv in ter:
                c_f, c_m, c_p, c_n, c_d = st.columns([3,1,1,1,1])
                c_f.write(f"**{fr}** ({ds})")
                nm, np, nn = c_m.checkbox("M", value=bool(mv), key=f"m{tid}"), c_p.checkbox("P", value=bool(pv), key=f"p{tid}"), c_n.checkbox("N", value=bool(nv), key=f"n{tid}")
                if nm != mv or np != pv or nn != nv:
                    db_run("UPDATE terapie SET mat=?, pom=?, nott=? WHERE id_u=?", (int(nm), int(np), int(nn), tid), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"🔄 Modifica turni: {fr}", "Psichiatra", firma_op), True); st.rerun()
                if c_d.button("🗑️", key=f"dt{tid}"):
                    db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"🗑️ Terapia eliminata: {fr}", "Psichiatra", firma_op), True); st.rerun()

    elif ruolo_op == "Infermiere":
        t1, t2, t3 = st.tabs(["💊 SOMMINISTRA", "📝 CONSEGNE", "📊 PARAMETRI"])
        with t1:
            ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            c1,c2,c3 = st.columns(3)
            for t in ter:
                if t[3] and c1.button(f"☀️ MAT: {t[1]}", key=f"im{t[0]}"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"✔️ SOMM MAT: {t[1]}", "Infermiere", firma_op), True); st.rerun()
                if t[4] and c2.button(f"🌤️ POM: {t[1]}", key=f"ip{t[0]}"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"✔️ SOMM POM: {t[1]}", "Infermiere", firma_op), True); st.rerun()
                if t[5] and c3.button(f"🌙 NOT: {t[1]}", key=f"in{t[0]}"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"✔️ SOMM NOT: {t[1]}", "Infermiere", firma_op), True); st.rerun()
        with t2:
            with st.form("f_cons"):
                txt = st.text_area("Note di consegna")
                if st.form_submit_button("REGISTRA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"📝 CONSEGNA: {txt}", "Infermiere", firma_op), True); st.rerun()
        with t3:
            with st.form("f_par"):
                c1,c2,c3 = st.columns(3)
                p_a, f_c, sat = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("Sat%")
                if st.form_submit_button("SALVA"): db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"📊 PARAMETRI: PA {p_a}, FC {f_c}, Sat {sat}%", "Infermiere", firma_op), True); st.rerun()

    elif ruolo_op == "Educatore":
        t1, t2 = st.tabs(["💰 MOVIMENTI", "📜 STORICO"])
        with t1:
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum(m[0] if m[1] == "ENTRATA" else -m[0] for m in mov)
            st.markdown(f"<div class='cassa-card'>Saldo attuale: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
            with st.form("f_cassa"):
                tp, im, cau = st.selectbox("Azione", ["ENTRATA", "USCITA"]), st.number_input("Importo €", min_value=0.0), st.text_input("Causale")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, adesso, cau, im, tp, firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"💰 CASSA: {tp} {im}€ per {cau}", "Educatore", firma_op), True); st.rerun()
        with t2:
            st.table(pd.DataFrame(db_run("SELECT data, tipo, importo, causale FROM cassa WHERE p_id=? ORDER BY id_u DESC", (p_id,)), columns=["Data", "Tipo", "€", "Causale"]))

    elif ruolo_op == "OSS":
        with st.form("f_oss"):
            m = [st.checkbox(k) for k in ["Pulizia Stanza", "Sale Fumo", "Refettorio", "Cortile", "Sala Caffè", "Lavatrice"]]
            if st.form_submit_button("CONFERMA"):
                l = [k for v, k in zip(m, ["Stanza","Fumo","Refettorio","Cortile","Caffè","Lavatrice"]) if v]
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"🧹 MANSIONI: {', '.join(l)}", "OSS", firma_op), True); st.rerun()

# --- NAVIGAZIONE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"): render_postits(pid)

elif nav == "⚙️ Pannello Admin":
    st.markdown("<div class='section-banner'><h2>PANNELLO ADMIN</h2></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["👥 UTENTI", "🗑️ GESTIONE LOG PER PAZIENTE"])
    with t1:
        u_lista = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        for us, no, co, ru in u_lista:
            c1, c2, c3, c4 = st.columns([2,2,2,1])
            c1.write(f"**{us}**"); c2.write(f"{no} {co}"); c3.write(f"*{ru}*")
            if us != 'admin' and c4.button("Rimuovi", key=f"u_{us}"): db_run("DELETE FROM utenti WHERE user=?", (us,), True); st.rerun()
    with t2:
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            p_sel = st.selectbox("Gestisci log di:", [p[1] for p in p_lista])
            pid_log = [p[0] for p in p_lista if p[1] == p_sel][0]
            render_postits(pid_log, limit=100, can_delete=True)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO</h2></div>", unsafe_allow_html=True)
    r_op, f_op = u['ruolo'], firma
    if u['ruolo'] == "Admin":
        r_op = st.selectbox("Agisci come:", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
        f_op = f"ADMIN ({r_op})"; st.divider()
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        pid = [p[0] for p in p_lista if p[1] == p_sel][0]
        logica_equipe(pid, r_op, f_op)

elif nav == "⚙️ Sistema":
    st.markdown("<div class='section-banner'><h2>SISTEMA</h2></div>", unsafe_allow_html=True)
    with st.form("p_new"):
        nome_p = st.text_input("Inserisci Nuovo Paziente")
        if st.form_submit_button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (nome_p.upper(),), True); st.rerun()
