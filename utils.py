import os, json, hashlib, time, pandas as pd, numpy as np
import tempfile, pathlib

APP_DIR = os.path.dirname(__file__)
# ÉCRITURE DANS UN DOSSIER TEMP (autorisé sur Streamlit Cloud)
DATA_DIR = os.path.join(tempfile.gettempdir(), "immo_roi_data")
pathlib.Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "frais_achat_pct": 0.07,
    "frais_vente_pct": 0.04,
    "duree_mois": 6,
    "taux_annuel": 0.06,
    "autres_frais_mensuels": 200,
    "risque_marche": 0.2,
    "reno_map": {
        "à rénover": 800,
        "rafraîchir": 450,
        "bon état": 150,
        "très bon état": 50,
        "par_defaut": 400
    },
    "weights": {
        "w_roi": 0.6, "w_margin": 0.3, "w_risk": 0.1
    }
}

def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def get_settings():
    s = _read_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    # fill missing keys
    for k,v in DEFAULT_SETTINGS.items():
        if k not in s:
            s[k] = v
    return s

def save_settings(s):
    _write_json(SETTINGS_FILE, s)

def hash_pwd(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def get_users():
    users = _read_json(USERS_FILE, {})
    return users

def add_user(email: str, pwd: str):
    users = get_users()
    if email in users:
        return False, "Utilisateur déjà existant"
    users[email] = {"pwd": hash_pwd(pwd), "created_at": time.time()}
    _write_json(USERS_FILE, users)
    return True, "OK"

def verify_user(email: str, pwd: str):
    users = get_users()
    if email not in users:
        return False
    return users[email]["pwd"] == hash_pwd(pwd)

def get_projects():
    return _read_json(PROJECTS_FILE, {})

def save_project(owner_email: str, name: str, df_dict: dict):
    allp = get_projects()
    key = f"{owner_email}::{name}"
    allp[key] = df_dict
    _write_json(PROJECTS_FILE, allp)

def load_project(owner_email: str, name: str):
    allp = get_projects()
    return allp.get(f"{owner_email}::{name}", None)

def list_user_projects(owner_email: str):
    allp = get_projects()
    out = []
    for k in allp.keys():
        if k.startswith(owner_email+"::"):
            out.append(k.split("::",1)[1])
    return sorted(out)

# ---- Core analytics (same logic as v1, modularized) ----
def compute_comps_ppm2(comps_df, area_col="surface_m2", price_col="prix_vente", group_cols=("ville","quartier")):
    df = comps_df.copy()
    for c in group_cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.lower()
        else:
            df[c] = "all"
    df["ppm2"] = df[price_col] / df[area_col]
    agg = (
        df.groupby(list(group_cols))["ppm2"]
        .agg(["count","median","mean","std"])
        .reset_index()
        .rename(columns={"median":"ppm2_med","mean":"ppm2_mean","std":"ppm2_std","count":"nb_comps"})
    )
    return agg

def est_arv(row, comps_stats, default_ppm2, group_cols=("ville","quartier")):
    key = tuple(str(row.get(c,"all")).strip().lower() for c in group_cols)
    sub = comps_stats
    for i, c in enumerate(group_cols):
        sub = sub[sub[c]==key[i]]
    ppm2 = sub["ppm2_med"].values[0] if len(sub)>0 and not np.isnan(sub["ppm2_med"].values[0]) else default_ppm2
    return ppm2 * float(row.get("surface_m2", np.nan))

def renovation_cost(row, reno_ppm2_map):
    cond = str(row.get("etat","")).strip().lower()
    base = reno_ppm2_map.get(cond, reno_ppm2_map.get("par_defaut", 400))
    surface = float(row.get("surface_m2", np.nan))
    return base * surface if not np.isnan(surface) else np.nan

def holding_costs(months, price, rate_annual, other_monthly):
    intr = price * (rate_annual/12.0) * months
    return intr + other_monthly * months

def deal_metrics(props_df, comps_stats, default_ppm2, reno_map, params, weights):
    df = props_df.copy()
    for c in ("ville","quartier","etat"):
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.lower()
    df["arv_estime"] = df.apply(lambda r: est_arv(r, comps_stats, default_ppm2), axis=1)
    df["cout_renov"] = df.apply(lambda r: renovation_cost(r, reno_map), axis=1)
    df["frais_achat"] = df["prix_achat"] * params.get("frais_achat_pct",0.07)
    df["frais_vente"] = df["arv_estime"] * params.get("frais_vente_pct",0.04)
    df["holding_costs"] = df.apply(lambda r: holding_costs(params.get("duree_mois",6), r["prix_achat"], params.get("taux_annuel",0.06), params.get("autres_frais_mensuels",200)), axis=1)
    df["cout_total"] = df["prix_achat"] + df["cout_renov"] + df["frais_achat"] + df["frais_vente"] + df["holding_costs"]
    df["marge_brute"] = df["arv_estime"] - df["cout_total"]
    df["roi"] = df["marge_brute"] / df["cout_total"]
    df["ppm2_achat"] = df["prix_achat"] / df["surface_m2"]
    df["ppm2_arv"] = df["arv_estime"] / df["surface_m2"]
    reno_intensity = df["cout_renov"] / (df["surface_m2"]*max(reno_map.get("par_defaut",400),1))
    leverage = df["prix_achat"] / df["arv_estime"]
    market_vol = params.get("risque_marche", 0.2)
    df["risk_score"] = (0.5*reno_intensity.fillna(0) + 0.4*leverage.fillna(0) + 0.1*market_vol).clip(0, 2.0)
    w_roi = float(weights.get("w_roi",0.6))
    w_margin = float(weights.get("w_margin",0.3))
    w_risk = float(weights.get("w_risk",0.1))
    df["opportunity_score"] = ( (df["roi"].fillna(0)).rank(pct=True) * w_roi
                              + (df["marge_brute"].fillna(0)).rank(pct=True) * w_margin
                              + (1 - df["risk_score"].fillna(0).rank(pct=True)) * w_risk )
    return df

# ---- Import helper stub ----
def import_listings_from_csv(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path)

def save_example_csvs():
    props = pd.DataFrame({
        "id":[1,2,3],
        "adresse":["Rue Exemple 1","Rue Exemple 2","Rue Exemple 3"],
        "ville":["bruxelles","bruxelles","anvers"],
        "quartier":["ixelles","saint-gilles","zuid"],
        "surface_m2":[65,90,45],
        "prix_achat":[210000, 295000, 145000],
        "etat":["à rénover","rafraîchir","bon état"]
    })
    comps = pd.DataFrame({
        "ville":["bruxelles","bruxelles","anvers","bruxelles","anvers","bruxelles"],
        "quartier":["ixelles","saint-gilles","zuid","ixelles","zuid","saint-gilles"],
        "surface_m2":[60,85,50,70,40,95],
        "prix_vente":[360000, 525000, 210000, 455000, 195000, 560000]
    })
    props.to_csv(os.path.join(DATA_DIR,"modele_proprietes.csv"), index=False)
    comps.to_csv(os.path.join(DATA_DIR,"modele_comparables.csv"), index=False)
