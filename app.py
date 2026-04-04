

# --- CONFIGURAZIONE INTERFACCIA ELITE PRO v28.9.2 ---
st.set_page_config(page_title="REMS Connect ELITE PRO v28.9.2", layout="wide", page_icon="🏥")

st.markdown("""
<style>
    /* 1. SIDEBAR BLU NAVY ELITE */
    [data-testid="stSidebar"] { 
        background-color: #1e3a8a !important; 
    }
    [data-testid="stSidebar"] * { 
        color: #ffffff !important; 
    }
    .sidebar-title { 
        color: #ffffff !important; 
        font-size: 1.8rem !important; 
        font-weight: 800 !important; 
        text-align: center; 
        margin-bottom: 1rem; 
        padding-top: 10px; 
        border-bottom: 2px solid #ffffff33; 
    }
    .user-logged { 
        color: #00ff00 !important; 
        font-weight: 900; 
        font-size: 1.1rem; 
        text-transform: uppercase; 
        margin-bottom: 20px; 
        text-align: center; 
    }

    /* 2. BANNER PRINCIPALE (Secton Banner) */
    .section-banner { 
        background-color: #1e3a8a; 
        color: white !important; 
        padding: 25px; 
        border-radius: 12px; 
        margin-bottom: 30px; 
        text-align: center; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.3); 
        border: 1px solid #ffffff22; 
    }

    /* 3. POST-IT DIARI CLINICI */
    .postit { 
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 12px; 
        border-left: 10px solid; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1); 
        color: #1e293b; 
        background-color: #ffffff; 
    }
    .postit-header { 
        font-weight: 800; 
        font-size: 0.85rem; 
        text-transform: uppercase; 
        margin-bottom: 5px; 
        display: flex; 
        justify-content: space-between; 
    }

    /* COLORI BORDI POST-IT PER RUOLO */
    .role-psichiatra { background-color: #fef2f2; border-color: #dc2626; } 
    .role-infermiere { background-color: #eff6ff; border-color: #2563eb; } 
    .role-educatore { background-color: #ecfdf5; border-color: #059669; } 
    .role-oss { background-color: #f8fafc; border-color: #64748b; }
    .role-psicologo { background-color: #faf5ff; border-color: #a855f7; }
    .role-sociale { background-color: #fff7ed; border-color: #f97316; }

    /* 4. TABELLA CALENDARIO E GRIGLIA */
    .cal-table { 
        width:100%; 
        border-collapse: collapse; 
        background: white; 
        border-radius: 12px; 
    }
    .cal-table th { 
        background: #f1f5f9; 
        padding: 10px; 
        color: #1e3a8a; 
        font-weight: 800; 
        border: 1px solid #e2e8f0; 
    }
    .scroll-giorni { 
        display: flex; 
        overflow-x: auto; 
        gap: 4px; 
        padding: 8px; 
        background: #fdfdfd; 
    }
    .quadratino { 
        min-width: 38px; 
        height: 50px; 
        border-radius: 4px; 
        border: 1px solid #eee; 
        display: flex; 
        flex-direction: column; 
        align-items: center; 
        justify-content: center; 
        flex-shrink: 0;
    }
    /* 5. STILE PULSANTI VERDI ELITE */
    .stButton>button {
        background-color: #22c55e !important; /* Verde brillante */
        color: white !important;
        border: none !important;
        width: 100% !important;
        font-weight: 700 !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 6px rgba(34, 197, 94, 0.2) !important;
        transition: all 0.3s ease !important;
    }

    .stButton>button:hover {
        background-color: #16a34a !important; /* Verde più scuro al passaggio del mouse */
        box-shadow: 0 6px 12px rgba(34, 197, 94, 0.4) !important;
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

        
