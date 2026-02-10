from datetime import date, timedelta
import pandas as pd
import streamlit as st
import requests

# ✅ Ton lien Apps Script (doit finir par /exec)
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzvzzcDs8OmU9VPnMIKEVbwm1MRvOVWJ3ETakOZUEiUr_w5BvpL_gHQYXM9OcYHVr6Z/exec"

# Période : nuits du 16 au 22 août 2026 (départ le 23)
START_NIGHT = date(2026, 8, 16)
END_NIGHT_EXCL = date(2026, 8, 23)

# Couchages
BLOCKS = {
    "Chambre 1 (lit double)": ["Couchage 1", "Couchage 2"],
    "Chambre 2 (lit double)": ["Couchage 1", "Couchage 2"],
    "Chambre 3 (lit double)": ["Couchage 1", "Couchage 2"],
    "Dortoir (4 lits simples)": ["Couchage 1", "Couchage 2", "Couchage 3", "Couchage 4"],
}

# Prix
TOTAL_WEEK = 2154.0
NIGHTS_COUNT = 7
HOUSE_PER_NIGHT = TOTAL_WEEK / NIGHTS_COUNT  # 307.71
MIN_PER_PERSON = 31.0


def nights():
    d = START_NIGHT
    out = []
    while d < END_NIGHT_EXCL:
        out.append(d)
        d += timedelta(days=1)
    return out


def load_bookings() -> pd.DataFrame:
    r = requests.get(SCRIPT_URL, timeout=20)
    r.raise_for_status()

    # Google peut renvoyer du JSON avec content-type text/html, on accepte quand même
    txt = r.text.strip()
    if not txt.startswith("["):
        raise Exception("Le script ne renvoie pas du JSON. Déploiement Apps Script pas public ?")

    data = r.json()
    df = pd.DataFrame(data)

    # Sécurise colonnes attendues
    for col in ["night", "room", "bed", "name"]:
        if col not in df.columns:
            df[col] = []
    return df


def save_booking(night: date, room: str, bed: str, name: str):
    requests.post(
        SCRIPT_URL,
        json={"night": night.isoformat(), "room": room, "bed": bed, "name": name.strip()},
        timeout=20
    ).raise_for_status()


def is_taken(df: pd.DataFrame, night: date, room: str, bed: str):
    if df.empty:
        return None
    x = df[
        (df["night"] == night.isoformat()) &
        (df["room"] == room) &
        (df["bed"] == bed)
    ]
    if x.empty:
        return None
    return str(x.iloc[0]["name"])


def price_tables(df: pd.DataFrame):
    ns = nights()

    if df.empty:
        table_nuits = pd.DataFrame([{
            "Nuit": n.strftime("%a %d/%m"),
            "Présents": 0,
            "Prix / personne": ""
        } for n in ns])
        table_totaux = pd.DataFrame(columns=["Nom", "Nuits", "Total (€)"])
        return table_nuits, table_totaux

    df2 = df.copy()
    df2["night_date"] = pd.to_datetime(df2["night"]).dt.date

    # prix par nuit
    per_night_price = {}
    rows = []
    for n in ns:
        c = int((df2["night_date"] == n).sum())
        if c <= 0:
            rows.append({"Nuit": n.strftime("%a %d/%m"), "Présents": 0, "Prix / personne": ""})
            continue
        p = max(MIN_PER_PERSON, HOUSE_PER_NIGHT / c)
        per_night_price[n] = p
        rows.append({"Nuit": n.strftime("%a %d/%m"), "Présents": c, "Prix / personne": f"{p:.2f} €"})

    table_nuits = pd.DataFrame(rows)

    # total par personne
    totals = {}
    nights_count = {}
    for n in ns:
        if n not in per_night_price:
            continue
        p = per_night_price[n]
        people = df2[df2["night_date"] == n]["name"].tolist()
        for person in people:
            totals[person] = totals.get(person, 0.0) + p
            nights_count[person] = nights_count.get(person, 0) + 1

    table_totaux = pd.DataFrame([{
        "Nom": name,
        "Nuits": nights_count.get(name, 0),
        "Total (€)": round(totals.get(name, 0.0), 2)
    } for name in sorted(totals.keys(), key=lambda x: x.lower())])

    return table_nuits, table_totaux


# ---------- UI ----------
st.set_page_config(page_title="Réservation couchages", layout="wide")
st.title("🛏️ Réservation couchages — nuits du 16 au 22 août 2026 (départ 23)")

st.info(
    f"💶 **Prix maison** : {HOUSE_PER_NIGHT:.2f} € / nuit\n\n"
    f"➡️ **Prix par personne (par nuit)** = max({MIN_PER_PERSON:.2f} €, {HOUSE_PER_NIGHT:.2f}€ / nb de présents cette nuit)\n"
    "✅ Donc **31€ est le minimum** si la maison est complète."
)

try:
    df = load_bookings()
except Exception as e:
    st.error("Impossible de lire la Google Sheet.")
    st.exception(e)
    st.stop()

tabs = st.tabs([d.strftime("%a %d/%m") for d in nights()])
rooms_order = list(BLOCKS.keys())

for tab, d in zip(tabs, nights()):
    with tab:
        st.markdown(f"### {d.strftime('%A %d %B %Y').capitalize()} (nuit)")
        cols = st.columns(4)

        for i, room in enumerate(rooms_order):
            with cols[i]:
                st.subheader(room)
                for bed in BLOCKS[room]:
                    taken_by = is_taken(df, d, room, bed)
                    box = st.container(border=True)
                    with box:
                        st.write(f"**{bed}**")
                        if taken_by:
                            st.success(f"Pris par : {taken_by}")
                        else:
                            with st.form(key=f"{d}-{room}-{bed}", clear_on_submit=True):
                                n = st.text_input("Ton prénom", label_visibility="collapsed", placeholder="Ex : Emilie")
                                ok = st.form_submit_button("Réserver")
                                if ok:
                                    if not n.strip():
                                        st.error("Mets ton prénom 🙂")
                                    else:
                                        save_booking(d, room, bed, n)
                                        st.rerun()

st.divider()
st.subheader("💶 Répartition du prix (évolutif)")

t_nuits, t_totaux = price_tables(df)
c1, c2 = st.columns(2)
with c1:
    st.markdown("#### Par nuit")
    st.dataframe(t_nuits, use_container_width=True)
with c2:
    st.markdown("#### Total par personne")
    st.dataframe(t_totaux, use_container_width=True)

st.divider()
st.subheader("📋 Vue globale des inscriptions")
if df.empty:
    st.write("Aucune inscription pour l’instant.")
else:
    df_show = df.copy()
    df_show["night"] = pd.to_datetime(df_show["night"]).dt.strftime("%d/%m/%Y")
    st.dataframe(df_show[["night", "room", "bed", "name"]].sort_values(["night", "room", "bed"]),
                 use_container_width=True)

