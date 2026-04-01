import sqlite3
import hashlib
import pandas as pd
import streamlit as st
from datetime import datetime

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

# --- CSS DEFINITIVO: TASTI ROSSI NEL SIDEBAR ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; min-width: 300px !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); font-weight: 800; font-size: 1.8rem; text-transform: uppercase; }

    /* TASTI ROSSI NEL SIDEBAR */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #dc2626 !important;
        color: white !important;
        border-radius: 8px !important;
        border: 2px solid #b91c1c !important;
        font-weight: 900 !important;
        height: 40px !important;
        width: 100% !important;
        text-transform: uppercase !important;
        margin-bottom: 10px !important;
    }
    
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #b91c1c !important;
        border-color: #991b1b !important;
    }

    /* POST-IT */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding-bottom: 3px; }
    
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }

    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; color: #166534; }
    .saldo-txt { font-size: 2rem; font-weight: 900; }
</style>
""", unsafe_allow_html=True)

# --- ENGINE DATABASE ---
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
        except Exception as e: return []

# --- GESTIONE SESSIONE ---
if 'user_session' not in st.session_state: st.session_state.user_session = None

if not st.session_state.user_session:
    st.markdown("<div class='section-banner'>REMS CONNECT - ACCESSO</div>", unsafe_allow_html=True)
    u_i = st.text_input("Username")
    p_i = st.text_input("Password", type="password")
    if st.button("LOG IN"):
        res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hashlib.sha256(p_i.encode()).hexdigest()))
        if res:
            st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
            st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR (NAVIGAZIONE + TASTI ROSSI) ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)

# Tasti rossi nel sidebar
c1, c2 = st.sidebar.columns(2)
with c1: 
    if st.button("⬅️"): pass
with c2: 
    if st.button("➡️"): pass

if st.sidebar.button("LOGOUT 🚪"):
    st.session_state.user_session = None
    st.rerun()

st.sidebar.divider()

menu = ["📊 Monitoraggio", "👥 Modulo Equipe"]
if u['ruolo'] == "Admin": menu.append("⚙️ Pannello Admin")
else: menu.append("⚙️ Sistema")
nav = st.sidebar.radio("VAI A:", menu)

st.sidebar.divider()
st.sidebar.caption(f"Utente: {u['nome']} {u['cognome']}")

# --- FUNZIONI OPERATIVE ---
def render_postits(p_id=None, limit=50, can_delete=False):
    res = db_run("SELECT data, ruolo, op, nota, id_u FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT ?", (p_id, limit))
    if not res: st.info("Nessuna attività."); return
    for d, r, o, nt, uid in res:
        col_p, col_d = st.columns([0.93, 0.07])
        col_p.markdown(f'<div class="postit role-{r.lower()}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div class="postit-body">{nt}</div></div>', unsafe_allow_html=True)
        if can_delete:
            if col_d.button("🗑️", key=f"del_{uid}"):
                db_run("DELETE FROM eventi WHERE id_u=?", (uid,), True); st.rerun()

def logica_equipe(p_id, ruolo_op, firma_op):
    adesso = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    if ruolo_op == "Psichiatra":
        t1, t2 = st.tabs(["💊 PRESCRIZIONE", "🔄 MODIFICA TERAPIA"])
        with t1:
            with st.form("presc"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"➕ Nuova Terapia: {f} {d}", "Psichiatra", firma_op), True); st.rerun()
        with t2:
            ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            for tid, fr, ds, mv, pv, nv in ter:
                cf, cm, cp, cn, cd = st.columns([3,1,1,1,1])
                cf.write(f"**{fr}** ({ds})")
                nm, np, nn = cm.checkbox("M", value=bool(mv), key=f"m{tid}"), cp.checkbox("P", value=bool(pv), key=f"p{tid}"), cn.checkbox("N", value=bool(nv), key=f"n{tid}")
                if nm != mv or np != pv or nn != nv:
                    db_run("UPDATE terapie SET mat=?, pom=?, nott=? WHERE id_u=?", (int(nm), int(np), int(nn), tid), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"🔄 Modifica Terapia: {fr}", "Psichiatra", firma_op), True); st.rerun()
                if cd.button("🗑️", key=f"dt_{tid}"):
                    db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"🗑️ Terapia Rimossa: {fr}", "Psichiatra", firma_op), True); st.rerun()

    elif ruolo_op == "Infermiere":
        t1, t2, t3 = st.tabs(["💊 SOMMINISTRA", "📝 CONSEGNE", "📊 PARAMETRI"])
        with t1:
            ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            c1,c2,c3 = st.columns(3)
            for t in ter:
                if t[3] and c1.button(f"☀️ MAT: {t[1]}", key=f"im_{t[0]}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"✔️ SOMMINISTRATO: {t[1]} (MAT)", "Infermiere", firma_op), True); st.rerun()
                if t[4] and c2.button(f"🌤️ POM: {t[1]}", key=f"ip_{t[0]}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"✔️ SOMMINISTRATO: {t[1]} (POM)", "Infermiere", firma_op), True); st.rerun()
                if t[5] and c3.button(f"🌙 NOT: {t[1]}", key=f"in_{t[0]}"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"✔️ SOMMINISTRATO: {t[1]} (NOT)", "Infermiere", firma_op), True); st.rerun()
        with t2:
            with st.form("inf_c"):
                cons = st.text_area("Diario/Consegne")
                if st.form_submit_button("INVIA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"📝 CONSEGNA: {cons}", "Infermiere", firma_op), True); st.rerun()
        with t3:
            with st.form("inf_p"):
                c1,c2,c3 = st.columns(3)
                pa, fc, sat = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("Sat%")
                if st.form_submit_button("REGISTRA PARAMETRI"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"📊 PARAMETRI: PA {pa}, FC {fc}, Sat {sat}%", "Infermiere", firma_op), True); st.rerun()

    elif ruolo_op == "OSS":
        with st.form("oss_m"):
            m = [st.checkbox(k) for k in ["Pulizia Stanza", "Sale Fumo", "Refettorio", "Cortile", "Sala Caffè", "Lavatrice"]]
            if st.form_submit_button("SALVA ATTIVITÀ"):
                l = [k for v, k in zip(m, ["Stanza","Fumo","Refettorio","Cortile","Caffè","Lavatrice"]) if v]
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"🧹 MANSIONI: {', '.join(l)}", "OSS", firma_op), True); st.rerun()

    elif ruolo_op == "Educatore":
        t1, t2 = st.tabs(["💰 NUOVO MOVIMENTO", "📜 STORICO CASSA"])
        with t1:
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum(m[0] if m[1] == "ENTRATA" else -m[0] for m in mov)
            st.markdown(f"<div class='cassa-card'>SALDO: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
            with st.form("cassa_f"):
                tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€", min_value=0.0), st.text_input("Causale")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, adesso, cau, im, tp, firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso, f"💰 CASSA: {tp} di {im}€ ({cau})", "Educatore", firma_op), True); st.rerun()
        with t2:
            st.table(pd.DataFrame(db_run("SELECT data, tipo, importo, causale FROM cassa WHERE p_id=? ORDER BY id_u DESC", (p_id,)), columns=["Data", "Tipo", "€", "Causale"]))

# --- NAVIGAZIONE PAGINE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'>DIARIO CLINICO</div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"): render_postits(pid)

elif nav == "⚙️ Pannello Admin":
    st.markdown("<div class='section-banner'>ADMINISTRATION</div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["👥 UTENTI", "🗑️ GESTIONE LOG"])
    with t1:
        u_list = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        for us, no, co, ru in u_list:
            c1, c2, c3, c4 = st.columns([2,2,2,1])
            c1.write(f"**{us}**"); c2.write(f"{no} {co}"); c3.write(ru)
            if us != 'admin' and c4.button("ELIMINA", key=f"u_{us}"):
                db_run("DELETE FROM utenti WHERE user=?", (us,), True); st.rerun()
    with t2:
        p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista:
            sel_p = st.selectbox("Gestisci log di:", [p[1] for p in p_lista])
            pid_log = [p[0] for p in p_lista if p[1] == sel_p][0]
            render_postits(pid_log, can_delete=True)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'>MODULO EQUIPE</div>", unsafe_allow_html=True)
    r_op, f_op = u['ruolo'], firma
    if u['ruolo'] == "Admin":
        r_op = st.selectbox("Simula Ruolo Professionale:", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
        f_op = f"ADMIN as {r_op}"; st.divider()
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona il Paziente", [p[1] for p in p_lista])
        pid = [p[0] for p in p_lista if p[1] == p_sel][0]
        logica_equipe(pid, r_op, f_op)

elif nav == "⚙️ Sistema":
    st.markdown("<div class='section-banner'>ANAGRAFICA</div>", unsafe_allow_html=True)
    with st.form("new_p"):
        nome_p = st.text_input("Inserisci Nuovo Paziente")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nome_p.upper(),), True); st.rerun()
