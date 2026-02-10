
import streamlit as st
import requests
import pandas as pd

SCRIPT_URL = "COLLE ICI TON LIEN /exec"

st.title("Réservation couchages")

def load():
    r = requests.get(SCRIPT_URL)
    return pd.DataFrame(r.json())

def save(night, room, bed, name):
    requests.post(SCRIPT_URL, json={
        "night": night,
        "room": room,
        "bed": bed,
        "name": name
    })

df = load()

st.write("Inscriptions actuelles :")
st.dataframe(df)

st.subheader("Nouvelle réservation")

night = st.text_input("Date (ex: 2026-08-16)")
room = st.text_input("Chambre")
bed = st.text_input("Couchage")
name = st.text_input("Nom")

if st.button("Réserver"):
    save(night, room, bed, name)
    st.rerun()

