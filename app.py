import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st

DB_PATH = "reservations.db"

TOTAL_WEEK = 2154.0
NIGHTS_COUNT = 7
HOUSE_PER_NIGHT = TOTAL_WEEK / NIGHTS_COUNT  # 307.71
MIN_PER_PERSON = 31.0


# Nuits affichées : 16 -> 22 août 2026 (départ le 23)
START_NIGHT = date(2026, 8, 16)
END_NIGHT_EXCL = date(2026, 8, 23)  # exclu (dernière nuit = 22)

# Couchages (comme ta photo)
BEDS = [
    ("Chambre 1", "Couchage 1"),
    ("Chambre 1", "Couchage 2"),
    ("Chambre 2", "Couchage 1"),
    ("Chambre 2", "Couchage 2"),
    ("Chambre 3", "Couchage 1"),
    ("Chambre 3", "Couchage 2"),
    ("Dortoir", "Couchage 1"),
    ("Dortoir", "Couchage 2"),
    ("Dortoir", "Couchage 3"),
    ("Dortoir", "Couchage 4"),
]

def nights():
    d = START_NIGHT
    out = []
    while d < END_NIGHT_EXCL:
        out.append(d)
        d += timedelta(days=1)
    return out

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bed_bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            night TEXT NOT NULL,
            room TEXT NOT NULL,
            bed TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(night, room, bed)
        )
    """)
    conn.commit()
    conn.close()

def load_bookings():
    conn = get_conn()
    df = pd.read_sql_query("SELECT id, night, room, bed, name, created_at FROM bed_bookings", conn)
    conn.close()
    return df

def add_booking(night: date, room: str, bed: str, name: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO bed_bookings(night, room, bed, name, created_at) VALUES (?,?,?,?,?)",
        (night.isoformat(), room, bed, name.strip(), datetime.now().isoformat(timespec="seconds"))
    )
    conn.commit()
    conn.close()

def delete_booking(res_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM bed_bookings WHERE id = ?", (res_id,))
    conn.commit()
    conn.close()

def get_booking(df, night: date, room: str, bed: str):
    x = df[(df["night"] == night.isoformat()) & (df["room"] == room) & (df["bed"] == bed)]
    if x.empty:
        return None, None
    return x.iloc[0]["name"], int(x.iloc[0]["id"])

# ---------- PRIX ----------
def price_tables(df: pd.DataFrame):
    ns = nights()

    # On prépare un df avec date propre
    if df.empty:
        table_nuits = pd.DataFrame([{
            "Nuit": n.strftime("%a %d/%m"),
            "Inscrits": 0,
            "Prix / personne": "",
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
        if c > 0:
            price = max(MIN_PER_PERSON, HOUSE_PER_NIGHT / c)
            per_night_price[n] = price
            price_str = f"{price:.2f} €"
        else:
            price_str = ""
        rows.append({
            "Nuit": n.strftime("%a %d/%m"),
            "Inscrits": c,
            "Prix / personne": price_str
        })
    table_nuits = pd.DataFrame(rows)

    # Total par personne = somme des prix des nuits où la personne est présente
    totals = {}
    nights_count = {}
    for n in ns:
        people = df_n[df_n["night_date"] == n]["name"].tolist()
        if not people:
            continue
        price = per_night_price[n]
        for p in people:
            totals[p] = totals.get(p, 0.0) + price
            nights_count[p] = nights_count.get(p, 0) + 1

    table_totaux = pd.DataFrame([{
        "Nom": p,
        "Nuits": nights_count.get(p, 0),
        "Total (€)": round(totals.get(p, 0.0), 2)
    } for p in sorted(totals.keys(), key=lambda x: x.lower())])

    return table_nuits, table_totaux

# ---------- UI ----------
st.set_page_config(page_title="Couchages 16→23 août 2026", layout="wide")
st.title("🛏️ Couchages — nuits du 16 au 22 août 2026 (départ 23)")
st.info(
    f"💶 **Prix total maison** : {TOTAL_HOUSE_PER_NIGHT_EUR:.2f} € / nuit.\n\n"
    "➡️ **Prix par personne = (prix nuit) / (nombre d’inscrits cette nuit)**. "
    "Donc le tarif est **évolutif** tant que tout le monde n’est pas inscrit."
)

init_db()
df = load_bookings()

# Navigation par jours (onglets)
tabs = st.tabs([d.strftime("%d/%m") for d in nights()])

for tab, d in zip(tabs, nights()):
    with tab:
        st.markdown(f"### {d.strftime('%A %d %B %Y').capitalize()} (nuit)")
        cols = st.columns(4)

        blocks = [
            ("Chambre 1", [("Couchage 1", cols[0]), ("Couchage 2", cols[0])]),
            ("Chambre 2", [("Couchage 1", cols[1]), ("Couchage 2", cols[1])]),
            ("Chambre 3", [("Couchage 1", cols[2]), ("Couchage 2", cols[2])]),
            ("Dortoir",   [("Couchage 1", cols[3]), ("Couchage 2", cols[3]), ("Couchage 3", cols[3]), ("Couchage 4", cols[3])]),
        ]

        for room, bed_list in blocks:
            with bed_list[0][1]:
                st.subheader(room)
                for bed, _ in bed_list:
                    name, res_id = get_booking(df, d, room, bed)

                    box = st.container(border=True)
                    with box:
                        st.write(f"**{bed}**")
                        if name:
                            st.success(f"Pris par : {name}")
                            if st.button("🗑️ Supprimer", key=f"del-{d}-{room}-{bed}"):
                                delete_booking(res_id)
                                st.rerun()
                        else:
                            with st.form(key=f"form-{d}-{room}-{bed}", clear_on_submit=True):
                                n = st.text_input("Ton nom", placeholder="Ex : Auriane", label_visibility="collapsed")
                                ok = st.form_submit_button("Réserver ce couchage")
                                if ok:
                                    if not n.strip():
                                        st.error("Mets ton nom 🙂")
                                    else:
                                        try:
                                            add_booking(d, room, bed, n)
                                            st.success("Réservé ✅")
                                            st.rerun()
                                        except sqlite3.IntegrityError:
                                            st.error("Oups : quelqu’un vient de prendre ce couchage.")

st.divider()

# TABLES PRIX
st.subheader("💶 Répartition du prix (évolutif)")
table_nuits, table_totaux = price_tables(df)

c1, c2 = st.columns(2)
with c1:
    st.markdown("#### Par nuit")
    st.dataframe(table_nuits, use_container_width=True)

with c2:
    st.markdown("#### Total par personne")
    if table_totaux.empty:
        st.write("Aucun total pour l’instant (personne inscrit).")
    else:
        st.dataframe(table_totaux, use_container_width=True)

st.divider()

st.subheader("Vue globale (toutes les inscriptions)")
if df.empty:
    st.write("Aucune inscription pour l’instant.")
else:
    df2 = df.copy()
    df2["night"] = pd.to_datetime(df2["night"]).dt.strftime("%d/%m/%Y")
    st.dataframe(df2[["night", "room", "bed", "name"]].sort_values(["night","room","bed"]), use_container_width=True)


