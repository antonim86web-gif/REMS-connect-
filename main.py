import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect", layout="wide")

st.markdown("<style>.stButton>button {border-radius: 8px; height: 3.5rem; font-weight: 600;} .active-btn button {background-color: #2563eb !important; color: white !important;} .card {padding: 12px; margin: 8px 0; border-radius: 10px; background: white; border-left: 5px solid #64748b; box-shadow: 0 2px 4px rgba(0,0,0,0.05);} .nota-header {font-size: 0.8rem; color: #64748b; border-bottom: 1px solid #f1f5f9; margin-bottom: 5px;} .agitato {border-left-color: #ef4444 !important; background-color: #fef2f2 !important;} #MainMenu, footer, header {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- 2. FUNZIONI DATABASE ---
def db_run(query, params=(), commit=False):
    with sqlite3.connect("rems_v10.db", check_same_thread=False) as conn:
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
for k in ['v_g', 'v_a']: 
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
    lista_ruoli = ["TUTTI", "Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"]
    filtro_ruolo = st.selectbox("Filtra diario per figura professionale:", lista_ruoli)
    
    pazienti = db_run("SELECT * FROM pazienti ORDER BY nome")
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}"):
            v_i = st.session_state.get(f"v_{p_id}", 0)
            c_a, c_b = st.columns(2)
            r = c_a.selectbox("Tuo Ruolo", lista_ruoli[1:], key=f"r{p_id}{v_i}")
            o = c_b.text_input("Firma", key=f"f{p_id}{v_i}")
            u = st.radio("Stato", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u{p_id}{v_i}", horizontal=True)
            n = st.text_area("Nota", key=f"n{p_id}{v_i}")
            if st.button("SALVA NOTA", key=f"btn{p_id}"):
                if n and o:
                    db_run("INSERT INTO eventi (id, data, umore, nota, ruolo, op) VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%Y-%m-%d %H:%M"), u, n, r, o), True)
                    st.session_state[f"v_{p_id}"] = v_i + 1
                    st.rerun()
            
            # Recupero note con filtro
            q = "SELECT data, umore, nota, ruolo, op, row_id FROM eventi WHERE id=?"
            p = [p_id]
            if filtro_ruolo != "TUTTI":
                q += " AND ruolo=?"
                p.append(filtro_ruolo)
            q += " ORDER BY data DESC"
            
            note = db_run(q, tuple(p))
            current_date = ""
            for data, umore, testo, ruolo, firma, rid in note:
                date_part = data.split(" ")[0]
                if date_part != current_date:
                    st.markdown(f"**📅 {date_part}**")
                    current_date = date_part
                
                cl = "card agitato" if umore=="Agitato" else "card"
                st.markdown(f'<div class="{cl}"><div class="nota-header">{data.split(" ")[1]} | {ruolo} | {firma}</div><b>{umore}</b><br>{testo}</div>', unsafe_allow_html=True)
                if st.session_state.role == "admin":
                    if st.button(f"Elimina Nota ID:{rid}", key=f"del_{rid}"):
                        db_run("DELETE FROM eventi WHERE row_id=?", (rid, True))
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
    
    eventi = db_run("SELECT a.tipo, a.d_ora, a.note, a.rif, p.nome, a.row_id FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora ASC")
    for tip, ora, note, rif, p_nome, rid in eventi:
        st.markdown(f'<div class="card"><b>{tip}</b> | {ora}<br>Paziente: {p_nome}<br>Rif: {rif}<br><small>{note}</small></div>', unsafe_allow_html=True)
        if st.session_state.role == "admin":
            if st.button(f"Elimina Evento ID:{rid}", key=f"del_ag_{rid}"):
                db_run("DELETE FROM agenda WHERE row_id=?", (rid, True)); st.rerun()

elif st.session_state.menu == "Gestione":
    vg = st.session_state.v_g
    st.subheader("Pazienti")
    nn = st.text_input("Nuovo Paziente", key=f"nn{vg}")
    if st.button("AGGIUNGI"):
        if nn: db_run("INSERT INTO pazienti (nome) VALUES (?)", (nn,), True); st.session_state.v_g += 1; st.rerun()
    
    pl = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
    if pl:
        st.divider()
        p_sel = st.selectbox("Modifica/Elimina", [p[1] for p in pl], key=f"ps{vg}")
        nuovo_n = st.text_input("Cambia Nome", value=p_sel, key=f"modn{vg}")
        c1, c2 = st.columns(2)
        if c1.button("AGGIORNA"):
            pid = [p[0] for p in pl if p[1] == p_sel][0]
            db_run("UPDATE pazienti SET nome=? WHERE id=?", (nuovo_n, pid), True); st.session_state.v_g += 1; st.rerun()
        if c2.button("ELIMINA"):
            db_run("DELETE FROM pazienti WHERE nome=?", (p_sel,), True); st.session_state.v_g += 1; st.rerun()
