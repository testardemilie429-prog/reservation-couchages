from datetime import date, timedelta
import pandas as pd
import streamlit as st
import requests

https://script.google.com/macros/library/d/18Dey5ij_-cIxTwPW3XygcvPEoqAKLaNpycJ3oJCqKufb4gOrfiX5NOSm/22

TOTAL_WEEK = 2154.0
NIGHTS_COUNT = 7
HOUSE_PER_NIGHT = TOTAL_WEEK / NIGHTS_COUNT  # 307.71
MIN_PER_PERSON = 31.0

START_NIGHT = date(2026, 8, 16)
END_NIGHT_EXCL = date(2026, 8, 23)  # exclu => dernière nuit = 22

ROOMS = ["Chambre 1", "Chambre 2", "Chambre 3", "Dortoir"]
BEDS_BY_ROOM = {
    "Chambre 1": ["Couchage 1", "Couchage 2"],
    "Chambre 2": ["Couchage 1", "Couchage 2"],
    "Chambre 3": ["Couchage 1", "Couchage 2"],
    "Dortoir":   ["Couchage 1", "Couchage 2", "Couchage 3", "Couchage 4"],
}

LABELS = {
    "Chambre 1": "Chambre 1 (lit double)",
    "Chambre 2": "Chambre 2 (lit double)",
    "Chambre 3": "Chambre 3 (lit double)",
    "Dortoir": "Dortoir (4 lits simples)",
}

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
    txt = r.text.strip()
    if not txt.startswith("["):
        raise Exception("Le script ne renvoie pas du JSON (déploiement Apps Script pas public ?).")
    data = r.json()
    df = pd.DataFrame(data)

    for col in ["night", "room", "bed", "name"]:
        if col not in df.columns:
            df[col] = []

    df["night"] = df["night"].astype(str).str.slice(0, 10).str.strip()
    df["room"] = df["room"].astype(str).str.strip()
    df["bed"] = df["bed"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    return df

def save_booking(night: date, room: str, bed: str, name: str):
    r = requests.post(
        SCRIPT_URL,
        json={"night": night.isoformat(), "room": room, "bed": bed, "name": name.strip()},
        timeout=20
    )
    r.raise_for_status()
    if r.text.strip() not in ("OK", ""):
        raise Exception(f"Réponse script: {r.text.strip()}")

def norm(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    if " (" in s:
        s = s.split(" (")[0].strip()  # enlève "(lit double)" etc
    return s

def is_taken(df: pd.DataFrame, night: date, room_key: str, bed: str):
    if df.empty:
        return None
    n = night.isoformat()

    x = df[
        (df["night"] == n) &
        (df["room"].apply(norm) == norm(room_key)) &
        (df["bed"].apply(norm) == norm(bed))
    ]
    if x.empty:
        return None
    return str(x.iloc[0]["name"])

def price_tables(df: pd.DataFrame):
    ns = nights()
    if df.empty:
        return (
            pd.DataFrame([{"Nuit": n.strftime("%a %d/%m"), "Présents": 0, "Prix / personne": ""} for n in ns]),
            pd.DataFrame(columns=["Nom", "Nuits", "Total (€)"])
        )

    df2 = df.copy()
    df2["night_date"] = pd.to_datetime(df2["night"], errors="coerce").dt.date

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

    return pd.DataFrame(rows), table_totaux

# ---- UI ----
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

with st.expander("🔎 Debug (ce que lit l'appli)"):
    st.write("Nombre de lignes lues :", len(df))
    st.dataframe(df.tail(30), use_container_width=True)
    if not df.empty:
        st.write("Rooms uniques :", sorted(df["room"].unique().tolist()))
        st.write("Beds uniques :", sorted(df["bed"].unique().tolist()))
        st.write("Nights uniques :", sorted(df["night"].unique().tolist()))

tabs = st.tabs([d.strftime("%a %d/%m") for d in nights()])

for tab, d in zip(tabs, nights()):
    with tab:
        st.markdown(f"### {d.strftime('%A %d %B %Y').capitalize()} (nuit)")
        cols = st.columns(4)

        for i, room_key in enumerate(ROOMS):
            with cols[i]:
                st.subheader(LABELS[room_key])
                for bed in BEDS_BY_ROOM[room_key]:
                    taken_by = is_taken(df, d, room_key, bed)
                    box = st.container(border=True)
                    with box:
                        st.write(f"**{bed}**")
                        if taken_by:
                            st.success(f"Pris par : {taken_by}")
                        else:
                            with st.form(key=f"{d}-{room_key}-{bed}", clear_on_submit=True):
                                n = st.text_input("Ton prénom", label_visibility="collapsed", placeholder="Ex : Emilie")
                                ok = st.form_submit_button("Réserver")
                                if ok:
                                    if not n.strip():
                                        st.error("Mets ton prénom 🙂")
                                    else:
                                        try:
                                            save_booking(d, room_key, bed, n)
                                            st.success("Réservé ✅")
                                            st.rerun()
                                        except Exception as e:
                                            st.error("Impossible d’enregistrer.")
                                            st.exception(e)

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
st.subheader("📋 Vue globale")
if df.empty:
    st.write("Aucune inscription pour l’instant.")
else:
    df_show = df.copy()
    st.dataframe(df_show[["night", "room", "bed", "name"]].sort_values(["night", "room", "bed"]),
                 use_container_width=True)

