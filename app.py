from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
import requests

# --- Ton lien Apps Script (déjà OK) ---
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwE-zsX0D_zE0L3hkmUV9IkWKLVbSS24khntToqKLUuiK0M-RBD1KWbCrxI7aI6peKt/exec"

# --- Doit être IDENTIQUE à const TOKEN dans Apps Script ---
TOKEN = "CHANGE-MOI-123"

# --- Période affichée : nuits du 16 au 22 août 2026 (départ 23) ---
START_NIGHT = date(2026, 8, 16)
END_NIGHT_EXCL = date(2026, 8, 23)  # exclu => dernière nuit = 22

# --- Couchages ---
BLOCKS = {
    "Chambre 1": ["Couchage 1", "Couchage 2"],
    "Chambre 2": ["Couchage 1", "Couchage 2"],
    "Chambre 3": ["Couchage 1", "Couchage 2"],
    "Dortoir":   ["Couchage 1", "Couchage 2", "Couchage 3", "Couchage 4"],
}

# --- Prix (minimum 31€ si complet) ---
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
    data = r.json()  # liste de dicts depuis Google Sheet
    df = pd.DataFrame(data)

    # si la sheet est vide, on crée les colonnes attendues
    needed = ["night", "room", "bed", "name", "created_at"]
    for col in needed:
        if col not in df.columns:
            df[col] = []
    return df


def add_booking(night: date, room: str, bed: str, name: str):
    payload = {
        "token": TOKEN,
        "night": night.isoformat(),
        "room": room,
        "bed": bed,
        "name": name.strip(),
    }
    r = requests.post(SCRIPT_URL, json=payload, timeout=20)
    r.raise_for_status()


def is_taken(df: pd.DataFrame, night: date, room: str, bed: str) -> str | None:
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
            "Inscrits": 0,
            "Prix / personne": ""
        } for n in ns])
        table_totaux = pd.DataFrame(columns=["Nom", "Nuits", "Total (€)"])
        return table_nuits, table_totaux

    df_n = df.copy()
    df_n["night_date"] = pd.to_datetime(df_n["night"]).dt.date

    # Prix par nuit
    per_night_price = {}
    rows = []
    for n in ns:
        c = int((df_n["night_date"] == n).sum())
        if c <= 0:
            rows.append({"Nuit": n.strftime("%a %d/%m"), "Inscrits": 0, "Prix / personne": ""})
            continue

        price = max(MIN_PER_PERSON, HOUSE_PER_NIGHT / c)
        per_night_price[n] = price
        rows.append({"Nuit": n.strftime("%a %d/%m"), "Inscrits": c, "Prix / personne": f"{price:.2f} €"})

    table_nuits = pd.DataFrame(rows)

    # Totaux par personne
    totals = {}
    nights_count = {}
    for n in ns:
        if n not in per_night_price:
            continue
        price = per_night_price[n]
        people = df_n[df_n["night_date"] == n]["name"].tolist()
        for p in people:
            totals[p] = totals.get(p, 0.0) + price
            nights_count[p] = nights_count.get(p, 0) + 1

    table_totaux = pd.DataFrame([{
        "Nom": p,
        "Nuits": nights_count.get(p, 0),
        "Total (€)": round(totals.get(p, 0.0), 2)
    } for p in sorted(totals.keys(), key=lambda x: x.lower())])

    return table_nuits, table_totaux


# ---------------- UI ----------------
st.set_page_config(page_title="Réservation couchages", layout="wide")
st.title("🛏️ Réservation couchages — nuits du 16 au 22 août 2026 (départ 23)")

st.info(
    f"💶 Prix maison : **{HOUSE_PER_NIGHT:.2f} € / nuit**\n\n"
    f"➡️ Prix par personne (par nuit) = **max({MIN_PER_PERSON:.2f} €, {HOUSE_PER_NIGHT:.2f}€ / nb de présents cette nuit)**\n"
    "✅ Donc **31€ est le minimum** si la maison est complète."
)

try:
    df = load_bookings()
except Exception as e:
    st.error("Impossible de lire la Google Sheet. Vérifie le déploiement Apps Script et le partage de la feuille.")
    st.stop()

tabs = st.tabs([d.strftime("%d/%m") for d in nights()])

for tab, d in zip(tabs, nights()):
    with tab:
        st.markdown(f"### {d.strftime('%A %d %B %Y').capitalize()} (nuit)")
        cols = st.columns(4)

        rooms_order = ["Chambre 1", "Chambre 2", "Chambre 3", "Dortoir"]
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
                            with st.form(key=f"f-{d}-{room}-{bed}", clear_on_submit=True):
                                n = st.text_input("Ton nom", placeholder="Ex : Auriane", label_visibility="collapsed")
                                ok = st.form_submit_button("Réserver")
                                if ok:
                                    if not n.strip():
                                        st.error("Mets ton nom 🙂")
                                    else:
                                        try:
                                            add_booking(d, room, bed, n)
                                            st.success("Réservé ✅")
                                            st.rerun()
                                        except Exception:
                                            st.error("Erreur d’enregistrement (ou couchage pris entre-temps). Recharge la page.")

st.divider()

st.subheader("💶 Calculs")
table_nuits, table_totaux = price_tables(df)
c1, c2 = st.columns(2)
with c1:
    st.markdown("#### Par nuit")
    st.dataframe(table_nuits, use_container_width=True)
with c2:
    st.markdown("#### Total par personne")
    st.dataframe(table_totaux, use_container_width=True)

st.divider()
st.subheader("Vue globale")
if df.empty:
    st.write("Aucune inscription pour l’instant.")
else:
    df2 = df.copy()
    df2["night"] = pd.to_datetime(df2["night"]).dt.strftime("%d/%m/%Y")
    st.dataframe(df2[["night", "room", "bed", "name"]].sort_values(["night", "room", "bed"]), use_container_width=True)
