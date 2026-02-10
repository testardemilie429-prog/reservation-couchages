from datetime import date, timedelta
import pandas as pd
import streamlit as st
import requests

SSCRIPT_URL = "https://script.google.com/macros/s/AKfycbzvzzcDs80mU9VPnMIKEVbwm1MRvOVWJ3ETakOZUEiUr_w5BvpL_gHQYXM9OcYHVr6Z/exec"

"
TOKEN = "CHANGE-MOI-123"

START_NIGHT = date(2026, 8, 16)
END_NIGHT_EXCL = date(2026, 8, 23)

BLOCKS = {
    "Chambre 1": ["Couchage 1", "Couchage 2"],
    "Chambre 2": ["Couchage 1", "Couchage 2"],
    "Chambre 3": ["Couchage 1", "Couchage 2"],
    "Dortoir":   ["Couchage 1", "Couchage 2", "Couchage 3", "Couchage 4"],
}

def nights():
    d = START_NIGHT
    out = []
    while d < END_NIGHT_EXCL:
        out.append(d)
        d += timedelta(days=1)
    return out

def load_bookings():
    r = requests.get(SCRIPT_URL, timeout=20, allow_redirects=True)
    r.raise_for_status()

    # Debug lisible si ce n'est pas du JSON
    ct = r.headers.get("content-type", "")
    if "application/json" not in ct:
        # on affiche les 200 premiers caractères pour comprendre
        raise Exception(f"Réponse non-JSON (content-type={ct}) : {r.text[:200]}")

    return pd.DataFrame(r.json())


def add_booking(night, room, bed, name):
    payload = {
        "token": TOKEN,
        "night": night.isoformat(),
        "room": room,
        "bed": bed,
        "name": name.strip(),
    }
    r = requests.post(SCRIPT_URL, json=payload, timeout=20)
    r.raise_for_status()

def is_taken(df, night, room, bed):
    if df is None or df.empty:
        return None
    x = df[(df["night"] == night.isoformat()) & (df["room"] == room) & (df["bed"] == bed)]
    if x.empty:
        return None
    return str(x.iloc[0]["name"])

st.set_page_config(page_title="Réservation couchages", layout="wide")
st.title("🛏️ Réservation couchages — nuits du 16 au 22 août 2026 (départ 23)")

try:
    df = load_bookings()
except Exception as e:
    st.error("Impossible de lire la Google Sheet.")
    st.exception(e)
    st.stop()

tabs = st.tabs([d.strftime("%d/%m") for d in nights()])

for tab, d in zip(tabs, nights()):
    with tab:
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
                            with st.form(key=f"{d}-{room}-{bed}", clear_on_submit=True):
                                n = st.text_input("Ton nom", label_visibility="collapsed")
                                ok = st.form_submit_button("Réserver")
                                if ok:
                                    if not n.strip():
                                        st.error("Mets ton nom 🙂")
                                    else:
                                        add_booking(d, room, bed, n)
                                        st.rerun()





