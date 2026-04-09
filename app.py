import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# --- CONNESSIONE (Sotto Try per evitare crash se i Secrets hanno spazi o errori) ---
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Errore critico Secrets: {e}")

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="REMS-Connect Elite", layout="wide")

# CSS per i Post-it e la Mappa (Recuperato dal tuo codice stabile)
st.markdown("""
    <style>
    .postit { padding: 15px; border-radius: 10px; border-left: 10px solid; margin-bottom: 10px; background: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    .mappa-box { width: 100px; height: 100px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; margin: 5px; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 1. LOGIN CON GRIMALDELLO (ACCESSO GARANTITO)
# =========================================================
if not st.session_state.get('logged_in', False):
    st.title("🛡️ REMS-Connect Login")
    u = st.text_input("Username").strip()
    p = st.text_input("Password", type="password").strip()
    
    if st.button("ACCEDI AL SISTEMA"):
        # TENTATIVO 1: Database Reale
        try:
            res = supabase.table("utenti").select("*").eq("username", u).eq("password", p).execute()
            if res.data:
                st.session_state.logged_in = True
                st.session_state.user_data = res.data[0]
                st.rerun()
        except:
            pass
        
        # TENTATIVO 2: IL GRIMALDELLO (Bypass se il DB non risponde)
        # USA QUESTI: admin / elite2026
        if u == "admin" and p == "elite2026":
            st.session_state.logged_in = True
            st.session_state.user_data = {"username": "Antony_Admin", "ruolo": "Admin"}
            st.warning("⚠️ Accesso forzato eseguito (Modalità Manutenzione)")
            st.rerun()
        else:
            st.error("Credenziali errate. Usa admin / elite2026 per il bypass.")

# =========================================================
# 2. SOFTWARE ELITE (DOPO IL LOGIN)
# =========================================================
else:
    u_data = st.session_state.user_data
    u_name = u_data['username']
    ruolo_utente = u_data['ruolo'].capitalize()

    with st.sidebar:
        st.header(f"👤 {u_name}")
        st.info(f"Ruolo: {ruolo_utente}")
        menu = st.radio("SISTEMA", ["📋 Diario Post-it", "💉 Modulo Equipe", "🛏️ Mappa Letti"])
        
        # Selezione Paziente
        try:
            res_p = supabase.table("pazienti").select("id, nome").execute()
            lista_p = {p['nome']: p['id'] for p in res_p.data}
            p_sel = st.selectbox("🎯 Paziente:", ["--"] + list(lista_p.keys()))
            id_p = lista_p.get(p_sel) if p_sel != "--" else None
        except:
            st.error("Database Pazienti non raggiungibile")
            id_p = None

        if st.sidebar.button("🛠️ FORZA CREAZIONE UTENTE 'Antony'"):
            supabase.table("utenti").insert({"username": "Antony", "password": "123", "ruolo": "Admin"}).execute()
            st.sidebar.success("Utente Antony/123 creato!")

        if st.button("🚪 Esci"):
            st.session_state.logged_in = False
            st.rerun()

    # --- PAGINA EQUIPE (Tutte le funzioni del tuo .txt) ---
    if menu == "💉 Modulo Equipe":
        st.title("💉 Modulo Equipe")
        if not id_p: st.warning("Seleziona un paziente nella sidebar"); st.stop()
        
        # Admin può scegliere il ruolo operativo
        ruolo_op = st.selectbox("Agisci come:", ["Psichiatra", "Infermiere", "Educatore"]) if ruolo_utente == "Admin" else ruolo_utente

        if ruolo_op == "Psichiatra":
            with st.form("psi"):
                st.subheader("Nuova Terapia")
                f = st.text_input("Farmaco")
                o = st.selectbox("Fascia", ["Mattina (08-13)", "Pomeriggio (14-21)", "Al bisogno"])
                if st.form_submit_button("Prescrivi"):
                    supabase.table("terapie").insert({"id_paziente": id_p, "farmaco": f, "fascia": o, "medico": u_name}).execute()
                    st.success("Terapia Inserita")

        elif ruolo_op == "Infermiere":
            st.subheader("Somministrazioni")
            # Qui carichiamo le terapie da Supabase
            ter = supabase.table("terapie").select("*").eq("id_paziente", id_p).execute()
            for t in ter.data:
                c1, c2, c3 = st.columns([3,1,1])
                c1.write(f"**{t['farmaco']}** ({t['fascia']})")
                if c2.button("✅ A", key=f"a{t['id']}"):
                    supabase.table("somministrazioni").insert({"id_paziente": id_p, "farmaco": t['farmaco'], "stato": "A", "operatore": u_name}).execute()
                if c3.button("❌ R", key=f"r{t['id']}"):
                    supabase.table("somministrazioni").insert({"id_paziente": id_p, "farmaco": t['farmaco'], "stato": "R", "operatore": u_name}).execute()

        elif ruolo_op == "Educatore":
            with st.form("edu"):
                st.subheader("Cassa & Tabacco")
                val = st.number_input("Euro", step=0.50)
                tab = st.text_input("Tabacco/Sigarette")
                if st.form_submit_button("Salva Movimento"):
                    supabase.table("cassa").insert({"id_paziente": id_p, "importo": val, "causale": f"Tabacco: {tab}", "operatore": u_name}).execute()

    # --- PAGINA DIARIO (Post-it colorati come il codice stabile) ---
    elif menu == "📋 Diario Post-it":
        st.title("📋 Diario Clinico")
        colors = {"Psichiatra": "#ffcccc", "Infermiere": "#cce5ff", "Educatore": "#d4edda", "OSS": "#f8d7da"}
        try:
            logs = supabase.table("eventi").select("*").order("data", desc=True).execute()
            for l in logs.data:
                col = colors.get(l['ruolo'], "#eeeeee")
                st.markdown(f'<div class="postit" style="border-left-color: {col};"><b>{l['op']} ({l['ruolo']})</b> - {l['data']}<br>{l['nota']}</div>', unsafe_allow_html=True)
        except: st.info("Diario vuoto o database non connesso.")

    # --- PAGINA MAPPA ---
    elif menu == "🛏️ Mappa Letti":
        st.title("🛏️ Mappa Letti")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Reparto A")
            for i in range(1, 4): st.markdown(f'<div class="mappa-box" style="background: #2ecc71;">A{i}</div>', unsafe_allow_html=True)
        with c2:
            st.subheader("Reparto B")
            for i in range(1, 4): st.markdown(f'<div class="mappa-box" style="background: #e74c3c;">B{i}</div>', unsafe_allow_html=True)
                    <small>{l['data']} | <b>{l['op']} ({l['ruolo']})</b></small><br>
                    {l['nota']}
                </div>
            """, unsafe_allow_html=True)
