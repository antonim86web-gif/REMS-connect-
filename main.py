import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE & STILE ---
st.set_page_config(page_title="REMS Connect", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&family=Orbitron:wght@700&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; background-color: #f4f7f9; }
    .rems-h { text-align: center; color: #0f172a; font-family: 'Orbitron', sans-serif; font-size: 2.2rem; margin-bottom: 20px; }
    
    /* Navigazione Professionale */
    .nav-box { display: flex; gap: 10px; margin-bottom: 25px; }
    .stButton>button { 
        border-radius: 8px !important; height: 3.8rem !important; 
        background-color: white !important; color: #475569 !important;
        border: 1px solid #e2e8f0 !important; font-weight: 600 !important;
    }
    .active-btn > div > button { 
        background-color: #2563eb !important; color: white !important; 
        border: 1px solid #1d4ed8 !important; box-shadow: 0 4px 6px rgba(37,99,235,0.2);
    }
    
    /* Card Paziente */
    .card { padding: 15px; margin: 10px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .card-header { font-size: 0.85rem; color: #94a3b8; margin-bottom: 5px; border-bottom: 1px solid #f1f5f9; }
    .agitato { border-left-color: #ef4444 !important; background-color: #fef2f2 !important; }
    
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNZIONI CORE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_v6.db", check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSIONE & LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'menu' not in st.session_state: st.session_state.menu = "Monitoraggio"
if 'v_a' not in st.session_state: st.session_state.v_a = 0

if not st.session_state.auth:
    st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)
    pwd = st.text_input("Codice di Accesso", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 4. NAVIGAZIONE ---
st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f'<div class="{"active-btn" if st.session_state.menu=="Monitoraggio" else ""}">', unsafe_allow_html=True)
    if st.button("📊 MONITORAGGIO"): st.session_state.menu = "Monitoraggio"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="{"active-btn" if st.session_state.menu=="Agenda" else ""}">', unsafe_allow_html=True)
    if st.button("📅 AGENDA"): st.session_state.menu = "Agenda"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    if st.session_state.role == "admin":
        st.markdown(f'<div class="{"active-btn" if st.session_state.menu=="Gestione" else ""}">', unsafe_allow_html=True)
        if st.button("⚙️ GESTIONE"): st.session_state.menu = "Gestione"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MODULI ---
if st.session_state.menu == "Monitoraggio":
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            v_i = st.session_state.get(f"v_{p_id}", 0)
            c_a, c_b = st.columns(2)
            r = c_a.selectbox("Ruolo", ["OSS", "Infermiere", "Psichiatra", "Psicologo", "Educatore"], key=f"r{p_id}{v_i}")
            o = c_b.text_input("Firma", key=f"f{p_id}{v_i}")
            u = st.radio("Umore", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}{v_i}", horizontal=True)
            n = st.text_area("Nota clinica", key=f"n{p_id}{v_i}")
            
            if st.button("SALVA NOTA", key=f"btn{p_id}"):
                if n and o:
                    db_run("INSERT INTO eventi VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), u, n, r, o), True)
                    st.session_state[f"v_{p_id}"] = v_i + 1
                    st.rerun()
            
            st.markdown("---")
            for e in db_run("SELECT * FROM eventi WHERE id=? ORDER BY rowid DESC LIMIT 5", (p_id,)):
                cl = "card agitato" if e[2]=="Agitato" else "card"
                header = f"{e[1]} | {e[4]} | {e[5]}"
                st.markdown(f'<div class="{cl}"><div class="card-header">{header}</div><b>{e[2].upper()}</b><br>{e[3]}</div>', unsafe_allow_html=True)

elif st.session_state.menu == "Agenda":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        with st.expander("➕ NUOVO EVENTO"):
            v = st.session_state.v_a
            p_s = st.selectbox("Paziente", list(p_map.keys()), key=f"ap{v}")
            t_s = st.selectbox("Tipo", ["Visita Parenti", "Uscita", "Udienza", "Medica", "Altro"], key=f"at{v}")
            d_s = st.date_input("Data", key=f"ad{v}")
            o_s = st.time_input("Ora", key=f"ao{v}")
            r_s = st.text_input("Accompagnatore", key=f"ar{v}")
            n_s = st.text_area("Note", key=f"an{v}")
            if st.button("REGISTRA EVENTO"):
                if r_s:
                    db_run("INSERT INTO agenda VALUES (?,?,?,?,?)", (p_map[p_s], t_s, f"{d_s} {o_s}", n_s, r_s), True)
                    st.session_state.v_a += 1
                    st.rerun()
    
    for a in db_run("SELECT a.*, p.nome FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora ASC"):
        header = f"{a[2]} | {a[1].upper()}"
        st.markdown(f'<div class="card"><div class="card-header">{header}</div>Paziente: <b>{a[5]}</b><br>Rif: {a[4]}<br><small>{a[3]}</small></div>', unsafe_allow_html=True)

elif st.session_state.menu == "Gestione" and st.session_state.role == "admin":
    nn = st.text_input("Aggiungi Paziente")
    if st.button("SALVA"):
        if nn: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nn,), True); st.rerun()
    st.divider()
    pl = db_run("SELECT nome FROM pazienti")
    if pl:
        dp = st.selectbox("Elimina", [p[0] for p in pl])
        if st.button("ELIMINA"): db_run("DELETE FROM pazienti WHERE nome=?", (dp,), True); st.rerun()
