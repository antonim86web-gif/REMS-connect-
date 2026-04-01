import sqlite3
import streamlit as st
from datetime import datetime
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO ---
st.set_page_config(page_title="REMS Connect ELITE PRO v12.5", layout="wide", page_icon="🏥")

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
    .farmaco-row { background: white; padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
</style>
""", unsafe_allow_html=True)

# --- DATABASE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS utenti (user TEXT PRIMARY KEY, pwd TEXT, nome TEXT, cognome TEXT, qualifica TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, nota TEXT, ruolo TEXT, op TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dose TEXT, mat INTEGER, pom INTEGER, nott INTEGER, medico TEXT, id_u INTEGER PRIMARY KEY AUTOINCREMENT)")
        try:
            if query: cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall()
        except Exception as e:
            st.error(f"Errore DB: {e}"); return []

def hash_pw(p): return hashlib.sha256(str.encode(p)).hexdigest()

def render_postits(p_id=None, limit=50, can_delete=False):
    query = "SELECT data, ruolo, op, nota, id_u FROM eventi"
    params = []
    if p_id: query += " WHERE id=?"; params.append(p_id)
    query += " ORDER BY id_u DESC LIMIT ?"
    res = db_run(query, tuple(params + [limit]))
    if not res:
        st.info("Nessun post-it trovato.")
        return
    for d, r, o, nt, uid in res:
        cls = f"role-{r.lower()}"
        col_p, col_d = st.columns([0.92, 0.08])
        col_p.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div class="postit-body">{nt}</div></div>', unsafe_allow_html=True)
        if can_delete:
            if col_d.button("🗑️", key=f"del_ev_{uid}"):
                db_run("DELETE FROM eventi WHERE id_u=?", (uid,), True); st.rerun()

# --- LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if not st.session_state.user_session:
    # ... (Login standard) ...
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO</h2></div>", unsafe_allow_html=True)
    with st.form("l"):
        u_i, p_i = st.text_input("User"), st.text_input("Password", type="password")
        if st.form_submit_button("ENTRA"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
            if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
menu = ["📊 Monitoraggio", "👥 Modulo Equipe", "⚙️ Sistema"]
nav = st.sidebar.radio("NAVIGAZIONE", menu)
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- LOGICA OPERATIVA ---
def logica_equipe(p_id, ruolo_op, firma_op):
    now = datetime.now()
    adesso_str = now.strftime("%d/%m/%Y %H:%M")
    
    # Calcolo Reset ore 06:00
    if now.hour < 6:
        data_rif = (now.replace(hour=0, minute=0) - pd.Timedelta(days=1)).strftime("%d/%m/%Y")
    else:
        data_rif = now.strftime("%d/%m/%Y")
    rif_full = f"{data_rif} 06:00"

    if ruolo_op == "Psichiatra":
        # ... (Logica Psichiatra Invariata) ...
        t1, t2 = st.tabs(["💊 NUOVA PRESCRIZIONE", "🔄 MODIFICA"])
        with t1:
            with st.form("p_ps"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("CONFERMA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"➕ Nuova Terapia: {f} {d}", "Psichiatra", firma_op), True); st.rerun()
        with t2:
            ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            for tid, fr, ds, mv, pv, nv in ter:
                col_f, col_m, col_p, col_n, col_d = st.columns([3,1,1,1,1])
                col_f.write(f"**{fr}**")
                nm, np, nn = col_m.checkbox("M", value=bool(mv), key=f"m{tid}"), col_p.checkbox("P", value=bool(pv), key=f"p{tid}"), col_n.checkbox("N", value=bool(nv), key=f"n{tid}")
                if nm != mv or np != pv or nn != nv:
                    db_run("UPDATE terapie SET mat=?, pom=?, nott=? WHERE id_u=?", (int(nm), int(np), int(nn), tid), True); st.rerun()
                if col_d.button("🗑️", key=f"del_{tid}"):
                    db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True); st.rerun()

    elif ruolo_op == "Infermiere":
        t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONE", "📝 CONSEGNE", "📊 PARAMETRI"])
        with t1:
            terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            
            for label, db_col in [("☀️ MATTINA", 3), ("⛅ POMERIGGIO", 4), ("🌙 NOTTE", 5)]:
                st.markdown(f"<div class='turno-header'>{label}</div>", unsafe_allow_html=True)
                
                turno_code = label.split()[1][:3] # MAT, POM, NOT
                f_in_turno = [t for t in terapie if t[db_col] == 1]
                
                mostrati = 0
                for f in f_in_turno:
                    # Controllo se è già stato somministrato per questo turno dopo le 06:00
                    check = db_run("SELECT id_u FROM eventi WHERE id=? AND data >= ? AND nota LIKE ?", (p_id, rif_full, f"%{turno_code}: {f[1]}%"))
                    
                    if not check:
                        mostrati += 1
                        with st.container():
                            col_info, col_btn = st.columns([0.7, 0.3])
                            col_info.markdown(f"**{f[1]}** — *{f[2]}*")
                            
                            c_ass, c_rif = col_btn.columns(2)
                            if c_ass.button("✅", key=f"ass_{f[0]}_{turno_code}", help="Assunta"):
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"✅ TERAPIA {turno_code}: {f[1]} (ASSUNTA)", "Infermiere", firma_op), True); st.rerun()
                            if c_rif.button("⭕", key=f"rif_{f[0]}_{turno_code}", help="Rifiutata"):
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"⭕ TERAPIA {turno_code}: {f[1]} (RIFIUTATA)", "Infermiere", firma_op), True); st.rerun()
                
                if mostrati == 0:
                    st.write("--- *Nessun farmaco da somministrare* ---")

        with t2:
            with st.form("c"):
                txt = st.text_area("Consegne")
                if st.form_submit_button("INVIA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"📝 CONSEGNA: {txt}", "Infermiere", firma_op), True); st.rerun()
        with t3:
            with st.form("p"):
                c1,c2,c3 = st.columns(3)
                pa, fc, sat = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("Sat%")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"📊 PARAMETRI: PA {pa}, FC {fc}, Sat {sat}", "Infermiere", firma_op), True); st.rerun()

    elif ruolo_op == "OSS":
        with st.form("o"):
            m = [st.checkbox(l) for l in ["Stanza", "Fumo", "Refettorio"]]
            if st.form_submit_button("CONFERMA"):
                res = ", ".join([l for v,l in zip(m, ["Stanza", "Fumo", "Refettorio"]) if v])
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"🧹 MANSIONI: {res}", "OSS", firma_op), True); st.rerun()

    st.divider()
    st.subheader("Storico Recente (Post-it)")
    render_postits(p_id, limit=8)

# --- NAVIGAZIONE PRINCIPALE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>MONITORAGGIO PAZIENTI</h2></div>", unsafe_allow_html=True)
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"📁 {nome}"): render_postits(pid)

elif nav == "👥 Modulo Equipe":
    st.markdown("<div class='section-banner'><h2>MODULO OPERATIVO</h2></div>", unsafe_allow_html=True)
    ruolo_corr, firma_corr = u['ruolo'], firma
    if u['ruolo'] == "Admin":
        ruolo_corr = st.selectbox("Simula:", ["Psichiatra", "Infermiere", "OSS"])
        firma_corr = f"ADMIN as {ruolo_corr}"
    
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pazienti:
        p_sel = st.selectbox("Paziente:", [p[1] for p in pazienti])
        p_id = [p[0] for p in pazienti if p[1] == p_sel][0]
        logica_equipe(p_id, ruolo_corr, firma_corr)

elif nav == "⚙️ Sistema":
    with st.form("a"):
        np = st.text_input("Nuovo Paziente")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
