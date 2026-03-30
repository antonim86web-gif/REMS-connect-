import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAZIONE ---
st.set_page_config(page_title="REMS Connect PRO", page_icon="🏥", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"] { font-size: 19px !important; background-color: #f1f5f9; }
    .stButton>button { height: 3.5rem !important; font-size: 1.1rem !important; border-radius: 12px !important; background-color: #2563eb !important; color: white !important; font-weight: bold !important; width: 100%; }
    
    /* CARD DIARIO */
    .nota-card { padding: 12px; margin-bottom: 8px; border-radius: 8px; color: #1e293b; border-left: 6px solid #cbd5e1; background-color: #f8fafc; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .nota-Psichiatra { border-left-color: #ef4444 !important; }
    .nota-Infermiere { border-left-color: #3b82f6 !important; }
    .nota-OSS { border-left-color: #8b5cf6 !important; }
    .nota-Psicologo { border-left-color: #10b981 !important; }
    .nota-Educatore { border-left-color: #f59e0b !important; }
    
    /* ALLERTA AGITATO */
    .allerta-agitato { 
        background-color: #fee2e2 !important; 
        border: 2px solid #dc2626 !important; 
        border-left: 10px solid #dc2626 !important;
        animation: blinker 2s linear infinite;
    }
    @keyframes blinker { 50% { opacity: 0.8; } }

    .stExpander { border: 1px solid #e2e8f0 !important; margin-bottom: 5px !important; }
    
    /* Stile per i Radio Buttons dello stato */
    div[data-testid="stRadio"] > div { flex-direction: row !important; gap: 10px; }
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
def db_query(query, params=(), commit=False):
    conn = sqlite3.connect("rems_connect_v1.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS pazienti (id INTEGER PRIMARY KEY, nome TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS eventi (id INTEGER PRIMARY KEY, p_id INTEGER, data TEXT, umore TEXT, nota TEXT, ruolo TEXT, operatore TEXT)")
    cur.execute(query, params)
    res = cur.fetchall()
    if commit: conn.commit()
    conn.close()
    return res

# --- 3. LOGIN ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'role' not in st.session_state: st.session_state.role = "user"

if not st.session_state.auth:
    st.title("🏥 REMS Connect")
    pwd = st.text_input("Codice Identificativo", type="password")
    if st.button("ENTRA"):
        if pwd == "rems2026":
            st.session_state.auth = True; st.session_state.role = "user"; st.rerun()
        elif pwd == "admin2026":
            st.session_state.auth = True; st.session_state.role = "admin"; st.rerun()
        else: st.error("Codice errato")
    st.stop()

# --- 4. NAVIGAZIONE ---
if 'menu_val' not in st.session_state: st.session_state.menu_val = "📊 Monitoraggio"
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("📊 Monitoraggio"): st.session_state.menu_val = "📊 Monitoraggio"; st.rerun()
with col_nav2:
    if st.session_state.role == "admin":
        if st.button("⚙️ Gestione"): st.session_state.menu_val = "⚙️ Gestione"; st.rerun()
    else: st.button("⚙️ Gestione (Protetto)", disabled=True)

menu = st.session_state.menu_val

# --- 5. MONITORAGGIO ---
if menu == "📊 Monitoraggio":
    st.title("Monitoraggio Clinico")
    pazienti = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    
    for p_id, nome in pazienti:
        with st.expander(f"👤 {nome.upper()}", expanded=False):
            if f"v_{p_id}" not in st.session_state: st.session_state[f"v_{p_id}"] = 0
            
            c1, c2 = st.columns(2)
            with c1: ruolo = st.selectbox("Ruolo:", ["Psichiatra", "Infermiere", "OSS", "Psicologo", "Educatore"], key=f"sel_{p_id}_{st.session_state[f'v_{p_id}']}")
            with c2: operatore = st.text_input("Firma:", key=f"op_{p_id}_{st.session_state[f'v_{p_id}']}")
            
            # NUOVO SISTEMA DI SELEZIONE STATO (Sostituisce lo Slider)
            st.markdown("---")
            st.write("**Seleziona Stato del Paziente:**")
            umore = st.radio(
                label="Stato attuale",
                options=["🟢 Stabile", "🟡 Cupo", "🟠 Deflesso", "🔴 Agitato"],
                index=0,
                key=f"u_{p_id}_{st.session_state[f'v_{p_id}']}",
                horizontal=True,
                label_visibility="collapsed"
            )
            
            nota = st.text_area("Nota di Turno:", key=f"n_{p_id}_{st.session_state[f'v_{p_id}']}", height=120, placeholder="Dettagli sull'andamento del turno...")
            
            if st.button("SALVA NOTA", key=f"btn_{p_id}"):
                if nota and operatore:
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    # Puliamo l'umore dall'emoji per il database
                    umore_clean = umore.split(" ")[1]
                    db_query("INSERT INTO eventi (p_id, data, umore, nota, ruolo, operatore) VALUES (?,?,?,?,?,?)", (p_id, dt, umore_clean, nota, ruolo, operatore), commit=True)
                    st.session_state[f"v_{p_id}"] += 1
                    st.rerun()
                else: st.error("Inserisci Firma e Nota!")

            st.divider()
            
            # ESPORTAZIONE E DIARIO
            eventi_raw = db_query("SELECT data, umore, ruolo, operatore, nota FROM eventi WHERE p_id=? ORDER BY data DESC", (p_id,))
            if eventi_raw:
                df = pd.DataFrame(eventi_raw, columns=['Data', 'Umore', 'Ruolo', 'Operatore', 'Nota'])
                st.download_button(label="📥 SCARICA DIARIO (CSV)", data=df.to_csv(index=False).encode('utf-8'), file_name=f"diario_{nome}.csv", mime='text/csv')

                diario_per_data = {}
                for e in eventi_raw:
                    try:
                        nice_date = datetime.strptime(e[0].split(" ")[0], "%Y-%m-%d").strftime("%d/%m/%Y")
                        time_part = e[0].split(" ")[1]
                    except:
                        nice_date = e[0].split(" ")[0]; time_part = e[0].split(" ")[1] if " " in e[0] else ""
                    if nice_date not in diario_per_data: diario_per_data[nice_date] = []
                    diario_per_data[nice_date].append({"ora": time_part, "umore": e[1], "ruolo": e[2], "firma": e[3], "testo": e[4]})

                for data_label, note_del_giorno in diario_per_data.items():
                    with st.expander(f"📅 Diario del {data_label}"):
                        for n in note_del_giorno:
                            classe_agitato = "allerta-agitato" if n['umore'] == "Agitato" else ""
                            r_style = f"nota-{n['ruolo'].replace(' ', '')}"
                            st.markdown(f"""
                            <div class="nota-card {r_style} {classe_agitato}">
                                <small><b>{n['ora']}</b> | <b>{n['ruolo'].upper()}</b> | {n['firma']}</small><br>
                                <b>Stato: {n['umore']}</b><br>
                                <div style="margin-top:5px; white-space: pre-wrap;">{n['testo']}</div>
                            </div>
                            """, unsafe_allow_html=True)

# --- 6. GESTIONE (SOLO ADMIN) ---
elif menu == "⚙️ Gestione" and st.session_state.role == "admin":
    st.title("Area Amministratore")
    with st.expander("➕ AGGIUNGI NUOVO"):
        nuovo = st.text_input("Nome e Cognome")
        if st.button("SALVA"):
            if nuovo: db_query("INSERT INTO pazienti (nome) VALUES (?)", (nuovo,), commit=True); st.rerun()
    p_list = db_query("SELECT id, nome FROM pazienti ORDER BY nome")
    if p_list:
        with st.expander("✏️ MODIFICA"):
            p_da_mod = st.selectbox("Seleziona", [p[1] for p in p_list], key="sm")
            nuovo_n = st.text_input("Nuovo Nome", value=p_da_mod)
            if st.button("AGGIORNA"): db_query("UPDATE pazienti SET nome=? WHERE nome=?", (nuovo_n, p_da_mod), commit=True); st.rerun()
        with st.expander("🗑️ ELIMINA"):
            p_del = st.selectbox("Seleziona", [p[1] for p in p_list], key="sd")
            if st.button("ELIMINA DEFINITIVAMENTE"): db_query("DELETE FROM pazienti WHERE nome=?", (p_del,), commit=True); st.rerun()
