
import streamlit as st, pandas as pd
from utils import save_project, load_project, list_user_projects, get_settings, compute_comps_ppm2, deal_metrics

st.title("Projets & Sauvegardes")

if "user" not in st.session_state:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

user = st.session_state["user"]
s = get_settings()
params = dict(
    frais_achat_pct=s["frais_achat_pct"],
    frais_vente_pct=s["frais_vente_pct"],
    duree_mois=s["duree_mois"],
    taux_annuel=s["taux_annuel"],
    autres_frais_mensuels=s["autres_frais_mensuels"],
    risque_marche=s["risque_marche"]
)
reno_map = s["reno_map"]
weights = s["weights"]

st.subheader("Sauvegarder un projet")
name = st.text_input("Nom du projet")
props_file = st.file_uploader("Propriétés (CSV)", type=["csv"], key="props_proj")
comps_file = st.file_uploader("Comparables (CSV)", type=["csv"], key="comps_proj")
if st.button("Analyser & sauvegarder") and name and props_file and comps_file:
    props_df = pd.read_csv(props_file)
    comps_df = pd.read_csv(comps_file)
    comps_stats = compute_comps_ppm2(comps_df)
    default_ppm2 = (comps_df["prix_vente"].sum() / comps_df["surface_m2"].sum()) if len(comps_df)>0 else 3000.0
    out = deal_metrics(props_df, comps_stats, default_ppm2, reno_map, params, weights)
    save_project(user, name, {
        "props": props_df.to_dict(orient="list"),
        "comps": comps_df.to_dict(orient="list"),
        "analyses": out.to_dict(orient="list")
    })
    st.success(f"Projet '{name}' sauvegardé.")

st.subheader("Charger un projet")
existing = list_user_projects(user)
if not existing:
    st.info("Aucun projet sauvegardé pour le moment.")
else:
    sel = st.selectbox("Sélectionner", existing)
    if st.button("Charger"):
        prj = load_project(user, sel)
        if prj:
            analyses = pd.DataFrame(prj["analyses"])
            st.dataframe(analyses.head(50), use_container_width=True, hide_index=True)
            st.download_button("Exporter analyses (CSV)", analyses.to_csv(index=False).encode("utf-8"), f"{sel}_analyses.csv", "text/csv")
