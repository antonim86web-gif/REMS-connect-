import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import plotly.express as px

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect PRO", layout="wide")

st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    [data-testid="column"] { padding-left: 3px !important; padding-right: 3px !important; }
    .stButton>button {
        width: 100%; border-radius: 6px; height: 42px !important; 
        background-color: white !important; color: #1e3a8a !important; 
        border: 1px solid #cbd5e1; font-size: 0.85rem !important; font-weight: 600;
    }
    .active-btn button { background-color: #1e3a8a !important; color: white !important; border: 1px solid #1e3a8a !important; }
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    .terapia-card {border-left-color: #10b981 !important; background-color: #f0fdf4 !important;}
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS terapie (p_id INTEGER, farmaco TEXT, dosaggio TEXT, data TEXT, medico TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS documenti (p_id INTEGER, nome_doc TEXT, file_blob BLOB, data TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        
        try:
            cur.execute("SELECT medico FROM terapie LIMIT 1")
        except sqlite3.OperationalError:
            cur.execute("ALTER TABLE terapie ADD COLUMN medico TEXT DEFAULT 'N.D.'")
            conn.commit()

        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'menu' not in st.session_state: st.session_state.menu = "Monitoraggio"
for k in ['v_g', 'v_a', 'v_t']: 
    if k not in st.session_state: st.session_state[k] = 0

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.markdown("<h3 style='text-align:center;'>REMS CONNECT</h3>", unsafe_allow_html=True)
    pwd = st.text_input("Codice", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 5. NAVIGAZIONE ---
menu_items = ["Monitoraggio", "Agenda", "Terapie", "Statistiche", "Documenti"]
icons = ["📊", "📅", "💊", "📈", "📂"]
if st.session_state.role == "admin":
    menu_items.append("Gestione"); icons.append("⚙️")

cols = st.columns(len(menu_items))
for i, item in enumerate(menu_items):
    with cols[i]:
        active = "active-btn" if st.session_state.menu == item else ""
        st.markdown(f'<div class="{active}">', unsafe_allow_html=True)
        if st.button(f"{icons[i]} {item}"):
            st.session_state.menu = item
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# --- 6. MODULI ---

if st.session_state.menu == "Monitoraggio":
    ruoli_list = ["Tutti", "Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"]
    
    for p_id, nome in db_run("SELECT * FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            vi = st.session_state.get(f"v_{p_id}", 0)
            
            # --- SEZIONE INSERIMENTO ---
            st.markdown("### Nuova Nota")
            c1, c2 = st.columns(2)
            r = c1.selectbox("Ruolo", ruoli_list[1:], key=f"r{p_id}{vi}")
            o = c2.text_input("Firma Operatore", key=f"f{p_id}{vi}")
            u = st.radio("Stato", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}{vi}", horizontal=True)
            n = st.text_area("Nota Clinica", key=f"n{p_id}{vi}")
            if st.button("SALVA NOTA", key=f"btn{p_id}"):
                if n and o:
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", 
                           (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, r, o), True)
                    st.session_state[f"v_{p_id}"] = vi + 1; st.rerun()
            
            st.divider()
            
            # --- SEZIONE RICERCA E STORICO ---
            st.markdown("### Ricerca nello Storico")
            col_f1, col_f2 = st.columns([2, 1])
            search_query = col_f1.text_input("🔍 Cerca parole chiave (es. farmaco, notte, udienza...)", key=f"search{p_id}")
            filter_role = col_f2.selectbox("Filtra per Ruolo", ruoli_list, key=f"frole{p_id}")

            # Costruzione Query di Ricerca
            query = "SELECT data, umore, nota, ruolo, op, row_id FROM eventi WHERE id=?"
            params = [p_id]
            
            if search_query:
                query += " AND nota LIKE ?"
                params.append(f"%{search_query}%")
            if filter_role != "Tutti":
                query += " AND ruolo = ?"
                params.append(filter_role)
            
            query += " ORDER BY data DESC"
            
            results = db_run(query, tuple(params))
            
            if results:
                for d, um, tx, ru, fi, rid in results:
                    cl = "card agitato" if um=="Agitato" else "card"
                    st.markdown(f'''<div class="{cl}">
                        <div class="nota-header">{d} | {ru} | {fi}</div>
                        <b>{um}</b><br>{tx}
                    </div>''', unsafe_allow_html=True)
                    if st.session_state.role == "admin":
                        if st.button(f"Elimina Nota #{rid}", key=f"del_ev_{rid}"):
                            db_run("DELETE FROM eventi WHERE row_id=?", (rid,), True); st.rerun()
            else:
                st.info("Nessuna nota trovata con questi criteri.")

elif st.session_state.menu == "Terapie":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        sel_p = st.selectbox("Seleziona Paziente", list(p_map.keys()))
        pid = p_map[sel_p]
        
        if st.session_state.role == "admin":
            with st.expander("➕ AGGIUNGI/VARIA TERAPIA"):
                f = st.text_input("Farmaco", key=f"tf{st.session_state.v_t}")
                d = st.text_input("Dosaggio/Posologia", key=f"td{st.session_state.v_t}")
                m = st.text_input("Medico Prescrittore", key=f"tm{st.session_state.v_t}")
                if st.button("REGISTRA VARIAZIONE"):
                    if f and m:
                        db_run("INSERT INTO terapie (p_id, farmaco, dosaggio, data, medico) VALUES (?,?,?,?,?)", 
                               (pid, f, d, datetime.now().strftime("%Y-%m-%d"), m), True)
                        st.session_state.v_t += 1; st.rerun()
        
        st.subheader(f"Piano Terapeutico: {sel_p}")
        for f, ds, dt, med, rid in db_run("SELECT farmaco, dosaggio, data, medico, row_id FROM terapie WHERE p_id=? ORDER BY data DESC", (pid,)):
            st.markdown(f'''<div class="card terapia-card">
                <div class="nota-header">Modifica del {dt} | Medico: {med}</div>
                💊 <b>{f}</b><br>Dosaggio: {ds}
            </div>''', unsafe_allow_html=True)

elif st.session_state.menu == "Statistiche":
    res = db_run("SELECT p.nome, e.umore, e.data FROM eventi e JOIN pazienti p ON e.id = p.id")
    if res:
        df = pd.DataFrame(res, columns=["Paziente", "Umore", "Data"])
        fig = px.pie(df, names="Umore", title="Distribuzione Umore", color="Umore", 
                     color_discrete_map={"Agitato":"#ef4444", "Stabile":"#10b981", "Cupo":"#1e3a8a", "Deflesso":"#f59e0b"})
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Dati insufficienti.")

elif st.session_state.menu == "Documenti":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        sel_p = st.selectbox("Seleziona Paziente", list(p_map.keys()))
        pid = p_map[sel_p]
        up = st.file_uploader("Carica File", type=['pdf', 'jpg', 'png'])
        if up and st.button("SALVA"):
            db_run("INSERT INTO documenti (p_id, nome_doc, file_blob, data) VALUES (?,?,?,?)", (pid, up.name, up.read(), datetime.now().strftime("%Y-%m-%d")), True)
            st.rerun()
        for n, b, d, rid in db_run("SELECT nome_doc, file_blob, data, row_id FROM documenti WHERE p_id=?", (pid,)):
            st.download_button(f"📄 {n} ({d})", b, file_name=n, key=f"dl_{rid}")

elif st.session_state.menu == "Agenda":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        with st.expander("➕ NUOVO APPUNTAMENTO"):
            va = st.session_state.v_a
            ps = st.selectbox("Paziente", list(p_map.keys()), key=f"ap{va}")
            ts = st.selectbox("Tipo", ["Udienza", "Visita", "Uscita"], key=f"at{va}")
            ds = st.date_input("Data", key=f"ad{va}")
            rs = st.text_input("Rif", key=f"ar{va}")
            if st.button("SALVA"):
                db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (p_map[ps], ts, str(ds), "", rs), True)
                st.session_state.v_a += 1; st.rerun()
    for t, d, n, r, pn, rid in db_run("SELECT a.tipo, a.d_ora, a.note, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora ASC"):
        st.markdown(f'<div class="card"><b>{t}</b> | {d}<br>Paziente: {pn} | Rif: {r}</div>', unsafe_allow_html=True)

elif st.session_state.menu == "Gestione":
    vg = st.session_state.v_g
    nn = st.text_input("Nuovo Paziente", key=f"nn{vg}")
    if st.button("AGGIUNGI"):
        if nn: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nn,), True); st.session_state.v_g += 1; st.rerun()
    with open(DB_NAME, "rb") as f:
        st.download_button("📥 BACKUP DB", f, file_name=f"rems_backup.db")
