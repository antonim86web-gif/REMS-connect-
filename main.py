import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect", layout="wide")

# CSS Semplificato per stabilità
st.markdown("<style>.stButton>button {border-radius: 8px; height: 3.5rem; font-weight: 600;} .active-btn button {background-color: #2563eb !important; color: white !important;} .card {padding: 15px; margin: 10px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);} .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;} #MainMenu, footer, header {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_v9.db", check_same_thread=False) as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT, row_id INTEGER PRIMARY KEY AUTOINCREMENT)")
        cur.execute(query, params)
        if commit: conn.commit()
        return cur.fetchall()

# --- 3. SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'menu' not in st.session_state: st.session_state.menu = "Monitoraggio"
for k in ['v_g', 'v_a', 'v_m']: 
    if k not in st.session_state: st.session_state[k] = 0

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.title("REMS CONNECT")
    pwd = st.text_input("Codice", type="password")
    if st.button("ACCEDI"):
        if pwd in ["rems2026", "admin2026"]:
            st.session_state.auth = True
            st.session_state.role = "admin" if "admin" in pwd else "user"
            st.rerun()
    st.stop()

# --- 5. NAVIGAZIONE ---
st.markdown("<h1 style='text-align:center;'>REMS CONNECT</h1>", unsafe_allow_html=True)
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

# --- 6. MODULI ---

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
                    db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), u, n, r, o), True)
                    st.session_state[f"v_{p_id}"] = v_i + 1
                    st.rerun()
            
            # Storico con opzioni Admin
            for e in db_run("SELECT data, umore, nota, ruolo, op, row_id FROM eventi WHERE id=? ORDER BY row_id DESC LIMIT 5", (p_id,)):
                cl = "card agitato" if e[1]=="Agitato" else "card"
                st.markdown(f'<div class="{cl}"><small>{e[0]} | {e[3]} | {e[4]}</small><br><b>{e[1]}</b><br>{e[2]}</div>', unsafe_allow_html=True)
                if st.session_state.role == "admin":
                    if st.button(f"Elimina Nota #{e[5]}", key=f"del_ev_{e[5]}"):
                        db_run("DELETE FROM eventi WHERE row_id=?", (e[5],), True)
                        st.rerun()

elif st.session_state.menu == "Agenda":
    paz = db_run("SELECT * FROM pazienti ORDER BY nome")
    if paz:
        p_map = {p[1]: p[0] for p in paz}
        with st.expander("➕ NUOVO EVENTO"):
            v = st.session_state.v_a
            p_s = st.selectbox("Paziente", list(p_map.keys()), key=f"ap{v}")
            t_s = st.selectbox("Tipo", ["Visita Parenti", "Uscita", "Udienza", "Medica"], key=f"at{v}")
            d_s = st.date_input("Data", key=f"ad{v}")
            o_s = st.time_input("Ora", key=f"ao{v}")
            r_s = st.text_input("Accompagnatore", key=f"ar{v}")
            n_s = st.text_area("Note", key=f"an{v}")
            if st.button("REGISTRA EVENTO"):
                if r_s:
                    db_run("INSERT INTO agenda (p_id, tipo, d_ora, note, rif) VALUES (?,?,?,?,?)", (p_map[p_s], t_s, f"{d_s} {o_s}", n_s, r_s), True)
                    st.session_state.v_a += 1
                    st.rerun()
    
    for a in db_run("SELECT a.tipo, a.d_ora, a.note, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora ASC"):
        st.markdown(f'<div class="card"><b>{a[0]}</b> | {a[1]}<br>Paziente: {a[4]}<br>Rif: {a[3]}<br><small>{a[2]}</small></div>', unsafe_allow_html=True)
        if st.session_state.role == "admin":
            if st.button(f"Elimina Evento #{a[5]}", key=f"del_ag_{a[5]}"):
                db_run("DELETE FROM agenda WHERE row_id=?", (a[5],), True)
                st.rerun()

elif st.session_state.menu == "Gestione":
    vg = st.session_state.v_g
    st.subheader("Nuovo Paziente")
    nn = st.text_input("Inserisci Nome", key=f"nn{vg}")
    if st.button("AGGIUNGI"):
        if nn:
            db_run("INSERT INTO pazienti (nome) VALUES (?)", (nn,), True)
            st.session_state.v_g += 1
            st.rerun()
    st.divider()
    pl = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pl:
        st.subheader("Modifica o Elimina Paziente")
        p_sel = st.selectbox("Scegli Paziente", [p[1] for p in pl], key=f"ps{vg}")
        nuovo_n = st.text_input("Modifica Nome", value=p_sel, key=f"modn{vg}")
        c_mod, c_del = st.columns(2)
        if c_mod.button("AGGIORNA NOME"):
            p_id = [p[0] for p in pl if p[1] == p_sel][0]
            db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo_n, p_id), True)
            st.session_state.v_g += 1
            st.rerun()
        if c_del.button("ELIMINA DEFINITIVAMENTE"):
            db_run("DELETE FROM pazienti WHERE nome=?", (p_sel,), True)
            st.session_state.v_g += 1
            st.rerun()
