import streamlit as st
import sqlite3
from datetime import datetime

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    .rems-h { text-align: center; color: #1e3a8a; font-family: 'Orbitron', sans-serif; font-size: 2.5rem; margin-bottom: 20px; }
    .stButton>button { height: 3.5rem; border-radius: 12px; background-color: #2563eb !important; color: white !important; font-weight: bold; width: 100%; }
    .card { padding: 12px; margin: 8px 0; border-radius: 8px; border-left: 6px solid #cbd5e1; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); color: #1e293b; }
    .agitato { background: #fee2e2 !important; border-left-color: #dc2626 !important; }
</style>
""", unsafe_allow_html=True)

# --- FUNZIONE DATABASE ---
def run_query(q, p=(), commit=False):
    conn = sqlite3.connect("rems_v3.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, op TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS agenda (p_id INTEGER, tipo TEXT, d_ora TEXT, note TEXT, rif TEXT)")
    cur.execute(q, p)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- INIZIALIZZAZIONE SESSIONE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'menu' not in st.session_state: st.session_state.menu = "📊 Monitoraggio"
if 'v_a' not in st.session_state: st.session_state.v_a = 0
if 'role' not in st.session_state: st.session_state.role = "user"

# --- SCHERMATA DI LOGIN ---
if not st.session_state.auth:
    st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)
    with st.container():
        pwd = st.text_input("Inserire Codice Identificativo", type="password")
        if st.button("ACCEDI"):
            if pwd == "rems2026":
                st.session_state.auth = True
                st.session_state.role = "user"
                st.rerun()
            elif pwd == "admin2026":
                st.session_state.auth = True
                st.session_state.role = "admin"
                st.rerun()
            else:
                st.error("Codice non valido")
    st.stop()

# --- NAVBAR ---
st.markdown('<h1 class="rems-h">REMS CONNECT</h1>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
if c1.button("📊 Monitoraggio"): st.session_state.menu = "📊 Monitoraggio"; st.rerun()
if c2.button("📅 Agenda & Uscite"): st.session_state.menu = "📅 Agenda"; st.rerun()
if c3.button("⚙️ Gestione"): st.session_state.menu = "⚙️ Gestione"; st.rerun()

# --- MODULO MONITORAGGIO ---
if st.session_state.menu == "📊 Monitoraggio":
    paz = run_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if not paz: st.info("Usa la sezione Gestione per aggiungere pazienti.")
    for p_id, nome in paz:
        with st.expander(f"👤 {nome.upper()}"):
            v_i = st.session_state.get(f"v_{p_id}", 0)
            col_a, col_b = st.columns(2)
            ruolo_sel = col_a.selectbox("Tuo Ruolo", ["OSS", "Infermiere", "Psichiatra", "Psicologo", "Educatore"], key=f"r_{p_id}_{v_i}")
            firma_sel = col_b.text_input("Tua Firma", key=f"f_{p_id}_{v_i}")
            umore_sel = st.radio("Stato Paziente", ["Stabile", "Cupo", "Deflesso", "Agitato"], key=f"u_{p_id}_{v_i}", horizontal=True)
            nota_text = st.text_area("Diario clinico", key=f"n_{p_id}_{v_i}")
            
            if st.button("REGISTRA NOTA", key=f"btn_{p_id}"):
                if nota_text and firma_sel:
                    run_query("INSERT INTO eventi VALUES (?,?,?,?,?,?)", (p_id, datetime.now().strftime("%d/%m %H:%M"), umore_sel, nota_text, ruolo_sel, firma_sel), True)
                    st.session_state[f"v_{p_id}"] = v_i + 1
                    st.rerun()
            
            st.divider()
            storico = run_query("SELECT data, umore, nota, ruolo, op FROM eventi WHERE id=? ORDER BY rowid DESC LIMIT 10", (p_id,))
            for s in storico:
                css_class = "card agitato" if s[1] == "Agitato" else "card"
                st.markdown(f'<div class="{css_class}"><small>{s[0]} | {s[3]} | {s[4]}</small><br><b>{s[1]}</b><br>{s[2]}</div>', unsafe_allow_html=True)

# --- MODULO AGENDA ---
elif st.session_state.menu == "📅 Agenda":
    paz_list = run_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if paz_list:
        p_map = {p[1]: p[0] for p in paz_list}
        with st.expander("➕ PROGRAMMA NUOVA USCITA O VISITA"):
            v_a = st.session_state.v_a
            p_sel = st.selectbox("Seleziona Paziente", list(p_map.keys()), key=f"ap_{v_a}")
            t_sel = st.selectbox("Tipo Evento", ["Visita Parenti", "Uscita Operatore", "Udienza", "Visita Medica", "Altro"], key=f"at_{v_a}")
            d_sel = st.date_input("Data", key=f"ad_{v_a}")
            o_sel = st.time_input("Ora", key=f"ao_{v_a}")
            r_sel = st.text_input("Accompagnatore / Riferimento", key=f"ar_{v_a}")
            n_sel = st.text_area("Dettagli/Note", key=f"an_{v_a}")
            
            if st.button("CONFERMA E SALVA"):
                if r_sel:
                    run_query("INSERT INTO agenda VALUES (?,?,?,?,?)", (p_map[p_sel], t_sel, f"{d_sel} {o_sel}", n_sel, r_sel), True)
                    st.session_state.v_a += 1
                    st.rerun()
    
    st.divider()
    eventi_agenda = run_query("SELECT a.tipo, a.d_ora, a.note, a.rif, p.nome FROM agenda a JOIN pazienti p ON a.p_id = p.id ORDER BY d_ora ASC")
    for ev in eventi_agenda:
        st.markdown(f'<div class="card"><b>{ev[0].upper()}</b> - {ev[1]}<br>Paziente: <b>{ev[4]}</b><br><small>Riferimento: {ev[3]} | Note: {ev[2]}</small></div>', unsafe_allow_html=True)

# --- MODULO GESTIONE ---
elif st.session_state.menu == "⚙️ Gestione":
    if st.session_state.role == "admin":
        st.subheader("Anagrafica Pazienti")
        n_p = st.text_input("Nome e Cognome nuovo paziente")
        if st.button("AGGIUNGI A DATABASE"):
            if n_p: run_query("INSERT INTO pazienti (nome) VALUES (?)", (n_p,), True); st.rerun()
        
        st.divider()
        lista_p = run_query("SELECT nome FROM pazienti ORDER BY nome")
        if lista_p:
            p_da_eliminare = st.selectbox("Seleziona paziente da rimuovere", [lp[0] for lp in lista_p])
            if st.button("ELIMINA DEFINITIVAMENTE"):
                run_query("DELETE FROM pazienti WHERE nome=?", (p_da_eliminare,), True)
                st.rerun()
    else:
        st.warning("Quest'area è riservata agli amministratori.")
