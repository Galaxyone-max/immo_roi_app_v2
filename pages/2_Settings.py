
import streamlit as st
from utils import get_settings, save_settings

st.title("Paramètres & Pondérations")
st.caption("Ajustez les coûts, durées et poids des scores. Les réglages sont sauvegardés localement.")

if "user" not in st.session_state:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

s = get_settings()

st.subheader("Frais & Durées")
col = st.columns(3)
s["frais_achat_pct"] = col[0].slider("Frais d'achat %", 0.0, 0.12, float(s["frais_achat_pct"]), 0.005)
s["frais_vente_pct"] = col[1].slider("Frais de vente %", 0.0, 0.08, float(s["frais_vente_pct"]), 0.005)
s["duree_mois"]      = col[2].slider("Durée projet (mois)", 1, 24, int(s["duree_mois"]), 1)

col2 = st.columns(3)
s["taux_annuel"] = col2[0].slider("Taux annuel (coût capital)", 0.00, 0.20, float(s["taux_annuel"]), 0.005)
s["autres_frais_mensuels"] = col2[1].number_input("Frais mensuels (€)", 0, 5000, int(s["autres_frais_mensuels"]), 50)
s["risque_marche"] = col2[2].slider("Risque marché", 0.0, 0.5, float(s["risque_marche"]), 0.05)

st.subheader("Coût rénovation (€/m²)")
for k in ["à rénover","rafraîchir","bon état","très bon état","par_defaut"]:
    s["reno_map"][k] = st.number_input(k, 0, 2000, int(s["reno_map"][k]), 10)

st.subheader("Pondérations du score d'opportunité")
col3 = st.columns(3)
s["weights"]["w_roi"] = col3[0].slider("Poids ROI", 0.0, 1.0, float(s["weights"]["w_roi"]), 0.05)
s["weights"]["w_margin"] = col3[1].slider("Poids Marge", 0.0, 1.0, float(s["weights"]["w_margin"]), 0.05)
s["weights"]["w_risk"] = col3[2].slider("Poids (1-Risque)", 0.0, 1.0, float(s["weights"]["w_risk"]), 0.05)

if st.button("Enregistrer"):
    save_settings(s)
    st.success("Paramètres sauvegardés.")
