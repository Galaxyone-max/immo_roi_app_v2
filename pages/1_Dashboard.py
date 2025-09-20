
import streamlit as st, pandas as pd, numpy as np
from utils import get_settings, compute_comps_ppm2, deal_metrics
from utils import import_listings_from_csv

st.title("Tableau de bord")
st.caption("Chargez vos CSV, filtrez et classez les opportunités.")

if "user" not in st.session_state:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

settings = get_settings()
params = dict(
    frais_achat_pct=settings["frais_achat_pct"],
    frais_vente_pct=settings["frais_vente_pct"],
    duree_mois=settings["duree_mois"],
    taux_annuel=settings["taux_annuel"],
    autres_frais_mensuels=settings["autres_frais_mensuels"],
    risque_marche=settings["risque_marche"]
)
reno_map = settings["reno_map"]
weights = settings["weights"]

col = st.columns(2)
with col[0]:
    props_file = st.file_uploader("Propriétés (CSV)", type=["csv"], key="props_dash")
with col[1]:
    comps_file = st.file_uploader("Comparables (CSV)", type=["csv"], key="comps_dash")

if props_file and comps_file:
    props_df = pd.read_csv(props_file)
    comps_df = pd.read_csv(comps_file)
else:
    st.info("Importez deux CSV pour commencer.")
    st.stop()

comps_stats = compute_comps_ppm2(comps_df)
default_ppm2 = (comps_df["prix_vente"].sum() / comps_df["surface_m2"].sum()) if len(comps_df)>0 else 3000.0
df = deal_metrics(props_df, comps_stats, default_ppm2, reno_map, params, weights)

st.subheader("Filtres")
c = st.columns(6)
min_roi = c[0].slider("ROI min", 0.0, 0.5, 0.10, 0.01)
min_marge = c[1].number_input("Marge brute min (€)", 0, 500000, 20000, 1000)
max_risk = c[2].slider("Risk max", 0.0, 2.0, 1.0, 0.05)
ville_filter = c[3].text_input("Ville contient", "")
quartier_filter = c[4].text_input("Quartier contient", "")
min_surface = c[5].number_input("Surface min (m²)", 0, 1000, 0, 5)

view = df.copy()
view = view[view["roi"]>=min_roi]
view = view[view["marge_brute"]>=min_marge]
view = view[view["risk_score"]<=max_risk]
if ville_filter:
    view = view[view["ville"].astype(str).str.contains(ville_filter.strip().lower(), na=False)]
if quartier_filter:
    view = view[view["quartier"].astype(str).str.contains(quartier_filter.strip().lower(), na=False)]
if min_surface>0:
    view = view[view["surface_m2"]>=min_surface]

cols_show = ["id","adresse","ville","quartier","surface_m2","prix_achat","etat",
             "arv_estime","cout_renov","frais_achat","frais_vente","holding_costs",
             "cout_total","marge_brute","roi","risk_score","opportunity_score"]

fmt_money = lambda x: f"€{x:,.0f}".replace(",", " ").replace(".", ",")
fmt_pct = lambda x: f"{x*100:.1f}%"
fmt_num = lambda x: f"{x:.0f}"

st.write("### Résultats")
if len(view)==0:
    st.info("Aucun résultat avec ces filtres.")
else:
    show = view[cols_show].copy()
    show["prix_achat"] = show["prix_achat"].apply(fmt_money)
    for c2 in ["arv_estime","cout_renov","frais_achat","frais_vente","holding_costs","cout_total","marge_brute"]:
        show[c2] = show[c2].apply(fmt_money)
    show["roi"] = show["roi"].apply(fmt_pct)
    show["surface_m2"] = show["surface_m2"].apply(fmt_num)
    show["risk_score"] = show["risk_score"].map(lambda x: f"{x:.2f}")
    st.dataframe(show, use_container_width=True, hide_index=True)

st.write("### Top 10 par score")
top = view.sort_values("opportunity_score", ascending=False).head(10)
if len(top)>0:
    show = top[cols_show].copy()
    show["prix_achat"] = show["prix_achat"].apply(fmt_money)
    for c2 in ["arv_estime","cout_renov","frais_achat","frais_vente","holding_costs","cout_total","marge_brute"]:
        show[c2] = show[c2].apply(fmt_money)
    show["roi"] = show["roi"].apply(fmt_pct)
    show["surface_m2"] = show["surface_m2"].apply(fmt_num)
    show["risk_score"] = show["risk_score"].map(lambda x: f"{x:.2f}")
    st.dataframe(show, use_container_width=True, hide_index=True)

st.download_button("Exporter analyses (CSV)", view.to_csv(index=False).encode("utf-8"), "analyses_filtrees.csv", "text/csv")
