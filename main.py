import sqlite3
import streamlit as st
from datetime import datetime
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v15.0 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v15.0", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    
    /* TASTO LOGOUT VERDE */
    .stButton>button[kind="secondary"] { background-color: #22c55e !important; color: white !important; border: none !important; width: 100%; font-weight: 700; }
    
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    
    .therapy-container { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .turn-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; }
    .mat-style { color: #d97706; } .pom-style { color: #2563eb; } .not-style { color: #4338ca; }
    .farmaco-title { font-size: 1.2rem; font-weight: 900; color: #1e293b; margin: 0; }
    .dose-subtitle { font-size: 1rem; color: #64748b; font-weight: 600; margin-bottom: 10px; }
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
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

def render_postits(p_id=None, limit=50, filter_role=None):
    query = "SELECT data, ruolo, op, nota FROM eventi WHERE 1=1"
    params = []
    if p_id: query += " AND id=?"; params.append(p_id)
    if filter_role: query += " AND ruolo=?"; params.append(filter_role)
    res = db_run(query + " ORDER BY id_u DESC LIMIT ?", tuple(params + [limit]))
    for d, r, o, nt in res:
        cls = f"role-{r.lower()}"
        st.markdown(f'<div class="postit {cls}"><div class="postit-header"><span>👤 {o} ({r})</span><span>📅 {d}</span></div><div>{nt}</div></div>', unsafe_allow_html=True)

# --- LOGIN ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT LOGIN</h2></div>", unsafe_allow_html=True)
    with st.form("login"):
        u_i, p_i = st.text_input("User"), st.text_input("Password", type="password")
        if st.form_submit_button("ACCEDI"):
            res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
            if res: st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}; st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
nav = st.sidebar.radio("MENU", ["📊 Monitoraggio", "👥 Modulo Equipe", "⚙️ Admin"])
if st.sidebar.button("LOGOUT SICURO"): 
    st.session_state.user_session = None; st.rerun()

# --- MODULI ---
if nav == "📊 Monitoraggio":
    for pid, nome in db_run("SELECT id, nome FROM pazienti ORDER BY nome"):
        with st.expander(f"📁 {nome}"): render_postits(pid)

elif nav == "👥 Modulo Equipe":
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": ruolo_corr = st.selectbox("Simula:", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = datetime.now(); oggi = now.strftime("%d/%m/%Y")

        if ruolo_corr == "Psichiatra":
            t1, t2 = st.tabs(["➕ Nuova Terapia", "📝 Modifica/Sospendi"])
            with t1:
                with st.form("f_ps"):
                    f, d = st.text_input("Farmaco"), st.text_input("Dose")
                    c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                    if st.form_submit_button("REGISTRA"):
                        db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"➕ Prescritto: {f} {d}", "Psichiatra", firma), True); st.rerun()
            with t2:
                terapie_attive = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                for tid, fn, ds, m_v, p_v, n_v in terapie_attive:
                    with st.expander(f"Modifica: {fn} ({ds})"):
                        with st.form(key=f"mod_{tid}"):
                            new_f = st.text_input("Farmaco", value=fn)
                            new_d = st.text_input("Dose", value=ds)
                            cc1, cc2, cc3 = st.columns(3)
                            nm = cc1.checkbox("MAT", value=bool(m_v))
                            np = cc2.checkbox("POM", value=bool(p_v))
                            nn = cc3.checkbox("NOT", value=bool(n_v))
                            c_m1, c_m2 = st.columns(2)
                            if c_m1.form_submit_button("AGGIORNA"):
                                db_run("UPDATE terapie SET farmaco=?, dose=?, mat=?, pom=?, nott=? WHERE id_u=?", (new_f, new_d, int(nm), int(np), int(nn), tid), True)
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"📝 Modificato: {new_f}", "Psichiatra", firma), True); st.rerun()
                            if c_m2.form_submit_button("SOSPENDI ❌"):
                                db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"❌ Sospeso: {fn}", "Psichiatra", firma), True); st.rerun()

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
                                if st.button(f"SOMM. {f[1]}", key=f"ok_{f[0]}_{t_n}"):
                                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({t_n}): {f[1]}", "Infermiere", firma), True); st.rerun()
            with t2:
                with st.form("vit"):
                    c1,c2,c3 = st.columns(3); pa=c1.text_input("PA"); fc=c2.text_input("FC"); sat=c3.text_input("SatO2")
                    c4,c5 = st.columns(2); tc=c4.text_input("TC"); gl=c5.text_input("Glicemia")
                    if st.form_submit_button("SALVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💓 PA:{pa} FC:{fc} Sat:{sat} TC:{tc} Gl:{gl}", "Infermiere", firma), True); st.rerun()
            with t3:
                with st.form("n_i"):
                    txt = st.text_area("Nota"); 
                    if st.form_submit_button("INVIA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt, "Infermiere", firma), True); st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("oss_v2"):
                st.subheader("Consegne OSS")
                mans = st.multiselect("Attività:", ["Igiene Totale", "Igiene Parziale", "Cambio Panno", "Pulizia Stanza", "Letto", "Cortile", "Sale Fumo", "Lavatrice"])
                txt = st.text_area("Note e Consegne")
                if st.form_submit_button("REGISTRA"):
                    nota_oss = f"🧹 {', '.join(mans)} | NOTE: {txt}"
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), nota_oss, "OSS", firma), True); st.rerun()

        elif ruolo_corr == "Educatore":
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
            st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
            with st.form("cs"):
                tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€"), st.text_input("Causale")
                if st.form_submit_button("OK"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi, cau, im, tp, firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tp}: {im}€ - {cau}", "Educatore", firma), True); st.rerun()

        st.divider(); render_postits(p_id, filter_role=ruolo_corr)

elif nav == "⚙️ Admin":
    np = st.text_input("Paziente"); 
    if st.button("AGGIUNGI"): db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
