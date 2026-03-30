import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect", layout="wide")

st.markdown("""
<style>
    .stButton>button {
        width: 100%; border-radius: 8px; height: 45px !important; 
        background-color: white !important; color: #1e3a8a !important; 
        border: 1px solid #e2e8f0; font-size: 0.9rem !important; font-weight: 600;
    }
    .active-btn button {
        background-color: #1e3a8a !important; color: white !important; 
        border: 1px solid #1e3a8a !important;
    }
    .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    .nota-header {font-size: 0.75rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;}
    .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;}
    #MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE (NOME DEFINITIVO) ---
DB_NAME = "rems_connect_data.db"

def db_run(query, params=(), commit=False):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cur = conn.cursor()
        # Inizializzazione tabelle
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'menu' not in st.session_state: st.session_state.menu = "Monitoraggio"
if 'v_g' not in st.session_state: st.session_state.v_g = 0
if 'v_a' not in st.session_state: st.session_state.v_a = 0

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
st.markdown("<h4 style='text-align:center; color:#1e3a8a;'>REMS CONNECT</h4>", unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)

cls_mon = "active-btn" if st.session_state.menu == "Monitoraggio" else ""
cls_age = "active-btn" if st.session_state.menu == "Agenda" else ""
cls_ges = "active-btn" if st.session_state.menu == "Gestione" else ""

with c1:
    st.markdown(f'<div class="{cls_mon}">', unsafe_allow_html=True)
    if st.button("📊 Monitoraggio"):
        st.session_state.menu = "Monitoraggio"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown(f'<div class="{cls_age}">', unsafe_allow_html=True)
    if st.button("📅 Agenda"):
        st.session_state.menu = "Agenda"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    if st.session_state.role == "admin":
        st.markdown(f'<div class="{cls_ges}">', unsafe_allow_html=True)
        if st.button("⚙️ Gestione"):
            st.session_state.menu = "Gestione"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. MODULI ---
if st.session_state.menu == "Monitoraggio":
    ruoli = ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"]
    filtro = st.selectbox("Filtra per figura:", ["TUTTI"] + ruoli)
    for p_id, nome in db_run("SELECT * FROM pazienti ORDER BY nome"):
        with st.expander(f"👤 {nome.upper()}"):
            vi = st.session_state.get(f"v_{p_id}", 0)
            c_a, c_b = st.columns(2)
            r = c_a.selectbox("Ruolo", ruoli, key=f"r{p_id}{vi}")
            o = c_b.text_input("Firma", key=f"f{p_id}{vi}")
            u = st.radio("Stato", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}{vi}", horizontal=True)
            n = st.text_area("Nota", key=f"n{p_id}{vi}")
            if st.button("SALVA NOTA", key=f"btn{p_id}"):
                if n and o:
                    db_run("INSERT INTO eventi (id,data,umore,nota,ruolo,op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, r, o), True)
                    st.session_state[f"v_{p_id}"] = vi + 1
                    st.rerun()
            q = "SELECT data, umore, nota, ruolo, op, row_id FROM eventi WHERE id=?"
            pa = [p_id]
            if filtro != "TUTTI": q += " AND ruolo=?"; pa.append(filtro)
            for d, um, tx, ru, fi, rid in db_run(q + " ORDER BY data DESC", tuple(pa)):
                cl = "card agitato" if um=="Agitato" else "card"
                st.markdown(f'<div class="{cl}"><div class="nota-header">{d} | {ru} | {fi}</div><b>{um}</b><br>{tx}</div>', unsafe_allow_html=True)
                if st.session_state.role == "admin":
                    if st.button(f"Elimina Nota #{rid}", key=f"del_ev_{rid}"):
                        db_run("DELETE FROM eventi WHERE row_id=?", (rid,), True); st.rerun()

elif st.session_state.menu == "Agenda":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        with st.expander("➕ NUOVO EVENTO"):
            va = st.session_state.v_a
            ps = st.selectbox("Paziente", list(p_map.keys()), key=f"ap{va}")
            ts = st.selectbox("Tipo", ["Visita Parenti", "Uscita", "Udienza", "Medica"], key=f"at{va}")
            ds, os = st.date_input("Data", key=f"ad{va}"), st.time_input("Ora", key=f"ao{va}")
            rs, ns = st.text_input("Accompagnatore", key=f"ar{va}"), st.text_area("Note", key=f"an{va}")
            if st.button("REGISTRA"):
                if rs:
                    db_run("INSERT INTO agenda (p_id,tipo,d_ora,note,rif) VALUES (?,?,?,?,?)", (p_map[ps], ts, f"{ds} {os}", ns, rs), True)
                    st.session_state.v_a += 1; st.rerun()
    for t, d, n, r, pn, rid in db_run("SELECT a.tipo, a.d_ora, a.note, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora ASC"):
        st.markdown(f'<div class="card"><b>{t}</b> | {d}<br>Paziente: {pn}<br>Rif: {r}<br><small>{n}</small></div>', unsafe_allow_html=True)
        if st.session_state.role == "admin":
            if st.button(f"Elimina ID:{rid}", key=f"del_ag_{rid}"): db_run("DELETE FROM agenda WHERE row_id=?", (rid,), True); st.rerun()

elif st.session_state.menu == "Gestione":
    vg = st.session_state.v_g
    nn = st.text_input("Nuovo Paziente", key=f"nn{vg}")
    if st.button("AGGIUNGI"):
        if nn: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nn,), True); st.session_state.v_g += 1; st.rerun()
    pl = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pl:
        st.divider()
        psel = st.selectbox("Paziente", [p[1] for p in pl], key=f"ps{vg}")
        n_n = st.text_input("Nuovo Nome", value=psel, key=f"modn{vg}")
        c1, c2 = st.columns(2)
        if c1.button("AGGIORNA"):
            pid = [p[0] for p in pl if p[1] == psel][0]
            db_run("UPDATE pazienti SET nome=? WHERE id=?", (n_n, pid), True); st.session_state.v_g += 1; st.rerun()
        if c2.button("ELIMINA"): db_run("DELETE FROM pazienti WHERE nome=?", (psel,), True); st.session_state.v_g += 1; st.rerun()
