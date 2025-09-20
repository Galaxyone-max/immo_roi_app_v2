
import streamlit as st
import pandas as pd
import numpy as np
from utils import get_users, add_user, verify_user, get_settings, save_settings, save_example_csvs

st.set_page_config(page_title="ImmoROI v2", layout="wide")
st.title("ImmoROI – Flip Scanner (v2)")
st.caption("Appli multi‑pages avec connexion, paramètres persistants et sauvegarde de projets (offline).")

# Onboarding / Auth
mode = st.sidebar.radio("Compte", ["Se connecter","Créer un compte"])
email = st.sidebar.text_input("Email")
pwd = st.sidebar.text_input("Mot de passe", type="password")

if mode=="Créer un compte":
    if st.sidebar.button("Créer"):
        ok, msg = add_user(email, pwd)
        if ok:
            st.success("Compte créé. Vous pouvez vous connecter.")
        else:
            st.error(msg)

if st.sidebar.button("Connexion"):
    if verify_user(email, pwd):
        st.session_state["user"] = email
        st.success("Connecté.")
    else:
        st.error("Identifiants invalides.")

if "user" not in st.session_state:
    st.info("Connectez‑vous pour accéder aux pages (barre latérale : **Pages**).")
    st.write("Téléchargez des CSV exemples pour démarrer :")
    if st.button("Générer CSV exemples"):
        save_example_csvs()
        st.success("Fichiers créés dans /data : modele_proprietes.csv, modele_comparables.csv")
else:
    st.success(f"Connecté en tant que {st.session_state['user']}")
    st.markdown("Utilisez le menu **Pages** (en haut) pour naviguer.")
