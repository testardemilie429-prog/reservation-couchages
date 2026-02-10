from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
import requests

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwE-zsX0D_zE0L3hkmUV9IkWKLVbSS24khntToqKLUuiK0M-RBD1KWbCrxI7aI6peKt/exec"
TOKEN = "CHANGE-MOI-123"

START_NIGHT = date(2026, 8, 16)
END_NIGHT_EXCL = date(2026, 8, 23)

BLOCKS = {
    "Chambre 1": ["Couchage 1", "Couchage 2"],
    "Chambre 2": ["Couchage 1", "Couchage 2"],
    "Chambre 3": ["Couchage 1", "Couchage 2"],
    "Dortoir":   ["Couchage 1", "Couchage 2", "Couchage 3", "Couchage 4"],
}

TOTAL_WEEK = 2154.0
NIGHTS_COUNT = 7
HOUSE_PER_NIGHT = TOTAL_WEEK / NIGHTS_COUNT
MIN_PER_PERSON = 31.0


def nights():
    d = START_NIGHT
    out = []
    while d < END_NIGHT_EXCL:
        out.append(d)
        d += timedelta(days=1)
    return out


def load_bookings():
    r = requests.get(SCRIPT_URL, timeout=20)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data)


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
    x = df[(df["night"] == night.isoformat()) & (df["room"] == room) & (df["bed"] == bed)]
    if x.empty:
        return None
    return str(x.iloc[0]["name"])


st.set_page_config(page_title="Réservation couchages", layout="wide")
st.title("🛏️ Réservation couchages — nuits du 16 au 22 août 2026")

try:
    df = load_bookings()
except:
    st.error("Impossible de lire la Google Sheet.")
    st.stop()

tabs = st.tabs([d.strftime("%d/%m") for d in nights()])

for tab, d in zip(tabs, nights()):
    with tab:
        cols = st.columns(4)
        for i, (room, beds) in enumerate(BLOCKS.items()):
            with cols[i]:
                st.subheader(room)
                for bed in beds:
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
                                if ok and n.strip():
                                    add_booking(d, room, bed, n)
                                    st.rerun()
