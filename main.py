import sqlite3
import streamlit as st
from datetime import datetime
import hashlib
import pandas as pd

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v14.5 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v14.5", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    
    /* STILE POST-IT PER RUOLO */
    .postit { padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 10px solid; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: #1e293b; background-color: #ffffff; }
    .postit-header { font-weight: 800; font-size: 0.85rem; text-transform: uppercase; margin-bottom: 5px; display: flex; justify-content: space-between; }
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; }  
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    
    /* GRAFICA TERAPIA */
    .therapy-container {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; border-left: 8px solid #1e3a8a;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .turn-header { font-weight: 800; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 10px; }
    .mat-style { color: #d97706; } .pom-style { color: #2563eb; } .not-style { color: #4338ca; }
    .farmaco-title { font-size: 1.2rem; font-weight: 900; color: #1e293b; margin: 0; }
    .dose-subtitle { font-size: 1rem; color: #64748b; font-weight: 600; margin-bottom: 10px; }
    
    /* DASHBOARD CASSA */
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
</style>
""", unsafe_allow_html=True)

# --- MOTORE DATABASE ---
DB_NAME = "rems_final_v12.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        # Creazione tabelle se non esistono
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
            st.error(f"Errore Critico Database: {e}"); return []

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

# --- GESTIONE ACCESSO ---
if 'user_session' not in st.session_state: st.session_state.user_session = None
if not st.session_state.user_session:
    st.markdown("<div class='section-banner'><h2>🏥 REMS CONNECT - PORTALE SICURO</h2></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔐 LOGIN", "📝 REGISTRAZIONE NUOVO OPERATORE"])
    with t1:
        with st.form("login"):
            u_i, p_i = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("ACCEDI"):
                res = db_run("SELECT nome, cognome, qualifica FROM utenti WHERE user=? AND pwd=?", (u_i, hash_pw(p_i)))
                if res: 
                    st.session_state.user_session = {"nome": res[0][0], "cognome": res[0][1], "ruolo": res[0][2]}
                    st.rerun()
    with t2:
        with st.form("reg"):
            nu, np = st.text_input("Nuovo Username"), st.text_input("Nuova Password", type="password")
            nn, nc = st.text_input("Nome"), st.text_input("Cognome")
            nq = st.selectbox("Qualifica", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
            if st.form_submit_button("REGISTRA"):
                db_run("INSERT INTO utenti VALUES (?,?,?,?,?)", (nu, hash_pw(np), nn, nc, nq), True)
                st.success("Utente creato!"); st.rerun()
    st.stop()

u = st.session_state.user_session
firma = f"{u['nome']} {u['cognome']} ({u['ruolo']})"

# --- SIDEBAR E NAVIGAZIONE ---
st.sidebar.markdown("<div class='sidebar-title'>Rems-connect</div>", unsafe_allow_html=True)
st.sidebar.write(f"🟢 Operatore: **{u['nome']} {u['cognome']}**")
nav = st.sidebar.radio("MODULI OPERATIVI", ["📊 Monitoraggio Generale", "👥 Modulo Equipe", "⚙️ Amministrazione"])
if st.sidebar.button("ESCI DAL SISTEMA"): st.session_state.user_session = None; st.rerun()

# --- MODULO 1: MONITORAGGIO ---
if nav == "📊 Monitoraggio Generale":
    st.markdown("<div class='section-banner'><h2>DIARIO CLINICO INTEGRATO</h2></div>", unsafe_allow_html=True)
    pazienti = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in pazienti:
        with st.expander(f"📁 CARTELLA CLINICA: {nome}"):
            render_postits(pid)

# --- MODULO 2: EQUIPE ---
elif nav == "👥 Modulo Equipe":
    ruolo_corr = u['ruolo']
    if u['ruolo'] == "Admin": ruolo_corr = st.selectbox("Simula Figura:", ["Psichiatra", "Infermiere", "Educatore", "OSS"])
    
    p_lista = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_lista:
        p_sel = st.selectbox("Seleziona Paziente in carico", [p[1] for p in p_lista])
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = datetime.now()
        oggi = now.strftime("%d/%m/%Y")

        if ruolo_corr == "Psichiatra":
            st.subheader("Gestione Terapie e Prescrizioni")
            with st.form("form_presc"):
                f, d = st.text_input("Nome Farmaco"), st.text_input("Dosaggio")
                c1,c2,c3 = st.columns(3); m,p,n = c1.checkbox("MAT"), c2.checkbox("POM"), c3.checkbox("NOT")
                if st.form_submit_button("REGISTRA PRESCRIZIONE"):
                    db_run("INSERT INTO terapie (p_id, farmaco, dose, mat, pom, nott, medico) VALUES (?,?,?,?,?,?,?)", (p_id, f, d, int(m), int(p), int(n), firma), True)
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"➕ Nuova Prescrizione: {f} {d}", "Psichiatra", firma), True); st.rerun()

        elif ruolo_corr == "Infermiere":
            t1, t2, t3 = st.tabs(["💊 SOMMINISTRAZIONE TERAPIA", "💓 PARAMETRI VITALI", "📝 CONSEGNE INFERMIERISTICHE"])
            
            with t1:
                terapie = db_run("SELECT id_u, farmaco, dose, mat, pom, nott FROM terapie WHERE p_id=?", (p_id,))
                cols = st.columns(3)
                turni = [("MAT", 3, "mat-style", "☀️"), ("POM", 4, "pom-style", "🌤️"), ("NOT", 5, "not-style", "🌙")]
                for i, (t_n, t_idx, t_css, t_ico) in enumerate(turni):
                    with cols[i]:
                        st.write(f"**{t_n}**")
                        for f in [x for x in terapie if x[t_idx]]:
                            # LA TUA STRINGA MAGICA PER LA SPARIZIONE:
                            check = db_run("SELECT id_u FROM eventi WHERE id=? AND nota LIKE ? AND data LIKE ?", (p_id, f"%SOMM ({t_n}): {f[1]}%", f"{oggi}%"))
                            if not check:
                                st.markdown(f"""<div class='therapy-container'><div class='turn-header {t_css}'>{t_ico} {t_n}</div>
                                <div class='farmaco-title'>{f[1]}</div><div class='dose-subtitle'>{f[2]}</div></div>""", unsafe_allow_html=True)
                                if st.button(f"CONFERMA {t_n}", key=f"btn_{f[0]}_{t_n}"):
                                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"✔️ SOMM ({t_n}): {f[1]}", "Infermiere", firma), True); st.rerun()

            with t2:
                with st.form("form_vitali"):
                    c1, c2, c3 = st.columns(3)
                    pa = c1.text_input("PA (Pressione)")
                    fc = c2.text_input("FC (Frequenza)")
                    sat = c3.text_input("SatO2 %")
                    c4, c5 = st.columns(2)
                    temp = c4.text_input("Temp °C")
                    gli = c5.text_input("Glicemia")
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        nota_v = f"💓 PARAMETRI: PA {pa} | FC {fc} | SatO2 {sat}% | TC {temp}° | Glic {gli}"
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), nota_v, "Infermiere", firma), True); st.rerun()

            with t3:
                with st.form("form_consegna_inf"):
                    txt_inf = st.text_area("Annotazioni Cliniche / Consegne del Turno")
                    if st.form_submit_button("SALVA NOTA INFERMIERISTICA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt_inf, "Infermiere", firma), True); st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("form_oss_full"):
                st.subheader("Diario Assistenziale OSS")
                m_list = ["Igiene Totale", "Igiene Parziale", "Cambio Panno", "Pulizia Stanza", "Rifacimento Letto", "Accompagnamento Cortile", "Monitoraggio Sale Fumo", "Lavatrice/Guardaroba"]
                mansioni = st.multiselect("Attività Svolte:", m_list)
                
                c1, c2, c3 = st.columns(3)
                pasto = c1.radio("Pasto:", ["Regolare", "Parziale", "Rifiutato"])
                diu = c2.radio("Diuresi:", ["Regolare", "Scarsa", "Assente"])
                alvo = c3.radio("Alvo:", ["Regolare", "Stitico", "Diarroico"])
                
                nota_oss = st.text_area("Consegne e Note OSS")
                if st.form_submit_button("REGISTRA CONSEGNA ASSISTENZIALE"):
                    nota_f = f"🧹 ATTIVITÀ: {', '.join(mansioni)} | PASTO: {pasto} | DIURESI: {diu} | ALVO: {alvo} | NOTE: {nota_oss}"
                    db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), nota_f, "OSS", firma), True); st.rerun()

        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 GESTIONE CASSA PAZIENTE", "📖 DIARIO EDUCATIVO"])
            with t1:
                mov = db_run("SELECT importo, tipo FROM cassa WHERE p_id=?", (p_id,))
                saldo = sum(m[0] if m[1]=="ENTRATA" else -m[0] for m in mov)
                st.markdown(f"<div class='cassa-card'>Saldo Attuale: <span class='saldo-txt'>{saldo:.2f} €</span></div>", unsafe_allow_html=True)
                with st.form("form_cassa"):
                    tipo, imp, cau = st.selectbox("Tipo Operazione", ["ENTRATA", "USCITA"]), st.number_input("Importo (€)", min_value=0.0), st.text_input("Causale Movimento")
                    if st.form_submit_button("ESEGUI TRANSAZIONE"):
                        db_run("INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)", (p_id, oggi, cau, imp, tipo, firma), True)
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), f"💰 {tipo}: {imp}€ - {cau}", "Educatore", firma), True); st.rerun()
            with t2:
                with st.form("form_nota_ed"):
                    txt_ed = st.text_area("Osservazioni comportamentali / Attività educative")
                    if st.form_submit_button("SALVA NOTA EDUCATIVA"):
                        db_run("INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)", (p_id, now.strftime("%d/%m/%Y %H:%M"), txt_ed, "Educatore", firma), True); st.rerun()

        st.divider()
        st.write("### Ultime 10 voci del Diario per questo paziente")
        render_postits(p_id, limit=10, filter_role=ruolo_corr)

# --- MODULO 3: ADMIN ---
elif nav == "⚙️ Amministrazione":
    st.markdown("<div class='section-banner'><h2>GESTIONE ANAGRAFICA PAZIENTI</h2></div>", unsafe_allow_html=True)
    with st.form("add_paz"):
        nome_p = st.text_input("Inserisci Nome e Cognome nuovo paziente")
        if st.form_submit_button("REGISTRA IN ANAGRAFICA"):
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nome_p.upper(),), True)
            st.success("Paziente registrato correttamente!"); st.rerun()
    
    st.subheader("Elenco Pazienti Residenti")
    elenco = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    for pid, nome in elenco:
        c1, c2 = st.columns([0.8, 0.2])
        c1.write(f"🔹 {nome} (ID: {pid})")
        if c2.button("RIMUOVI 🗑️", key=f"del_{pid}"):
            db_run("DELETE FROM pazienti WHERE id=?", (pid,), True)
            db_run("DELETE FROM terapie WHERE p_id=?", (pid,), True)
            st.warning(f"Paziente {nome} rimosso."); st.rerun()
