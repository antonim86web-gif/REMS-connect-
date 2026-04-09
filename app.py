import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from groq import Groq

# --- CONNESSIONI ---
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="REMS-Connect Elite", layout="wide")

# --- CSS CUSTOM (STILE PERITALE) ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    .main-card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .postit { padding: 15px; border-radius: 10px; border-left: 8px solid; margin-bottom: 10px; background: #fff; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .status-badge { padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# LOGIN BLINDATO CON DEBUG INTEGRATO
# =========================================================
if not st.session_state.get('logged_in', False):
    st.markdown('<div style="max-width:400px; margin:auto; padding-top:50px; text-align:center;">', unsafe_allow_html=True)
    st.title("🛡️ REMS-Connect Login")
    
    u_input = st.text_input("username").strip()
    p_input = st.text_input("password", type="password").strip()
    
    col1, col2 = st.columns(2)
    
    if col1.button("ACCEDI", use_container_width=True):
        try:
            # Cerchiamo l'utente (usiamo il minuscolo per sicurezza)
            res = supabase.table("utenti").select("*").execute()
            
            # Filtriamo manualmente per evitare problemi di Case Sensitivity
            user_match = next((item for item in res.data if item["username"].lower() == u_input.lower()), None)
            
            if user_match:
                if user_match["password"] == p_input:
                    st.session_state.logged_in = True
                    st.session_state.user_data = user_match
                    st.success("Accesso in corso...")
                    st.rerun()
                else:
                    st.error("❌ Password errata.")
            else:
                st.error(f"❌ Utente '{u_input}' non trovato nel database.")
                
        except Exception as e:
            st.error(f"⚠️ Errore di connessione a Supabase: {e}")

    # --- PULSANTE DI EMERGENZA (Solo se non riesci a entrare) ---
    if col2.button("CREA ADMIN ORA", use_container_width=True):
        try:
            supabase.table("utenti").insert({
                "username": "Antony", 
                "password": "admin123", 
                "ruolo": "Admin"
            }).execute()
            st.warning("✅ Utente 'Antony' con pass 'admin123' creato! Ora prova il login.")
        except:
            st.info("L'utente esiste già o c'è un errore di rete.")

    st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- SIDEBAR & UTENTE ---
    with st.sidebar:
        u_data = st.session_state.user_data
        u_name = u_data.get('username')
        ruolo_utente = str(u_data.get('ruolo', 'Nessuno')).capitalize()
        st.success(f"Operatore: {u_name}\n\nRuolo: {ruolo_utente}")
        
        voci_menu = ["📋 Monitoraggio & Diario", "💉 Modulo Equipe", "🗓️ Agenda Uscite", "🛏️ Mappa Letti", "⚙️ Pannello Admin"]
        scelta_menu = st.radio("Menu Principale", voci_menu)
        st.divider()

        # Selezione Paziente Unificata
        res_p = supabase.table("pazienti").select("id, nome").eq("stato", "ATTIVO").execute()
        lista_p = {p['nome']: p['id'] for p in res_p.data}
        nome_sel = st.selectbox("🎯 Seleziona Paziente:", ["--"] + list(lista_p.keys()))
        p_attivo = nome_sel if nome_sel != "--" else None
        id_p_attivo = lista_p.get(nome_sel) if nome_sel != "--" else None

        if st.button("🚪 Esci"):
            st.session_state.logged_in = False
            st.rerun()

    # =========================================================
    # 2. PAGINA: MODULO EQUIPE (FUNZIONI TXT)
    # =========================================================
    if scelta_menu == "💉 Modulo Equipe":
        if not p_attivo:
            st.warning("Seleziona un paziente nella Sidebar.")
        else:
            st.markdown(f"## 💉 Gestione Integrata Equipe: {p_attivo}")
            
            # Filtro Ruolo (Admin switch)
            ruoli = ["Psichiatra", "Infermiere", "Educatore", "Psicologo", "Assistente Sociale", "OSS", "OPSI"]
            ruolo_op = st.selectbox("🎯 Ruolo Operativo:", ruoli) if ruolo_utente == "Admin" else ruolo_utente
            st.divider()

            # --- 🩺 PSICHIATRA ---
            if ruolo_op == "Psichiatra":
                t1, t2 = st.tabs(["📝 Prescrizioni", "📊 Monitoraggio Real-Time"])
                with t1:
                    with st.form("psi_form"):
                        st.markdown("##### Nuova Prescrizione Farmacologica")
                        f_nome = st.text_input("Farmaco")
                        f_dose = st.text_input("Dosaggio")
                        f_fascia = st.selectbox("Fascia Oraria", ["Mattina (08:00-13:00)", "Pomeriggio (14:00-21:00)", "Al bisogno (H24)"])
                        f_note = st.text_area("Prescrizione Esami / Consegna Medica")
                        if st.form_submit_button("REGISTRA & RELAZIONE IA"):
                            supabase.table("terapie").insert({
                                "id_paziente": id_p_attivo, "farmaco": f_nome, "dose": f_dose, 
                                "fascia": f_fascia, "medico": u_name
                            }).execute()
                            st.success("Terapia archiviata.")
                with t2:
                    st.subheader("Verifica Assunzioni (Sola Lettura)")
                    log_s = supabase.table("somministrazioni").select("*").eq("id_paziente", id_p_attivo).order("timestamp", desc=True).execute()
                    if log_s.data: st.table(pd.DataFrame(log_s.data)[['timestamp', 'farmaco', 'stato', 'operatore']])
                    else: st.info("Nessuna somministrazione registrata.")

            # --- 💉 INFERMIERE ---
            elif ruolo_op == "Infermiere":
                st.subheader("🗓️ Calendario Somministrazioni")
                terapie_attive = supabase.table("terapie").select("*").eq("id_paziente", id_p_attivo).eq("attiva", True).execute()
                for t in terapie_attive.data:
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.write(f"**{t['farmaco']}** ({t['dose']}) - {t['fascia']}")
                    if c2.button(f"✅ A", key=f"a_{t['id']}"):
                        supabase.table("somministrazioni").insert({"id_terapia": t['id'], "id_paziente": id_p_attivo, "farmaco": t['farmaco'], "stato": "A", "operatore": u_name}).execute()
                        st.rerun()
                    if c3.button(f"❌ R", key=f"r_{t['id']}"):
                        motivo = st.text_input("Motivo rifiuto", key=f"not_{t['id']}")
                        if motivo:
                            supabase.table("somministrazioni").insert({"id_terapia": t['id'], "id_paziente": id_p_attivo, "farmaco": t['farmaco'], "stato": "R", "operatore": u_name, "note": motivo}).execute()
                            st.rerun()

                with st.form("inf_cons"):
                    st.text_input("📊 Parametri Vitali (PA, FC, SpO2)")
                    st.text_area("📝 Consegne Infermieristiche")
                    if st.form_submit_button("SALVA & BREAFING IA"): st.success("Dati Infermieristici salvati.")

            # --- 🎨 EDUCATORE ---
            elif ruolo_op == "Educatore":
                with st.form("edu_form"):
                    st.subheader("💰 Cassa & Tabacco")
                    col1, col2 = st.columns(2)
                    tipo = col1.selectbox("Movimento", ["Entrata", "Uscita"])
                    importo = col1.number_input("Valore (€)", step=0.50)
                    tabacco = col2.text_input("Gestione Sigarette / Tabacco")
                    causale = st.text_input("Causale Spesa")
                    st.text_area("Attività svolte / Consegne")
                    if st.form_submit_button("REGISTRA MOVIMENTO"):
                        supabase.table("cassa").insert({"id_paziente": id_p_attivo, "tipo": tipo, "importo": importo, "causale": f"{causale} | Tabacco: {tabacco}", "operatore": u_name}).execute()
                        st.success("Dato economico salvato.")

            # --- 🧺 OSS / OPSI (CONSEGNE GENERICHE) ---
            elif ruolo_op in ["OSS", "OPSI"]:
                st.subheader(f"📝 Consegne Generiche {ruolo_op}")
                nota_gen = st.text_area(f"Inserisci report di reparto ({ruolo_op})")
                if st.button("PUBBLICA NEL DIARIO DI BORDO"):
                    supabase.table("eventi").insert({"ruolo": ruolo_op, "op": u_name, "nota": nota_gen, "categoria": "Reparto"}).execute()
                    st.success("Nota di reparto pubblicata.")

    # =========================================================
    # 3. PAGINA: MAPPA LETTI (LOGICA AVANZATA)
    # =========================================================
    elif scelta_menu == "🛏️ Mappa Letti":
        st.title("🛏️ Mappa Posti Letto")
        rep_a, rep_b = st.columns(2)
        with rep_a:
            st.subheader("REPARTO A")
            for i in range(1, 5):
                st.button(f"Stanza A{i}", help="Occupata", use_container_width=True)
        with rep_b:
            st.subheader("REPARTO B")
            for i in range(1, 5):
                st.button(f"Stanza B{i}", help="Libera", use_container_width=True)

    # =========================================================
    # 4. PAGINA: MONITORAGGIO & DIARIO (STILE POST-IT)
    # =========================================================
    elif scelta_menu == "📋 Monitoraggio & Diario":
        st.title("📋 Diario Clinico Integrato")
        colori = {"Psichiatra": "#ffcccc", "Infermiere": "#cce5ff", "Educatore": "#d4edda", "Psicologo": "#fff3cd", "OSS": "#f8d7da"}
        
        logs = supabase.table("eventi").select("*").order("data", desc=True).limit(20).execute()
        for l in logs.data:
            c = colori.get(l['ruolo'], "#eeeeee")
            st.markdown(f"""
                <div class="postit" style="border-left-color: {c};">
                    <small>{l['data']} | <b>{l['op']} ({l['ruolo']})</b></small><br>
                    {l['nota']}
                </div>
            """, unsafe_allow_html=True)
