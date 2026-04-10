import re
import calendar
import hashlib
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from fpdf import FPDF
from groq import Groq
from supabase import create_client

# --- Streamlit: prima chiamata deve essere set_page_config ---
st.set_page_config(
    page_title="REMS Connect ELITE PRO v28.9.2",
    layout="wide",
    page_icon="🏥",
)

# --- Session state ---
for key, default in (
    ("autenticato", False),
    ("ruolo", None),
    ("user", None),
    ("user_session", None),
    ("cal_month", None),
    ("cal_year", None),
):
    if key not in st.session_state:
        st.session_state[key] = default

# --- Supabase ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- Groq (opzionale) ---
try:
    _groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    _groq_client = None


def get_italy_time():
    return datetime.now(ZoneInfo("Europe/Rome"))


def get_now_it():
    return get_italy_time()


def scrivi_log(azione, dettagli):
    """Audit log: no-op se tabella non disponibile."""
    try:
        u = st.session_state.get("user_session") or {}
        utente = u.get("username") or u.get("user") or "SISTEMA"
        supabase.table("logs_sistema").insert(
            {
                "data_ora": get_italy_time().strftime("%Y-%m-%d %H:%M:%S"),
                "utente": utente,
                "azione": azione,
                "dettaglio": str(dettagli)[:2000],
            }
        ).execute()
    except Exception:
        pass


def _limit_from_query(qu: str) -> Optional[int]:
    m = re.search(r"LIMIT\s+(\d+)", qu, re.I)
    return int(m.group(1)) if m else None


def _as_01(v):
    if v is True or v == 1:
        return 1
    if v is False or v == 0:
        return 0
    return 1 if v else 0


def _coerce_patient_id(p_id):
    """Allinea il tipo di p_id a quello usato in Supabase (int se numerico)."""
    if p_id is None:
        return p_id
    if isinstance(p_id, int):
        return p_id
    if isinstance(p_id, str) and p_id.strip().isdigit():
        return int(p_id.strip())
    return p_id


def insert_terapia_prescrizione(p_id, farmaco, dose, mattina, pomeriggio, al_bisogno):
    """
    Inserisce una riga in terapie e restituisce (ok, messaggio_errore).
    Usa interi 0/1 per i flag (compatibile con colonne INTEGER su Postgres).
    """
    row = {
        "p_id": _coerce_patient_id(p_id),
        "farmaco": (farmaco or "").strip(),
        "dose": (dose or "").strip() or "-",
        "mat_nuovo": 1 if mattina else 0,
        "pom_nuovo": 1 if pomeriggio else 0,
        "al_bisogno": 1 if al_bisogno else 0,
    }
    if not row["farmaco"]:
        return False, "Inserisci il nome del farmaco."
    try:
        supabase.table("terapie").insert(row).execute()
        return True, None
    except Exception as e:
        err = str(e)
        if "row-level security" in err.lower() or "42501" in err:
            return (
                False,
                "Permesso negato (RLS su Supabase): abilita INSERT sulla tabella "
                "`terapie` per la chiave usata dall'app, oppure usa la Service Role Key solo lato server.",
            )
        if "column" in err.lower() and "does not exist" in err.lower():
            return (
                False,
                f"Schema DB non allineato: {err}. Verifica i nomi delle colonne in `terapie` (es. p_id, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno).",
            )
        return False, err


def db_run(query, params=None, _commit=False, *, params_tuple=None):
    """Adattatore SQL-stile → Supabase PostgREST. Il terzo argomento (commit) è ignorato, solo compatibilità."""
    if params_tuple is not None:
        params = params_tuple
    params = tuple(params) if params is not None else ()
    q = " ".join(query.split())
    qu = q.upper()

    try:
        # --- SELECT: scadenze oggi ---
        if "FROM SCADENZE" in qu and "COUNT" in qu:
            today = get_italy_time().strftime("%Y-%m-%d")
            r = supabase.table("scadenze").select("id").eq("data", today).execute()
            return [(len(r.data or []),)]

        # --- SELECT: stanze ---
        if "FROM STANZE" in qu:
            r = (
                supabase.table("stanze")
                .select("id,reparto,tipo")
                .order("id")
                .execute()
            )
            return [
                (x["id"], x.get("reparto"), x.get("tipo"))
                for x in (r.data or [])
            ]

        # --- SELECT: pazienti + assegnazioni (LEFT JOIN simulato) ---
        if "LEFT JOIN ASSEGNAZIONI" in qu or (
            "FROM PAZIENTI" in qu and "ASSEGNAZIONI" in qu
        ):
            paz = (
                supabase.table("pazienti")
                .select("id,nome,stato")
                .eq("stato", "ATTIVO")
                .execute()
            )
            ass = supabase.table("assegnazioni").select("p_id,stanza_id,letto").execute()
            amap = {a["p_id"]: a for a in (ass.data or [])}
            rows = []
            for p in paz.data or []:
                a = amap.get(p["id"])
                if a:
                    rows.append(
                        (p["id"], p["nome"], a["stanza_id"], a["letto"])
                    )
                else:
                    rows.append((p["id"], p["nome"], None, None))
            return rows

        # --- SELECT: appuntamenti JOIN pazienti ---
        if "FROM APPUNTAMENTI" in qu and "JOIN" in qu and "PAZIENTI" in qu:
            paz_rows = supabase.table("pazienti").select("id,nome").execute()
            nomi = {p["id"]: p["nome"] for p in (paz_rows.data or [])}
            if "BETWEEN" in qu and len(params) >= 2:
                r = (
                    supabase.table("appuntamenti")
                    .select("*")
                    .eq("stato", "PROGRAMMATO")
                    .gte("data", str(params[0]))
                    .lte("data", str(params[1]))
                    .execute()
                )
                out = []
                for a in r.data or []:
                    out.append(
                        (
                            a["data"],
                            nomi.get(a["p_id"], "?"),
                            a.get("ora"),
                            a.get("tipo_evento"),
                            a.get("mezzo"),
                            a.get("nota"),
                            a.get("accompagnatore"),
                        )
                    )
                return out
            if "DATA >=" in qu.replace(" ", "") or (
                ">=" in qu and len(params) >= 1
            ):
                r = (
                    supabase.table("appuntamenti")
                    .select("*")
                    .eq("stato", "PROGRAMMATO")
                    .gte("data", str(params[0]))
                    .order("data")
                    .order("ora")
                    .execute()
                )
                out = []
                for a in r.data or []:
                    out.append(
                        (
                            a.get("id_u"),
                            a["data"],
                            a.get("ora"),
                            nomi.get(a["p_id"], "?"),
                            a.get("tipo_evento"),
                        )
                    )
                return out

        # --- SELECT: eventi + join pazienti (diario admin) ---
        if "FROM EVENTI" in qu and "JOIN" in qu and "PAZIENTI" in qu:
            lim = _limit_from_query(qu) or 100
            evs = (
                supabase.table("eventi")
                .select("*")
                .order("id_u", desc=True)
                .limit(500)
                .execute()
            )
            paz_rows = supabase.table("pazienti").select("id,nome").execute()
            nomi = {p["id"]: p["nome"] for p in (paz_rows.data or [])}
            rows = []
            for e in evs.data or []:
                nome_p = nomi.get(e.get("id"))
                if params and nome_p != params[0]:
                    continue
                rows.append(
                    (
                        e.get("data"),
                        e.get("ruolo"),
                        e.get("op"),
                        e.get("nota"),
                        nome_p,
                        e.get("id_u"),
                    )
                )
            return rows[:lim]

        # --- SELECT: lista utenti (admin / compat) ---
        if "FROM UTENTI" in qu and "SELECT" in qu and "JOIN" not in qu:
            r = (
                supabase.table("utenti")
                .select("username,nome,cognome,qualifica,ruolo")
                .execute()
            )
            out = []
            for row in r.data or []:
                uname = row.get("username") or row.get("user")
                qual = row.get("qualifica") or row.get("ruolo")
                out.append(
                    (
                        uname,
                        row.get("nome"),
                        row.get("cognome"),
                        qual,
                    )
                )
            return out

        # --- SELECT: pazienti (varianti) ---
        if "FROM PAZIENTI" in qu and "JOIN" not in qu:
            tb = supabase.table("pazienti").select("id,nome,stato")
            if "STATO='ATTIVO'" in qu.replace(" ", "") or (
                "STATO" in qu and "ATTIVO" in qu
            ):
                tb = tb.eq("stato", "ATTIVO")
            elif "DIMESSO" in qu:
                tb = tb.eq("stato", "DIMESSO")
            if "ORDER BY NOME" in qu.replace(" ", ""):
                tb = tb.order("nome")
            r = tb.execute()
            if "SELECT *" in qu or "SELECT*" in qu.replace(" ", ""):
                return r.data or []
            return [(x["id"], x["nome"]) for x in (r.data or [])]

        # --- SELECT: terapie ---
        if "FROM TERAPIE" in qu:
            r = (
                supabase.table("terapie")
                .select("*")
                .eq("p_id", params[0])
                .execute()
            )
            rows = []
            for t in r.data or []:
                rows.append(
                    (
                        t.get("id_u"),
                        t.get("farmaco"),
                        t.get("dose"),
                        _as_01(t.get("mat_nuovo")),
                        _as_01(t.get("pom_nuovo")),
                        _as_01(t.get("al_bisogno")),
                    )
                )
            return rows

        # --- SELECT: cassa ---
        if "FROM CASSA" in qu:
            r = (
                supabase.table("cassa")
                .select("importo,tipo")
                .eq("p_id", params[0])
                .execute()
            )
            return [
                (x.get("importo", 0), x.get("tipo"))
                for x in (r.data or [])
            ]

        # --- SELECT: logs ---
        if "FROM LOGS_SISTEMA" in qu:
            lim = _limit_from_query(qu) or 200
            r = (
                supabase.table("logs_sistema")
                .select("data_ora,utente,azione,dettaglio,id_log")
                .order("id_log", desc=True)
                .limit(lim)
                .execute()
            )
            return [
                (
                    x.get("data_ora"),
                    x.get("utente"),
                    x.get("azione"),
                    x.get("dettaglio"),
                )
                for x in (r.data or [])
            ]

        # --- SELECT: eventi (per paziente, filtri in Python) ---
        if "FROM EVENTI" in qu and "JOIN" not in qu:
            pid = params[0] if params else None
            if pid is None:
                return []
            r = (
                supabase.table("eventi")
                .select("*")
                .eq("id", pid)
                .order("id_u", desc=True)
                .execute()
            )
            rows_raw = r.data or []
            lim = _limit_from_query(qu)

            def filt(row):
                if "ESITO='A'" in qu or "ESITO='R'" in qu:
                    es = row.get("esito")
                    n = row.get("nota") or ""
                    if es in ("A", "R"):
                        return True
                    return n.startswith("✔️") or n.startswith("❌")
                if "💓 PARAMETRI" in qu or "PARAMETRI:%" in qu:
                    return (row.get("nota") or "").startswith("💓 Parametri:")
                if "NOTA LIKE '%💊%'" in qu or "💊" in qu and "NOTA LIKE" in qu:
                    n = row.get("nota") or ""
                    op = row.get("op") or ""
                    return (
                        "💊" in n
                        or "✔️" in n
                        or "❌" in n
                        or "SOMMINISTRAZIONE" in op.upper()
                    )
                if "INFERMIERE" in qu and "RUOLO" in qu:
                    ru = (row.get("ruolo") or "").lower()
                    return "infermiere" in ru or row.get("ruolo") == "Infermiere"
                return True

            rows_f = [x for x in rows_raw if filt(x)]

            # Filtri dinamici monitoraggio (params dopo id)
            pi = 1
            if "DATA LIKE" in qu and len(params) > pi:
                pat = params[pi].strip("%")
                rows_f = [x for x in rows_f if pat in (x.get("data") or "")]
                pi += 1
            if "OP LIKE" in qu and len(params) > pi:
                pat = params[pi].strip("%")
                rows_f = [
                    x
                    for x in rows_f
                    if pat.lower() in (x.get("op") or "").lower()
                    or pat.lower() in (x.get("ruolo") or "").lower()
                ]

            # LIKE multipli (firme terapia): id + 3 pattern su nota/data
            if len(params) >= 4 and "NOTA LIKE" in qu:
                p1, p2, p3 = (
                    params[1].strip("%"),
                    params[2].strip("%"),
                    params[3].strip("%"),
                )
                rows_f = [
                    x
                    for x in rows_f
                    if p1 in (x.get("nota") or "")
                    and p2 in (x.get("nota") or "")
                    and p3 in (x.get("data") or "")
                ]

            if lim:
                rows_f = rows_f[:lim]

            # Formato colonne richiesto dalla query
            if "DATA, NOTA, OP" in qu.replace(" ", "") or (
                "SELECT DATA, NOTA, OP" in qu.replace("\n", " ").upper()
            ):
                return [
                    (x.get("data"), x.get("nota"), x.get("op"))
                    for x in rows_f
                ]
            if "DATA, ESITO, OP" in qu.replace(" ", ""):
                return [
                    (x.get("data"), x.get("esito"), x.get("op"))
                    for x in rows_f
                ]
            if re.search(
                r"SELECT\s+DATA,\s*NOTA\s+FROM\s+EVENTI", qu, re.I
            ):
                return [
                    (x.get("data"), x.get("nota")) for x in rows_f
                ]
            if "DATA, OP, NOTA" in qu.replace(" ", ""):
                return [
                    (x.get("data"), x.get("op"), x.get("nota"))
                    for x in rows_f
                ]
            return [
                (
                    x.get("data"),
                    x.get("ruolo"),
                    x.get("op"),
                    x.get("nota"),
                )
                for x in rows_f
            ]

        # --- INSERT eventi ---
        if qu.startswith("INSERT INTO EVENTI"):
            if len(params) >= 6:
                row = {
                    "id": params[0],
                    "data": params[1],
                    "nota": params[2],
                    "ruolo": params[3],
                    "op": params[4],
                    "esito": params[5],
                }
            else:
                row = {
                    "id": params[0],
                    "data": params[1],
                    "nota": params[2],
                    "ruolo": params[3],
                    "op": params[4],
                }
            supabase.table("eventi").insert(row).execute()
            return []

        # --- INSERT terapie ---
        if qu.startswith("INSERT INTO TERAPIE"):
            ok, _err = insert_terapia_prescrizione(
                params[0],
                params[1],
                params[2],
                bool(params[3]),
                bool(params[4]),
                bool(params[5]),
            )
            return []

        # --- INSERT pazienti ---
        if qu.startswith("INSERT INTO PAZIENTI"):
            supabase.table("pazienti").insert(
                {"nome": params[0], "stato": "ATTIVO"}
            ).execute()
            return []

        # --- INSERT assegnazioni ---
        if qu.startswith("INSERT INTO ASSEGNAZIONI"):
            supabase.table("assegnazioni").insert(
                {
                    "p_id": params[0],
                    "stanza_id": params[1],
                    "letto": int(params[2]),
                    "data_ass": params[3],
                }
            ).execute()
            return []

        # --- INSERT appuntamenti ---
        if qu.startswith("INSERT INTO APPUNTAMENTI"):
            supabase.table("appuntamenti").insert(
                {
                    "p_id": params[0],
                    "data": str(params[1]),
                    "ora": params[2],
                    "nota": params[3],
                    "stato": "PROGRAMMATO",
                    "autore": params[4],
                    "tipo_evento": params[5],
                    "mezzo": params[6],
                    "accompagnatore": params[7],
                }
            ).execute()
            return []

        # --- INSERT cassa ---
        if qu.startswith("INSERT INTO CASSA"):
            supabase.table("cassa").insert(
                {
                    "p_id": params[0],
                    "data": params[1],
                    "causale": params[2],
                    "importo": float(params[3]),
                    "tipo": params[4],
                    "op": params[5],
                }
            ).execute()
            return []

        # --- DELETE ---
        if qu.startswith("DELETE FROM ASSEGNAZIONI"):
            supabase.table("assegnazioni").delete().eq("p_id", params[0]).execute()
            return []
        if qu.startswith("DELETE FROM TERAPIE"):
            supabase.table("terapie").delete().eq("id_u", params[0]).execute()
            return []
        if qu.startswith("DELETE FROM EVENTI"):
            supabase.table("eventi").delete().eq("id_u", params[0]).execute()
            return []
        if qu.startswith("DELETE FROM APPUNTAMENTI"):
            supabase.table("appuntamenti").delete().eq("id_u", params[0]).execute()
            return []
        if qu.startswith("DELETE FROM PAZIENTI"):
            supabase.table("pazienti").delete().eq("id", params[0]).execute()
            return []
        if qu.startswith("DELETE FROM UTENTI"):
            supabase.table("utenti").delete().eq("username", params[0]).execute()
            return []

        # --- UPDATE ---
        if "UPDATE PAZIENTI" in qu and "DIMESSO" in qu:
            supabase.table("pazienti").update({"stato": "DIMESSO"}).eq(
                "id", params[0]
            ).execute()
            return []
        if "UPDATE PAZIENTI" in qu and "ATTIVO" in qu:
            supabase.table("pazienti").update({"stato": "ATTIVO"}).eq(
                "id", params[0]
            ).execute()
            return []
        if "UPDATE APPUNTAMENTI" in qu and "COMPLETATO" in qu:
            supabase.table("appuntamenti").update({"stato": "COMPLETATO"}).eq(
                "id_u", params[0]
            ).execute()
            return []

    except Exception:
        return []

    return []


def genera_pdf_clinico(p_nome, dati_clinici, tipo_rep="Report"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "REMS-CONNECT - REPORT CLINICO", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, f"Paziente: {p_nome}", ln=True)
    pdf.ln(10)
    for data, op, nota in dati_clinici:
        nota_p = str(nota).encode("latin-1", "replace").decode("latin-1")
        op_p = str(op).encode("latin-1", "replace").decode("latin-1")
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 7, f"Data: {data} | Op: {op_p}", ln=True, fill=True)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 7, nota_p)
        pdf.ln(4)
    out = pdf.output()
    return bytes(out)


def genera_relazione_ia(p_id, testo_utente, _giorni=1):
    if _groq_client is None:
        return "Configura GROQ_API_KEY in Streamlit secrets per abilitare l'IA."
    try:
        completion = _groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Sei un esperto clinico REMS. Genera relazioni formali e concise.",
                },
                {
                    "role": "user",
                    "content": f"ID paziente: {p_id}. Contenuto:\n{texto_utente}",
                },
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Errore Groq: {str(e)}"


def render_postits(reparto_filtro):
    st.caption(f"Post-it / avvisi (contesto: {reparto_filtro})")


# --- CSS ---
st.markdown(
    """
<style>
    [data-testid="stSidebar"] { background-color: #1e3a8a !important; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    .sidebar-title { color: #ffffff !important; font-size: 1.8rem !important; font-weight: 800 !important; text-align: center; margin-bottom: 1rem; padding-top: 10px; border-bottom: 2px solid #ffffff33; }
    .user-logged { color: #00ff00 !important; font-weight: 900; font-size: 1.1rem; text-transform: uppercase; margin-bottom: 20px; text-align: center; }
    .sidebar-footer { color: #ffffff !important; font-size: 0.8rem; text-align: center; margin-top: 20px; opacity: 0.8; }
    .section-banner { background-color: #1e3a8a; color: white !important; padding: 25px; border-radius: 12px; margin-bottom: 30px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 2px solid #ffffff22; }
    .stButton>button[kind="secondary"] { background-color: #22c55e !important; color: white !important; border: none !important; width: 100%; font-weight: 700; }
    .ai-box { background: #f8fafc; border: 2px solid #a855f7; border-radius: 15px; padding: 25px; margin-top: 10px; box-shadow: 0 4px 12px rgba(168, 85, 247, 0.2); }
    .alert-sidebar { background: #ef4444; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: 800; margin: 10px 5px; border: 2px solid white; animation: pulse 2s infinite; }
    @keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.02);} 100% {transform: scale(1);} }
    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .cal-table th { background: #f1f5f9; padding: 10px; color: #1e3a8a; font-weight: 800; border: 1px solid #e2e8f0; font-size: 0.85rem; }
    .cal-table td { border: 1px solid #e2e8f0; vertical-align: top; height: 150px; padding: 5px; position: relative; overflow: visible !important; }
    .day-num-html { font-weight: 900; color: #64748b; font-size: 0.8rem; margin-bottom: 4px; display: block; }
    .event-tag-html { font-size: 0.65rem; background: #dbeafe; color: #1e40af; padding: 2px 4px; border-radius: 4px; margin-bottom: 3px; border-left: 3px solid #2563eb; line-height: 1.1; position: relative; cursor: help; }
    .event-tag-html .tooltip-text { visibility: hidden; width: 220px; background-color: #1e3a8a; color: #fff; text-align: left; border-radius: 8px; padding: 12px; position: absolute; z-index: 9999 !important; bottom: 125%; left: 0%; opacity: 0; transition: opacity 0.3s; box-shadow: 0 8px 20px rgba(0,0,0,0.4); font-size: 0.75rem; line-height: 1.4; white-space: normal; border: 1px solid #ffffff44; pointer-events: none; }
    .event-tag-html:hover .tooltip-text { visibility: visible; opacity: 1; }
    .today-html { background-color: #f0fdf4 !important; border: 2px solid #22c55e !important; }
    .map-reparto { background: #f1f5f9; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .reparto-title { text-align: center; color: #1e3a8a; font-weight: 900; text-transform: uppercase; margin-bottom: 15px; border-bottom: 2px solid #1e3a8a33; }
    .stanza-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
    .stanza-tile { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px; border-left: 6px solid #94a3b8; }
    .stanza-header { font-weight: 800; font-size: 0.8rem; color: #475569; margin-bottom: 5px; border-bottom: 1px solid #eee; }
    .letto-slot { font-size: 0.8rem; color: #1e293b; padding: 2px 0; }
    .stanza-occupata { border-left-color: #22c55e; background-color: #f0fdf4; }
    .stanza-piena { border-left-color: #2563eb; background-color: #eff6ff; }
    .stanza-isolamento { border-left-color: #ef4444; background-color: #fef2f2; border-width: 2px; }
    .cassa-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .saldo-txt { font-size: 2.2rem; font-weight: 900; color: #166534; }
</style>
""",
    unsafe_allow_html=True,
)

# --- Login ---
if not st.session_state.autenticato:
    st.title("🔐 REMS-Connect - Accesso")
    u_i = st.text_input("Username (es. Admin)")
    p_i = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if u_i and p_i:
            h_p = hashlib.sha256(p_i.encode()).hexdigest()
            try:
                res = (
                    supabase.table("utenti")
                    .select("*")
                    .eq("username", u_i)
                    .execute()
                )
                if res.data:
                    utente = res.data[0]
                    if utente.get("password") == h_p:
                        st.session_state.autenticato = True
                        st.session_state.user = utente.get("username")
                        st.session_state.ruolo = utente.get("ruolo")
                        sess = {
                            k: v
                            for k, v in utente.items()
                            if k != "password"
                        }
                        sess["user"] = sess.get("username", "")
                        st.session_state.user_session = sess
                        now = get_italy_time()
                        if st.session_state.cal_month is None:
                            st.session_state.cal_month = now.month
                        if st.session_state.cal_year is None:
                            st.session_state.cal_year = now.year
                        st.success(f"Benvenuto {u_i}!")
                        st.rerun()
                    else:
                        st.error("❌ Password errata.")
                else:
                    st.error("❌ Utente non trovato.")
            except Exception as e:
                st.error(f"⚠️ Errore di database: {e}")
        else:
            st.warning("Inserisci sia username che password.")
    st.stop()

# --- Dopo login ---
u = st.session_state.user_session or {}
firma_op = (
    f"{u.get('nome', '')} {u.get('cognome', '')}".strip()
    or u.get("username")
    or "Operatore"
)
oggi_iso = get_italy_time().strftime("%Y-%m-%d")

# --- Sidebar ---
with st.sidebar:
    try:
        scadenze_query = db_run(
            "SELECT COUNT(*) FROM scadenze WHERE data = CURRENT_DATE"
        )
        conta_oggi = scadenze_query[0][0] if scadenze_query else 0
    except Exception:
        conta_oggi = 0

    st.markdown(
        "<div class='sidebar-title'>REMS Connect</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='user-logged'>👤 {st.session_state.user} ({st.session_state.ruolo})</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<div class='alert-sidebar'>⚠️ {conta_oggi} SCADENZE OGGI</div>",
        unsafe_allow_html=True,
    )

    opts = [
        "📊 Monitoraggio",
        "👥 Modulo Equipe",
        "📅 Agenda Dinamica",
        "🗺️ Mappa Posti Letto",
    ]
    if st.session_state.ruolo == "Coordinatore" or (
        (st.session_state.user or "").lower() == "admin"
    ):
        opts.append("⚙️ Admin")

    nav = st.sidebar.radio("NAVIGAZIONE", opts)

    if st.sidebar.button("LOGOUT"):
        try:
            scrivi_log("LOGOUT", "Uscita dal sistema")
        except Exception:
            pass
        st.session_state.autenticato = False
        st.session_state.user = None
        st.session_state.ruolo = None
        st.session_state.user_session = None
        st.rerun()

    st.sidebar.markdown(
        "<br><br><br><div class='sidebar-footer'><b>Antony</b><br>Webmaster<br>ver. 28.9 Elite</div>",
        unsafe_allow_html=True,
    )

# --- LOGICA NAVIGAZIONE ---
if nav == "🗺️ Mappa Posti Letto":
    st.markdown(
        "<div class='section-banner'><h2>TABELLONE VISIVO POSTI LETTO</h2></div>",
        unsafe_allow_html=True,
    )
    stanze_db = db_run("SELECT id, reparto, tipo FROM stanze ORDER BY id")
    paz_db = db_run(
        "SELECT p.id, p.nome, a.stanza_id, a.letto FROM pazienti p LEFT JOIN assegnazioni a ON p.id = a.p_id WHERE p.stato='ATTIVO'"
    )
    mappa = {
        s[0]: {"rep": s[1], "tipo": s[2], "letti": {1: None, 2: None}}
        for s in stanze_db
    }
    for pid, pnome, sid, letto in paz_db:
        if sid in mappa and letto in (1, 2):
            mappa[sid]["letti"][letto] = {"id": pid, "nome": pnome}

    c_a, c_b = st.columns(2)
    for r_code, col_obj in [("A", c_a), ("B", c_b)]:
        with col_obj:
            st.markdown(
                f"<div class='map-reparto'><div class='reparto-title'>Reparto {r_code}</div><div class='stanza-grid'>",
                unsafe_allow_html=True,
            )
            for s_id, s_info in {
                k: v for k, v in mappa.items() if v["rep"] == r_code
            }.items():
                p_count = len([v for v in s_info["letti"].values() if v])
                cls = (
                    "stanza-isolamento"
                    if s_info["tipo"] == "ISOLAMENTO" and p_count > 0
                    else (
                        "stanza-piena"
                        if p_count == 2
                        else (
                            "stanza-occupata"
                            if p_count == 1
                            else ""
                        )
                    )
                )
                st.markdown(
                    f"<div class='stanza-tile {cls}'><div class='stanza-header'>{s_id} <small>{s_info['tipo']}</small></div>",
                    unsafe_allow_html=True,
                )
                for l in [1, 2]:
                    p = s_info["letti"][l]
                    st.markdown(
                        f"<div class='letto-slot'>L{l}: <b>{p['nome'] if p else 'Libero'}</b></div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div></div>", unsafe_allow_html=True)

    with st.expander("Sposta Paziente"):
        p_list = db_run(
            "SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"
        )
        sel_p = st.selectbox(
            "Paziente", [p[1] for p in p_list], index=None
        )
        if sel_p:
            pid_sel = [p[0] for p in p_list if p[1] == sel_p][0]
            posti_liberi = [
                f"{sid}-L{l}"
                for sid, si in mappa.items()
                for l, po in si["letti"].items()
                if not po
            ]
            dest = st.selectbox("Destinazione", posti_liberi)
            mot = st.text_input("Motivo Trasferimento")
            if st.button("ESEGUI TRASFERIMENTO") and mot:
                dsid, dl = dest.split("-L")
                db_run(
                    "DELETE FROM assegnazioni WHERE p_id=?",
                    (pid_sel,),
                )
                db_run(
                    "INSERT INTO assegnazioni (p_id, stanza_id, letto, data_ass) VALUES (?,?,?,?)",
                    (
                        pid_sel,
                        dsid,
                        int(dl),
                        get_now_it().strftime("%Y-%m-%d"),
                    ),
                )
                db_run(
                    "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                    (
                        pid_sel,
                        get_now_it().strftime("%d/%m/%Y %H:%M"),
                        f"🔄 TRASFERIMENTO: Spostato in {dsid} Letto {dl}. Motivo: {mot}",
                        u.get("ruolo", st.session_state.ruolo),
                        firma_op,
                    ),
                )
                st.rerun()

elif nav == "📊 Monitoraggio":
    st.markdown(
        "<div class='section-banner'><h2>DIARIO CLINICO GENERALE</h2></div>",
        unsafe_allow_html=True,
    )
    p_lista = db_run(
        "SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"
    )
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        f_data = st.text_input(
            "📅 Filtra per Data (es: 2026-04)",
            placeholder="GG/MM/AAAA",
        )
    with c2:
        f_op = st.text_input(
            "👤 Filtra Operatore/Ruolo",
            placeholder="Es: Rossi o Infermiere",
        )
    st.markdown("---")

    for pid, nome in p_lista:
        with st.expander(f"📁 SCHEDA: {nome}"):
            query = "SELECT data, ruolo, op, nota FROM eventi WHERE id=?"
            params = [pid]
            if f_data:
                query += " AND data LIKE ?"
                params.append(f"%{f_data}%")
            if f_op:
                query += " AND (op LIKE ? OR ruolo LIKE ?)"
                params.append(f"%{f_op}%")
                params.append(f"%{f_op}%")
            eventi = db_run(query + " ORDER BY id_u DESC", tuple(params))
            col1, col2 = st.columns([4, 1])
            with col2:
                if eventi:
                    eventi_pdf = [(e[0], e[2], e[3]) for e in eventi]
                    pdf_data = genera_pdf_clinico(nome, eventi_pdf)
                    st.download_button(
                        label="📄 PDF",
                        data=pdf_data,
                        file_name=f"diario_{nome}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{pid}",
                    )
            with col1:
                if eventi:
                    for e in eventi:
                        st.markdown(
                            f"**{e[0]}** - *{e[1]} ({e[2]})*"
                        )
                        st.write(e[3])
                        st.divider()
                else:
                    st.info("Nessuna nota trovata con questi filtri.")

elif nav == "👥 Modulo Equipe":
    st.markdown(
        "<div class='section-banner'><h2>MODULO OPERATIVO EQUIPE</h2></div>",
        unsafe_allow_html=True,
    )
    ruolo_corr = u.get("qualifica", u.get("ruolo", "OSS"))
    if u.get("qualifica") == "Admin" or (u.get("user") or "").lower() == "admin":
        ruolo_corr = st.selectbox(
            "Simula Figura:",
            [
                "Psichiatra",
                "Infermiere",
                "Educatore",
                "OSS",
                "Psicologo",
                "Assistente Sociale",
                "OPSI",
            ],
        )

    p_lista = db_run(
        "SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"
    )

    if p_lista:
        p_sel = st.selectbox(
            "Seleziona Paziente", [p[1] for p in p_lista]
        )
        p_id = [p[0] for p in p_lista if p[1] == p_sel][0]
        now = get_now_it()
        oggi = now.strftime("%d/%m/%Y")

        if ruolo_corr == "Psichiatra":
            if st.session_state.pop("_flash_terapia_ok", False):
                st.success("Prescrizione registrata.")
            t1, t2, t3, t4 = st.tabs(
                [
                    "📋 DIARIO CLINICO",
                    "💊 TERAPIA",
                    "🩺 ESAME OBIETTIVO",
                    "🤖 ANALISI CLINICA IA",
                ]
            )
            with t1:
                st.subheader("Inserimento Nota in Diario Clinico")
                with st.form("form_diario_med"):
                    nota_med = st.text_area(
                        "Valutazione clinica, colloqui, variazioni...",
                        height=200,
                    )
                    if st.form_submit_button("REGISTRA NOTA CLINICA"):
                        if nota_med:
                            db_run(
                                "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                                (
                                    p_id,
                                    get_now_it().strftime(
                                        "%d/%m/%Y %H:%M"
                                    ),
                                    f"🩺 [DIARIO] {nota_med}",
                                    "Psichiatra",
                                    firma_op,
                                ),
                            )
                            st.success("Nota registrata!")
                            st.rerun()

            with t2:
                st.subheader("💊 Gestione Terapia Farmacologica")
                terapie_attuali = db_run(
                    "SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?",
                    (p_id,),
                )
                if terapie_attuali:
                    for t in terapie_attuali:
                        c1, c2 = st.columns([4, 1])
                        c1.info(
                            f"💊 {t[1]} - {t[2]} (M:{'✅' if t[3] else '❌'} | P:{'✅' if t[4] else '❌'} | Bisogno:{'✅' if t[5] else '❌'})"
                        )
                        if c2.button("🗑️", key=f"del_med_{t[0]}"):
                            db_run(
                                "DELETE FROM terapie WHERE id_u=?",
                                (t[0],),
                            )
                            st.rerun()
                st.divider()
                st.markdown(
                    "### 📊 Registro Somministrazioni Infermieristiche"
                )
                res_smarc = db_run(
                    """
                    SELECT data, nota, op FROM eventi
                    WHERE id=? AND (esito='A' OR esito='R' OR nota LIKE '✔️%' OR nota LIKE '❌%')
                    ORDER BY id_u DESC LIMIT 15
                    """,
                    (p_id,),
                )
                if res_smarc:
                    df_smarc = pd.DataFrame(
                        res_smarc,
                        columns=[
                            "Data/Ora",
                            "Dettaglio Somministrazione",
                            "Infermiere",
                        ],
                    )
                    st.dataframe(df_smarc, use_container_width=True)
                else:
                    st.info(
                        "Nessuna somministrazione registrata nelle ultime ore."
                    )
                st.divider()
                with st.expander("➕ Prescrivi Nuovo Farmaco"):
                    with st.form("nuova_terapia_med"):
                        f_nome = st.text_input("Nome Farmaco")
                        f_dose = st.text_input("Dosaggio")
                        col1, col2, col3 = st.columns(3)
                        m_n = col1.checkbox("Mattina")
                        p_n = col2.checkbox("Pomeriggio")
                        a_b = col3.checkbox("Al bisogno")
                        if st.form_submit_button("CONFERMA PRESCRIZIONE"):
                            ok_t, err_t = insert_terapia_prescrizione(
                                p_id,
                                f_nome,
                                f_dose,
                                m_n,
                                p_n,
                                a_b,
                            )
                            if ok_t:
                                st.session_state["_flash_terapia_ok"] = True
                                st.rerun()
                            else:
                                st.error(err_t or "Errore sconosciuto.")

            with t3:
                st.subheader("🩺 Esame Obiettivo e Parametri")
                ultimi_p = db_run(
                    "SELECT data, nota FROM eventi WHERE id=? AND nota LIKE '💓 Parametri:%' ORDER BY id_u DESC LIMIT 5",
                    (p_id,),
                )
                if ultimi_p:
                    for d, n in ultimi_p:
                        st.write(f"**{d}**: {n}")
                with st.form("esame_ob_med"):
                    e_o = st.text_area(
                        "Descrizione esame obiettivo e stato mentale..."
                    )
                    if st.form_submit_button("SALVA ESAME OBIETTIVO"):
                        db_run(
                            "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                            (
                                p_id,
                                get_now_it().strftime(
                                    "%d/%m/%Y %H:%M"
                                ),
                                f"🧠 [E.O.] {e_o}",
                                "Psichiatra",
                                firma_op,
                            ),
                        )
                        st.rerun()

            with t4:
                st.subheader("🤖 Analisi Clinica IA (Briefing Medico)")
                b_logs = db_run(
                    "SELECT data, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 20",
                    (p_id,),
                )
                if b_logs:
                    if st.button(
                        "🤖 GENERA RELAZIONE CLINICA AGGIORNATA",
                        type="primary",
                    ):
                        testo_note = "\n".join(
                            [
                                f"[{d}] {o}: {n}"
                                for d, o, n in reversed(b_logs)
                            ]
                        )
                        with st.spinner(
                            "L'IA sta analizzando il caso clinico..."
                        ):
                            prompt = f"Agisci come Psichiatra. Analizza queste note e genera una sintesi clinica: {testo_note}"
                            relazione = genera_relazione_ia(
                                p_id, prompt, 1
                            )
                            st.markdown(
                                f"<div class='ai-box'>{relazione}</div>",
                                unsafe_allow_html=True,
                            )
                else:
                    st.warning("Dati insufficienti per l'analisi IA.")

            st.divider()
            with st.expander("📄 ESPORTAZIONE PDF", expanded=True):
                tipo_rep = st.radio(
                    "Contenuto del Report:",
                    [
                        "Diario Completo",
                        "Solo Terapie",
                        "Solo Consegne",
                    ],
                    horizontal=True,
                    key="radio_pdf_final",
                )
                if tipo_rep == "Solo Terapie":
                    q_pdf = "SELECT data, op, nota FROM eventi WHERE id=? AND (nota LIKE '%💊%' OR nota LIKE '%✔️%' OR nota LIKE '%❌%' OR op LIKE '%SOMMINISTRAZIONE%') ORDER BY id_u DESC"
                elif tipo_rep == "Solo Consegne":
                    q_pdf = "SELECT data, op, nota FROM eventi WHERE id=? AND (LOWER(ruolo) LIKE '%infermiere%' OR ruolo = 'Infermiere') ORDER BY id_u DESC"
                else:
                    q_pdf = "SELECT data, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC"
                dati_pdf = db_run(q_pdf, (p_id,))
                if dati_pdf:
                    try:
                        pdf_b = genera_pdf_clinico(
                            p_sel, dati_pdf, tipo_rep
                        )
                        st.download_button(
                            label=f"📥 SCARICA PDF: {tipo_rep.upper()}",
                            data=pdf_b,
                            file_name=f"Report_{p_sel}_{tipo_rep.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            key="dl_btn_auto",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.error(f"Errore tecnico PDF: {e}")
                else:
                    st.warning(
                        "Nessun dato trovato per questa selezione."
                    )

        elif ruolo_corr == "Infermiere":
            t1, t2, t3, t4 = st.tabs(
                [
                    "💊 KEEP TERAPIA",
                    "💓 PARAMETRI",
                    "📝 CONSEGNE",
                    "📋 BRIEFING IA",
                ]
            )
            u_inf = st.session_state.user_session or {}
            nome_reale = f"{u_inf.get('nome', '')} {u_inf.get('cognome', '')}".strip() or firma_op
            ruolo_reale = u_inf.get("ruolo", st.session_state.ruolo)

            with t1:
                st.subheader("Registrazione Somministrazione Farmaci")
                st.info(
                    f"👤 Operatore: **{nome_reale}** | Turno attivo"
                )
                turno_attivo = st.selectbox(
                    "Seleziona Turno Operativo",
                    [
                        "8:13 (Mattina)",
                        "16:20 (Pomeriggio)",
                        "Al bisogno",
                    ],
                )
                terapie_keep = db_run(
                    "SELECT id_u, farmaco, dose, mat_nuovo, pom_nuovo, al_bisogno FROM terapie WHERE p_id=?",
                    (p_id,),
                )
                for f in terapie_keep:
                    t_id_univoco, nome_f, dose_f = f[0], f[1], f[2]
                    mostra = (
                        turno_attivo == "8:13 (Mattina)" and f[3] == 1
                    ) or (
                        turno_attivo == "16:20 (Pomeriggio)"
                        and f[4] == 1
                    ) or (
                        turno_attivo == "Al bisogno" and f[5] == 1
                    )
                    if mostra:
                        st.markdown(
                            f"### 💊 {nome_f} <small>({dose_f})</small>",
                            unsafe_allow_html=True,
                        )
                        mese_corrente = get_now_it().strftime("%m/%Y")
                        firme = db_run(
                            "SELECT data, esito, op FROM eventi WHERE id=? AND nota LIKE ? AND nota LIKE ? AND data LIKE ?",
                            (
                                p_id,
                                f"%[{t_id_univoco}]%",
                                f"%({turno_attivo})%",
                                f"%/{mese_corrente}%",
                            ),
                        )
                        f_map = {
                            int(d[0].split("/")[0]): {"e": d[1], "o": d[2]}
                            for d in firme
                            if d[0]
                        }
                        num_giorni = calendar.monthrange(
                            get_now_it().year, get_now_it().month
                        )[1]
                        h = "<div style='display: flex; overflow-x: auto; padding: 10px; gap: 6px;'>"
                        for d in range(1, num_giorni + 1):
                            info = f_map.get(d)
                            is_today = (
                                "border: 2px solid #2563eb;"
                                if d == get_now_it().day
                                else "border: 1px solid #ddd;"
                            )
                            esito_txt, col_t, bg_c, firma_quadratino = (
                                "-",
                                "#888",
                                "white",
                                "",
                            )
                            if info:
                                firma_quadratino = info["o"]
                                if info["e"] == "A":
                                    esito_txt, col_t, bg_c = (
                                        "A",
                                        "#15803d",
                                        "#dcfce7",
                                    )
                                elif info["e"] == "R":
                                    esito_txt, col_t, bg_c = (
                                        "R",
                                        "#b91c1c",
                                        "#fee2e2",
                                    )
                            h += f"""
                            <div style='min-width: 85px; height: 85px; background: {bg_c}; color: {col_t};
                                {is_today} border-radius: 6px; display: flex; flex-direction: column;
                                align-items: center; justify-content: center; font-size: 0.75rem;'>
                                <div style='font-weight: bold;'>{d}</div>
                                <div style='font-size: 1.2rem; font-weight: bold;'>{esito_txt}</div>
                                <div style='font-size: 0.55rem; color: #333; margin-top: 4px; text-align: center; font-weight: 600;'>{firma_quadratino}</div>
                            </div>"""
                        st.markdown(h + "</div>", unsafe_allow_html=True)
                        with st.popover(f"Smarca {nome_f}"):
                            c1, c2 = st.columns(2)
                            if c1.button(
                                "✅ ASSUNTO",
                                key=f"ok_{t_id_univoco}_{turno_attivo}",
                            ):
                                nota_f = f"✔️ [{t_id_univoco}] {nome_f} ({turno_attivo})"
                                db_run(
                                    "INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)",
                                    (
                                        p_id,
                                        get_now_it().strftime(
                                            "%d/%m/%Y %H:%M"
                                        ),
                                        nota_f,
                                        ruolo_reale,
                                        nome_reale,
                                        "A",
                                    ),
                                )
                                st.rerun()
                            if c2.button(
                                "❌ RIFIUTO",
                                key=f"ko_{t_id_univoco}_{turno_attivo}",
                            ):
                                nota_f = f"❌ [{t_id_univoco}] RIFIUTO {nome_f} ({turno_attivo})"
                                db_run(
                                    "INSERT INTO eventi (id, data, nota, ruolo, op, esito) VALUES (?,?,?,?,?,?)",
                                    (
                                        p_id,
                                        get_now_it().strftime(
                                            "%d/%m/%Y %H:%M"
                                        ),
                                        nota_f,
                                        ruolo_reale,
                                        nome_reale,
                                        "R",
                                    ),
                                )
                                st.rerun()
                        st.divider()

            with t2:
                st.subheader("💓 Rilevazione Parametri Vitali")
                with st.form("form_p_inf"):
                    c1, c2, c3 = st.columns(3)
                    p_v = c1.text_input("PA (Pressione)")
                    f_v = c2.text_input("FC (Frequenza)")
                    s_v = c3.text_input("SatO2")
                    if st.form_submit_button("REGISTRA PARAMETRI"):
                        nota_p = f"💓 Parametri: PA {p_v}, FC {f_v}, Sat {s_v}"
                        db_run(
                            "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                            (
                                p_id,
                                get_now_it().strftime(
                                    "%d/%m/%Y %H:%M"
                                ),
                                nota_p,
                                ruolo_reale,
                                nome_reale,
                            ),
                        )
                        st.success("Parametri salvati!")
                        st.rerun()

            with t3:
                st.subheader("📝 Consegne Cliniche")
                with st.form("form_c_inf"):
                    txt_c = st.text_area("Inserisci diario clinico...")
                    if st.form_submit_button("SALVA NOTA"):
                        db_run(
                            "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                            (
                                p_id,
                                get_now_it().strftime(
                                    "%d/%m/%Y %H:%M"
                                ),
                                f"📝 {txt_c}",
                                ruolo_reale,
                                nome_reale,
                            ),
                        )
                        st.success("Nota registrata!")
                        st.rerun()

            with t4:
                st.subheader("📋 Briefing Intelligente (IA)")
                b_logs = db_run(
                    "SELECT data, op, nota FROM eventi WHERE id=? ORDER BY id_u DESC LIMIT 20",
                    (p_id,),
                )
                if b_logs:
                    st.success(
                        f"✅ Recuperate le ultime {len(b_logs)} attività dal diario clinico."
                    )
                    if st.button(
                        "🤖 GENERA RIASSUNTO TURNO (IA)",
                        type="primary",
                        use_container_width=True,
                    ):
                        testo_note = "\n".join(
                            [
                                f"[{d}] {o}: {n}"
                                for d, o, n in reversed(b_logs)
                            ]
                        )
                        with st.spinner(
                            "L'IA sta analizzando i dati..."
                        ):
                            istruzioni_ia = (
                                "RIASSUNTO BRIEFING TURNO: "
                                "Analizza queste ultime 20 note e crea un sunto professionale per il cambio turno, "
                                "dividendo in: 1. Terapie e Rifiuti, 2. Parametri, 3. Note comportamentali.\n\n"
                                f"DATI:\n{testo_note}"
                            )
                            try:
                                sunto = genera_relazione_ia(
                                    p_id, istruzioni_ia, 1
                                )
                                st.info(
                                    "### 📝 Riassunto IA (Ultime 20 attività)"
                                )
                                st.write(sunto)
                                st.divider()
                            except Exception as e:
                                st.error(
                                    f"Errore nella generazione: {e}"
                                )
                    with st.expander(
                        "🔍 Controlla i dati originali (Ultime 20)"
                    ):
                        for d, o, n in b_logs:
                            st.markdown(
                                f"**{d}** - *{o}*<br>{n}",
                                unsafe_allow_html=True,
                            )
                            st.divider()
                else:
                    st.warning(
                        "⚠️ Nessun dato trovato nel diario eventi."
                    )

        elif ruolo_corr == "Psicologo":
            t1, t2 = st.tabs(["🧠 COLLOQUIO", "📝 TEST"])
            with t1:
                with st.form("f_psi"):
                    txt = st.text_area("Sintesi Colloquio")
                    if st.form_submit_button("SALVA"):
                        db_run(
                            "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                            (
                                p_id,
                                now.strftime("%d/%m/%Y %H:%M"),
                                f"🧠 {txt}",
                                "Psicologo",
                                firma_op,
                            ),
                        )
                        st.rerun()
            with t2:
                with st.form("f_test"):
                    test_n = st.text_input("Nome Test")
                    test_r = st.text_area("Risultato")
                    if st.form_submit_button("REGISTRA"):
                        db_run(
                            "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                            (
                                p_id,
                                now.strftime("%d/%m/%Y %H:%M"),
                                f"📊 TEST {test_n}: {test_r}",
                                "Psicologo",
                                firma_op,
                            ),
                        )
                        st.rerun()

        elif ruolo_corr == "Assistente Sociale":
            t1, t2 = st.tabs(["🤝 RETE", "🏠 PROGETTO"])
            with t1:
                with st.form("f_soc"):
                    cont = st.text_input("Contatto")
                    txt = st.text_area("Esito")
                    if st.form_submit_button("SALVA"):
                        db_run(
                            "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                            (
                                p_id,
                                now.strftime("%d/%m/%Y %H:%M"),
                                f"🤝 CONTATTO {cont}: {txt}",
                                "Assistente Sociale",
                                firma_op,
                            ),
                        )
                        st.rerun()
            with t2:
                with st.form("f_prog"):
                    prog = st.text_area("Aggiornamento Progetto")
                    if st.form_submit_button("SALVA"):
                        db_run(
                            "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                            (
                                p_id,
                                now.strftime("%d/%m/%Y %H:%M"),
                                f"🏠 PROGETTO: {prog}",
                                "Assistente Sociale",
                                firma_op,
                            ),
                        )
                        st.rerun()

        elif ruolo_corr == "OPSI":
            with st.form("f_opsi"):
                cond = st.multiselect(
                    "Stato:",
                    ["Tranquillo", "Agitato", "Ispezione"],
                )
                nota = st.text_input("Note")
                if st.form_submit_button("REGISTRA"):
                    db_run(
                        "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                        (
                            p_id,
                            now.strftime("%d/%m/%Y %H:%M"),
                            f"🛡️ VIGILANZA: {', '.join(cond)} | {nota}",
                            "OPSI",
                            firma_op,
                        ),
                    )
                    st.rerun()

        elif ruolo_corr == "OSS":
            with st.form("oss_f"):
                mans = st.multiselect(
                    "Mansioni:",
                    ["Igiene", "Cambio", "Pulizia", "Letto"],
                )
                txt = st.text_area("Note")
                if st.form_submit_button("REGISTRA"):
                    db_run(
                        "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                        (
                            p_id,
                            now.strftime("%d/%m/%Y %H:%M"),
                            f"🧹 {', '.join(mans)} | {txt}",
                            "OSS",
                            firma_op,
                        ),
                    )
                    st.rerun()

        elif ruolo_corr == "Educatore":
            t1, t2 = st.tabs(["💰 CASSA", "📝 CONSEGNA"])
            with t1:
                mov = db_run(
                    "SELECT importo, tipo FROM cassa WHERE p_id=?",
                    (p_id,),
                )
                saldo = sum(
                    m[0] if m[1] == "ENTRATA" else -m[0] for m in mov
                )
                st.markdown(
                    f"<div class='cassa-card'>Saldo: <span class='saldo-txt'>{saldo:.2f} €</span></div>",
                    unsafe_allow_html=True,
                )
                with st.form("cs"):
                    tp = st.selectbox("Tipo", ["ENTRATA", "USCITA"])
                    im = st.number_input("€")
                    cau = st.text_input("Causale")
                    if st.form_submit_button("REGISTRA"):
                        db_run(
                            "INSERT INTO cassa (p_id, data, causale, importo, tipo, op) VALUES (?,?,?,?,?,?)",
                            (p_id, oggi, cau, im, tp, firma_op),
                        )
                        db_run(
                            "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                            (
                                p_id,
                                now.strftime("%d/%m/%Y %H:%M"),
                                f"💰 {tp}: {im}€ - {cau}",
                                "Educatore",
                                firma_op,
                            ),
                        )
                        st.rerun()
            with t2:
                with st.form("edu_cons"):
                    txt_edu = st.text_area("Osservazioni")
                    if st.form_submit_button("SALVA"):
                        db_run(
                            "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                            (
                                p_id,
                                now.strftime("%d/%m/%Y %H:%M"),
                                f"📝 {txt_edu}",
                                "Educatore",
                                firma_op,
                            ),
                        )
                        st.rerun()

        st.divider()
        render_postits(p_id)

elif nav == "📅 Agenda Dinamica":
    st.markdown(
        "<div class='section-banner'><h2>AGENDA DINAMICA REMS</h2></div>",
        unsafe_allow_html=True,
    )
    c_nav1, c_nav2, c_nav3 = st.columns([1, 2, 1])
    with c_nav1:
        if st.button("⬅️ Mese Precedente"):
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            st.rerun()
    with c_nav2:
        mesi_nomi = [
            "Gennaio",
            "Febbraio",
            "Marzo",
            "Aprile",
            "Maggio",
            "Giugno",
            "Luglio",
            "Agosto",
            "Settembre",
            "Ottobre",
            "Novembre",
            "Dicembre",
        ]
        st.markdown(
            f"<h3 style='text-align:center;'>{mesi_nomi[st.session_state.cal_month - 1]} {st.session_state.cal_year}</h3>",
            unsafe_allow_html=True,
        )
    with c_nav3:
        if st.button("Mese Successivo ➡️"):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            st.rerun()

    col_cal, col_ins = st.columns([3, 1])
    with col_cal:
        start_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-01"
        end_d = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-31"
        evs_mese = db_run(
            """SELECT a.data, p.nome, a.ora, a.tipo_evento, a.mezzo, a.nota, a.accompagnatore FROM appuntamenti a JOIN pazienti p ON a.p_id=p.id WHERE a.data BETWEEN ? AND ? AND a.stato='PROGRAMMATO'""",
            (start_d, end_d),
        )
        mappa_ev = {}
        for d_ev, p_n, h_ev, t_ev, m_ev, nt_ev, acc_ev in evs_mese:
            try:
                g_int = int(str(d_ev).split("-")[2])
                if g_int not in mappa_ev:
                    mappa_ev[g_int] = []
                prefix = (
                    "🚗" if t_ev == "Uscita Esterna" else "🏠"
                )
                tag_final = f'<div class="event-tag-html">{prefix} {p_n}<span class="tooltip-text"><b>{t_ev}</b><br>⏰ {h_ev}<br>🚗 {m_ev}<br>📝 {nt_ev}</span></div>'
                mappa_ev[g_int].append(tag_final)
            except Exception:
                pass
        cal_html = (
            "<table class='cal-table'><thead><tr>"
            + "".join(
                f"<th>{d}</th>"
                for d in [
                    "Lun",
                    "Mar",
                    "Mer",
                    "Gio",
                    "Ven",
                    "Sab",
                    "Dom",
                ]
            )
            + "</tr></thead><tbody>"
        )
        cal_obj = calendar.Calendar(firstweekday=0)
        for week in cal_obj.monthdayscalendar(
            st.session_state.cal_year, st.session_state.cal_month
        ):
            cal_html += "<tr>"
            for day in week:
                if day == 0:
                    cal_html += (
                        "<td style='background:#f8fafc;'></td>"
                    )
                else:
                    d_iso = f"{st.session_state.cal_year}-{st.session_state.cal_month:02d}-{day:02d}"
                    cls_today = (
                        "today-html" if d_iso == oggi_iso else ""
                    )
                    cal_html += f"<td class='{cls_today}'><span class='day-num-html'>{day}</span>{''.join(mappa_ev.get(day, []))}</td>"
            cal_html += "</tr>"
        st.markdown(
            cal_html + "</tbody></table>", unsafe_allow_html=True
        )

    with col_ins:
        st.subheader("➕ Nuovo Appuntamento")
        with st.form("add_app_cal"):
            p_l = db_run(
                "SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"
            )
            ps_sel = st.multiselect(
                "Paziente/i", [p[1] for p in p_l]
            )
            tipo_e = st.selectbox(
                "Tipo", ["Uscita Esterna", "Appuntamento Interno"]
            )
            dat, ora = st.date_input("Giorno"), st.time_input("Ora")
            mezzo_usato = (
                st.selectbox(
                    "Macchina",
                    ["Mitsubishi", "Fiat Qubo", "Nessuno"],
                )
                if tipo_e == "Uscita Esterna"
                else "Nessuno"
            )
            accomp = st.text_input("Accompagnatore")
            not_a = st.text_area("Note")
            if st.form_submit_button("REGISTRA"):
                for nome_p in ps_sel:
                    pid = [p[0] for p in p_l if p[1] == nome_p][0]
                    db_run(
                        "INSERT INTO appuntamenti (p_id, data, ora, nota, stato, autore, tipo_evento, mezzo, accompagnatore) VALUES (?,?,?,?,'PROGRAMMATO',?,?,?,?)",
                        (
                            pid,
                            str(dat),
                            str(ora)[:5],
                            not_a,
                            firma_op,
                            tipo_e,
                            mezzo_usato,
                            accomp,
                        ),
                    )
                    db_run(
                        "INSERT INTO eventi (id, data, nota, ruolo, op) VALUES (?,?,?,?,?)",
                        (
                            pid,
                            get_now_it().strftime(
                                "%d/%m/%Y %H:%M"
                            ),
                            f"📅 {tipo_e}: {not_a}",
                            u.get("ruolo", st.session_state.ruolo),
                            firma_op,
                        ),
                    )
                st.rerun()
        st.divider()
        st.subheader("📋 Lista Scadenze")
        agenda_list = db_run(
            "SELECT a.id_u, a.data, a.ora, p.nome, a.tipo_evento FROM appuntamenti a JOIN pazienti p ON a.p_id = p.id WHERE a.data >= ? AND a.stato='PROGRAMMATO' ORDER BY a.data, a.ora",
            (oggi_iso,),
        )
        for aid, adt, ahr, apn, atev in agenda_list:
            st.markdown(
                f"**{adt} {ahr}** - {apn}<br>{atev}",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            if c1.button("FATTO", key=f"done_{aid}"):
                db_run(
                    "UPDATE appuntamenti SET stato='COMPLETATO' WHERE id_u=?",
                    (aid,),
                )
                st.rerun()
            if c2.button("ELIMINA", key=f"del_{aid}"):
                db_run(
                    "DELETE FROM appuntamenti WHERE id_u=?", (aid,)
                )
                st.rerun()
            st.markdown("---")

elif nav == "⚙️ Admin":
    st.markdown(
        "<div class='section-banner'><h2>PANNELLO AMMINISTRAZIONE</h2></div>",
        unsafe_allow_html=True,
    )
    t_ut, t_paz_att, t_paz_dim, t_diar, t_log = st.tabs(
        ["UTENTI", "PAZIENTI ATTIVI", "ARCHIVIO", "DIARIO EVENTI", "📜 LOG"]
    )

    with t_ut:
        for us, un, uc, uq in db_run(
            "SELECT user, nome, cognome, qualifica FROM utenti"
        ):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"**{un} {uc}** ({uq})")
            if (us or "").lower() != "admin" and c2.button(
                "ELIMINA", key=f"d_{us}"
            ):
                db_run("DELETE FROM utenti WHERE user=?", (us,))
                st.rerun()

    with t_paz_att:
        with st.form("np"):
            np_val = st.text_input("Nuovo Paziente")
            if st.form_submit_button("AGGIUNGI"):
                db_run(
                    "INSERT INTO pazienti (nome, stato) VALUES (?, 'ATTIVO')",
                    (np_val.upper(),),
                )
                st.rerun()
        for pid, pn in db_run(
            "SELECT id, nome FROM pazienti WHERE stato='ATTIVO' ORDER BY nome"
        ):
            c1, c2, c3 = st.columns([0.6, 0.2, 0.2])
            c1.write(f"**{pn}**")
            if c2.button("DIMETTI", key=f"dim_{pid}"):
                db_run(
                    "UPDATE pazienti SET stato='DIMESSO' WHERE id=?",
                    (pid,),
                )
                db_run(
                    "DELETE FROM assegnazioni WHERE p_id=?", (pid,)
                )
                st.rerun()
            if c3.button("ELIMINA", key=f"dp_{pid}"):
                db_run("DELETE FROM pazienti WHERE id=?", (pid,))
                st.rerun()

    with t_paz_dim:
        for pid, pn in db_run(
            "SELECT id, nome FROM pazienti WHERE stato='DIMESSO' ORDER BY nome"
        ):
            c1, c2 = st.columns([0.8, 0.2])
            c1.write(f"📁 {pn}")
            if c2.button("RIAMMETTI", key=f"re_{pid}"):
                db_run(
                    "UPDATE pazienti SET stato='ATTIVO' WHERE id=?",
                    (pid,),
                )
                st.rerun()

    with t_diar:
        lista_p = db_run("SELECT id, nome FROM pazienti ORDER BY nome")
        filtro_p = st.selectbox(
            "Filtra per Paziente:", ["*TUTTI*"] + [p[1] for p in lista_p]
        )
        query_log = "SELECT e.data, e.ruolo, e.op, e.nota, p.nome, e.id_u FROM eventi e JOIN pazienti p ON e.id = p.id"
        params_log = []
        if filtro_p != "*TUTTI*":
            query_log += " WHERE p.nome = ?"
            params_log.append(filtro_p)
        tutti_log = db_run(
            query_log + " ORDER BY e.id_u DESC LIMIT 100",
            tuple(params_log),
        )
        for ldt, lru, lop, lnt, lpnome, lidu in tutti_log:
            c1, c2 = st.columns([0.85, 0.15])
            c1.write(
                f"**[{ldt}]** {lpnome} | {lop} ({lru}): {lnt}"
            )
            if c2.button("🗑️", key=f"del_adm_{lidu}"):
                db_run("DELETE FROM eventi WHERE id_u=?", (lidu,))
                st.rerun()
            st.divider()

    with t_log:
        logs_audit = db_run(
            "SELECT data_ora, utente, azione, dettaglio FROM logs_sistema ORDER BY id_log DESC LIMIT 200"
        )
        if logs_audit:
            st.dataframe(
                pd.DataFrame(
                    logs_audit,
                    columns=[
                        "Data/Ora",
                        "Operatore",
                        "Azione",
                        "Descrizione",
                    ],
                ),
                use_container_width=True,
            )
