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

    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2rem; font-weight: 900; color: #166534; }
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
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - ACCESSO</h2></div>", unsafe_allow_html=True)
    t_log, t_reg = st.tabs(["🔐 ACCEDI", "📝 REGISTRATI"])
    with t_log:
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
menu = ["📊 Monitoraggio", "👥 Modulo Equipe"]
if u['ruolo'] == "Admin": menu.append("⚙️ Pannello Admin")
else: menu.append("⚙️ Sistema")
nav = st.sidebar.radio("NAVIGAZIONE", menu)
if st.sidebar.button("LOGOUT"): st.session_state.user_session = None; st.rerun()

# --- LOGICA OPERATIVA ---
def logica_equipe(p_id, ruolo_op, firma_op):
    now = datetime.now()
    adesso_str = now.strftime("%d/%m/%Y %H:%M")
    
    # Calcolo data riferimento per il ciclo delle 06:00
    if now.hour < 6:
        data_rif = (now.replace(hour=0, minute=0) - pd.Timedelta(days=1)).strftime("%d/%m/%Y")
    else:
        data_rif = now.strftime("%d/%m/%Y")
    rif_full = f"{data_rif} 06:00"

    if ruolo_op == "Psichiatra":
        t1, t2 = st.tabs(["💊 NUOVA PRESCRIZIONE", "🔄 MODIFICA TERAPIA"])
        with t1:
            with st.form("p_ps"):
                f, d = st.text_input("Farmaco"), st.text_input("Dose")
                c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("CONFERMA"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"➕ Nuova Terapia: {f} {d}", "Psichiatra", firma_op), True); st.rerun()
        with t2:
            terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            for tid, fr, ds, mv, pv, nv in terapie:
                cf, cm, cp, cn, cd = st.columns([3,1,1,1,1])
                cf.write(f"**{fr}** ({ds})")
                nm, np, nn = cm.checkbox("M", value=bool(mv), key=f"m{tid}"), cp.checkbox("P", value=bool(pv), key=f"p{tid}"), cn.checkbox("N", value=bool(nv), key=f"n{tid}")
                if nm != mv or np != pv or nn != nv:
                    db_run("UPDATE terapie SET mat=?, pom=?, nott=? WHERE id_u=?", (int(nm), int(np), int(nn), tid), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"🔄 Modifica turni farmaco: {fr}", "Psichiatra", firma_op), True); st.rerun()
                if cd.button("🗑️", key=f"dt{tid}"):
                    db_run("DELETE FROM terapie WHERE id_u=?", (tid,), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"🗑️ Eliminata terapia: {fr}", "Psichiatra", firma_op), True); st.rerun()

    elif ruolo_op == "Infermiere":
        t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONI", "📝 CONSEGNE", "📊 PARAMETRI"])
        with t1:
            ter = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
            mostrati = 0
            for t in ter:
                turni_prescritti = []
                if t[3]: turni_prescritti.append("MAT")
                if t[4]: turni_prescritti.append("POM")
                if t[5]: turni_prescritti.append("NOT")
                
                turni_disp = []
                for tp in turni_prescritti:
                    # Controllo RIGOROSO: Cerca se esiste un evento per questo farmaco e questo turno dopo il reset
                    check = db_run("SELECT id_u FROM eventi WHERE id=? AND data >= ? AND nota LIKE ?", (p_id, rif_full, f"%TERAPIA {tp}: {t[1]}%"))
                    if not check:
                        turni_disp.append(tp)
                
                if turni_disp:
                    mostrati += 1
                    with st.expander(f"📌 {t[1]} - {t[2]}", expanded=True):
                        c1, c2, c3 = st.columns(3)
                        st_turno = c1.selectbox("Turno", turni_disp, key=f"t_{t[0]}")
                        esito = c2.radio("Esito", ["ASSUNTA", "RIFIUTATA"], key=f"e_{t[0]}", horizontal=True)
                        if c3.button(f"REGISTRA {st_turno}", key=f"b_{t[0]}"):
                            icona = "✔️" if esito == "ASSUNTA" else "❌"
                            # Nota formattata per essere riconosciuta dal controllo LIKE
                            nota_somm = f"{icona} TERAPIA {st_turno}: {t[1]} ({esito})"
                            db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, nota_somm, "Infermiere", firma_op), True); st.rerun()
            if mostrati == 0: st.success("✅ Ciclo terapie completato per questo paziente.")

        with t2:
            with st.form("inf_cons"):
                cons = st.text_area("Consegne")
                if st.form_submit_button("INVIA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"📝 CONSEGNA: {cons}", "Infermiere", firma_op), True); st.rerun()
        with t3:
            with st.form("inf_par"):
                c1, c2, c3 = st.columns(3)
                pa, fc, sat, te, gl = c1.text_input("PA"), c2.text_input("FC"), c3.text_input("Sat%"), c1.text_input("Temp"), c2.text_input("Glic")
                if st.form_submit_button("SALVA"):
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"📊 PARAMETRI: PA {pa}, FC {fc}, Sat {sat}%, T {te}, G {gl}", "Infermiere", firma_op), True); st.rerun()

    elif ruolo_op == "Educatore":
        t1, t2 = st.tabs(["💰 MOVIMENTO", "📜 STORICO"])
        with t1:
            mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
            saldo = sum(m[0] if m[1] == "ENTRATA" else -m[0] for m in mov)
            st.markdown(f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
            with st.form("cs_e"):
                tp, im, cau = st.selectbox("Tipo", ["ENTRATA", "USCITA"]), st.number_input("€", min_value=0.0), st.text_input("Causale")
                if st.form_submit_button("REGISTRA"):
                    db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, adesso_str, cau, im, tp, firma_op), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"💰 MOV. CASSA: {tp} di {im}€ ({cau})", "Educatore", firma_op), True); st.rerun()
        with t2:
            storico = db_run("SELECT data, tipo, importo, causale FROM cassa WHERE p_id=? ORDER BY id_u DESC", (p_id,))
            st.table(pd.DataFrame(storico, columns=["Data", "Tipo", "Euro", "Causale"]))

    elif ruolo_op == "OSS":
        with st.form("oss_man"):
            m = [st.checkbox(l) for l in ["Pulizia Stanza","Sale Fumo","Refettorio","Cortile","Sala Caffè","Lavatrice"]]
            if st.form_submit_button("CONFERMA"):
                lista = [l for v, l in zip(m, ["Stanza","Fumo","Refettorio","Cortile","Caffè","Lavatrice"]) if v]
                db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, adesso_str, f"🧹 MANSIONI: {', '.join(lista)}", "OSS", firma_op), True); st.rerun()

    st.divider()
    st.subheader(f"Situazione Clinica Recente")
    render_postits(p_id, limit=8)

# --- NAVIGAZIONE ---
if nav == "📊 Monitoraggio":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO COMPLETO</h2></div>", unsafe_allow_html=True)
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_lista:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"): render_postits(pid)

elif nav == "⚙️ Pannello Admin":
    st.markdown("<div class='section-banner'><h2>ADMIN CONTROL</h2></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["👥 UTENTI", "🗑️ GESTIONE LOG"])
    with t1:
        utenti = db_run("SELECT user, nome, cognome, qualifica FROM utenti")
        for us, no, co, ru in utenti:
            c1, c2, c3, c4 = st.columns([2,2,2,1])
            c1.write(f"**{us}**"); c2.write(f"{no} {co}"); c3.write(f"*{ru}*")
            if us != 'admin' and c4.button("Elimina", key=f"delu_{us}"):
                db_run("DELETE FROM utenti WHERE user=?", (us,), True); st.rerun()
    with t2:
        p_lista_log = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        if p_lista_log:
            p_sel_log = st.selectbox("Paziente:", [p[1] for p in p_lista_log])
            p_id_log = [p[0] for p in p_lista_log if p[1] == p_sel_log][0]
            render_postits(p_id=p_id_log, limit=100, can_delete=True)

elif nav == "👥 Modulo Equipe":
    st.markdown(f"<div class='section-banner'><h2>MODULO OPERATIVO INTEGRATO</h2></div>", unsafe_allow_html=True)
    ruolo_da_usare, firma_da_usare = u['ruolo'], firma
    if u['ruolo'] == "Admin":
        ruolo_da_usare = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
        firma_da_usare = f"ADMIN as {ruolo_da_usare}"; st.divider()
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        logica_equipe(p_id, ruolo_da_usare, firma_da_usare)

elif nav == "⚙️ Sistema":
    st.markdown("<div class='section-banner'><h2>GESTIONE ANAGRAFICA</h2></div>", unsafe_allow_html=True)
    with st.form("p_add"):
        np = st.text_input("Nome Paziente")
        if st.form_submit_button("AGGIUNGI"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (np.upper(),), True); st.rerun()
    
    st.divider()
    st.subheader("Pazienti Attuali")
    p_all = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in p_all:
        col1, col2 = st.columns([0.8, 0.2])
        col1.write(nome)
        if col2.button("Elimina", key=f"delp_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True); st.rerun()
