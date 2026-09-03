"""
Cahier de Mercato — demo Streamlit for the football market-value project.

Run from the project root:
    streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent
CSV_CANDIDATES = [
    ROOT / "data" / "processed" / "dataset_final.csv",
    ROOT / "dataset_final.csv",
    ROOT / "notebooks" / "dataset_final.csv",
]
MODEL_CANDIDATES = [
    ROOT / "models" / "modele_marche_joueur.pkl",
    ROOT / "modele_marche_joueur.pkl",
    ROOT / "model_et_visualisation_des _donnees" / "modele_marche_joueur.pkl",
    ROOT / "executed_notebooks" / "modele_marche_joueur.pkl",
]

FEATURE_COLS = [
    "position",
    "age",
    "country",
    "Buts",
    "xG",
    "Succ_dribbles",
    "Tacles",
    "Assists",
    "Passes_Reussies_Pct",
    "club",
    "league",
]
CAT_COLS = ["position", "country", "club", "league"]
NUM_COLS = ["age", "Buts", "xG", "Succ_dribbles", "Tacles", "Assists", "Passes_Reussies_Pct"]

LEAGUE_LABELS = {
    "premier_league": "Premier League",
    "la_liga": "La Liga",
    "bundesliga": "Bundesliga",
    "serie_a": "Serie A",
    "ligue_1": "Ligue 1",
}
POS_LABELS = {"F": "Attaquant", "M": "Milieu", "D": "Défenseur", "G": "Gardien"}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#D7DDD2", family="IBM Plex Sans, sans-serif"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Oswald:wght@500;600&display=swap");

        html, body, [class*="css"] { font-family: "IBM Plex Sans", sans-serif; }
        .stApp {
            background:
                radial-gradient(900px 420px at 8% -10%, rgba(214,255,58,.10), transparent 55%),
                radial-gradient(700px 380px at 100% 0%, rgba(184,92,42,.16), transparent 50%),
                repeating-linear-gradient(
                    -18deg,
                    rgba(214,255,58,.025) 0 2px,
                    transparent 2px 18px
                ),
                #0b100c;
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] {
            background: #101610;
            border-right: 1px solid rgba(214,255,58,.16);
        }
        .hero-kicker {
            letter-spacing: .28em;
            text-transform: uppercase;
            color: #d6ff3a;
            font-size: .74rem;
            font-weight: 600;
            margin-bottom: .35rem;
        }
        .hero-title {
            font-family: "Oswald", sans-serif;
            font-size: 3.1rem;
            line-height: .92;
            text-transform: uppercase;
            margin: 0 0 .6rem 0;
            color: #f3f7ee;
        }
        .hero-copy {
            max-width: 46rem;
            color: #b7c0b1;
            font-size: 1.02rem;
            margin-bottom: 1.4rem;
        }
        .stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 8px 0 22px; }
        .stat-card {
            border: 1px solid rgba(214,255,58,.18);
            background: rgba(20,27,21,.82);
            padding: 14px 16px;
            border-radius: 2px;
        }
        .stat-card span { display: block; color: #8f9889; font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; }
        .stat-card strong {
            font-family: "Oswald", sans-serif;
            font-size: 1.7rem;
            color: #f3f7ee;
        }
        .jersey {
            border: 1px solid rgba(214,255,58,.35);
            background: linear-gradient(180deg, rgba(214,255,58,.12), rgba(20,27,21,.9));
            padding: 22px 18px 16px;
            text-align: center;
            border-radius: 2px;
        }
        .jersey .label { letter-spacing: .22em; text-transform: uppercase; color: #d6ff3a; font-size: .7rem; }
        .jersey .value {
            font-family: "Oswald", sans-serif;
            font-size: 3.4rem;
            line-height: 1;
            color: #f3f7ee;
            margin: 8px 0 4px;
        }
        .jersey .hint { color: #8f9889; font-size: .85rem; }
        .note {
            color: #9aa394;
            font-size: .85rem;
            border-left: 3px solid #d6ff3a;
            padding-left: 10px;
            margin: 12px 0 4px;
        }
        @media (max-width: 900px) {
            .stat-row { grid-template-columns: 1fr 1fr; }
            .hero-title { font-size: 2.2rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def money(value: float) -> str:
    if pd.isna(value):
        return "—"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f} M€"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f} k€"
    return f"{value:.0f} €"


def league_label(code: str) -> str:
    return LEAGUE_LABELS.get(str(code), str(code).replace("_", " ").title())


def club_label(code: str) -> str:
    return str(code).replace("_", " ").title()


@st.cache_data(show_spinner=False)
def load_players() -> pd.DataFrame:
    path = next((p for p in CSV_CANDIDATES if p.exists()), None)
    if path is None:
        raise FileNotFoundError("dataset_final.csv introuvable.")
    df = pd.read_csv(path)
    df["market_value_raw"] = pd.to_numeric(
        df["market_value_raw"].astype(str).str.replace(r"[^0-9.]", "", regex=True),
        errors="coerce",
    )
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["league_label"] = df["league"].map(league_label)
    df["club_label"] = df["club"].map(club_label)
    df["position_label"] = df["position"].map(lambda x: POS_LABELS.get(str(x), str(x)))
    return df


def find_model_path() -> Path | None:
    return next((p for p in MODEL_CANDIDATES if p.exists()), None)


def _train_fallback(df: pd.DataFrame):
    work = df.dropna(subset=["market_value_raw"]).copy()
    X = work[FEATURE_COLS]
    y = work["market_value_raw"]
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUM_COLS),
            ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), CAT_COLS),
        ]
    )
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1)),
        ]
    )
    pipeline.fit(X, y)
    return pipeline


@st.cache_resource(show_spinner=False)
def load_predictor(df: pd.DataFrame):
    """Use the saved sklearn pipeline if present, otherwise train a compact fallback."""
    path = find_model_path()
    if path is not None:
        try:
            loaded = joblib.load(path)
            loaded.predict(pd.DataFrame([{
                "position": "F",
                "age": 24.0,
                "country": "France",
                "Buts": 10,
                "xG": 9.5,
                "Succ_dribbles": 30,
                "Tacles": 15,
                "Assists": 5,
                "Passes_Reussies_Pct": 82.0,
                "club": df["club"].iloc[0],
                "league": df["league"].iloc[0],
            }]))
            return loaded, f"modèle sauvegardé ({path.name})"
        except Exception:
            pass
    return _train_fallback(df), "modèle de démo (Random Forest entraîné sur dataset_final.csv)"


@st.cache_resource(show_spinner=False)
def similar_index(df: pd.DataFrame):
    matrix = df[NUM_COLS].fillna(0).to_numpy()
    scaler = StandardScaler()
    scaled = scaler.fit_transform(matrix)
    nn = NearestNeighbors(n_neighbors=6, metric="euclidean")
    nn.fit(scaled)
    return nn, scaler


def predict_value(model, row: dict) -> float:
    frame = pd.DataFrame([row])
    try:
        return float(model.predict(frame)[0])
    except Exception:
        # Saved notebook pipeline may expect extra leftover columns.
        extras = {"short_name": "Scout", "jersey_number": 9}
        extras.update(row)
        return float(model.predict(pd.DataFrame([extras]))[0])


def kpi_html(df: pd.DataFrame) -> str:
    return f"""
    <div class="stat-row">
      <div class="stat-card"><span>Joueurs</span><strong>{len(df):,}</strong></div>
      <div class="stat-card"><span>Ligues</span><strong>{df["league"].nunique()}</strong></div>
      <div class="stat-card"><span>Valeur médiane</span><strong>{money(df["market_value_raw"].median())}</strong></div>
      <div class="stat-card"><span>Plus haute cote</span><strong>{money(df["market_value_raw"].max())}</strong></div>
    </div>
    """


st.set_page_config(page_title="Cahier de Mercato", page_icon="⚽", layout="wide")
inject_css()

try:
    players = load_players()
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()

model, model_origin = load_predictor(players)
nn, nn_scaler = similar_index(players)

with st.sidebar:
    st.markdown("### Cahier de Mercato")
    st.caption("Desk de scouting pour la valeur de marché — projet Master Data / IA.")
    page = st.radio("Navigation", ["Bureau", "Scout", "Pipeline"], label_visibility="collapsed")
    st.markdown("---")
    st.caption(f"Source données : `{CSV_CANDIDATES[0].name}`")
    st.caption(f"Modèle : {model_origin}")

if page == "Bureau":
    st.markdown('<div class="hero-kicker">Saison scouting · 5 championnats</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Le prix d’un joueur<br>n’est pas un tableur.</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">Cahier de Mercato lit le dataset SofaScore du projet, '
        "compare les cotes observées, et estime une valeur à partir du même type de "
        "pipeline sklearn que le notebook (poste, âge, club, stats).</p>",
        unsafe_allow_html=True,
    )
    st.markdown(kpi_html(players), unsafe_allow_html=True)

    left, right = st.columns((1.25, 1), gap="large")
    with left:
        league_avg = (
            players.groupby("league_label", as_index=False)["market_value_raw"]
            .median()
            .sort_values("market_value_raw", ascending=True)
        )
        fig = px.bar(
            league_avg,
            x="market_value_raw",
            y="league_label",
            orientation="h",
            labels={"market_value_raw": "Valeur médiane (€)", "league_label": ""},
        )
        fig.update_traces(marker_color="#D6FF3A")
        fig.update_layout(**PLOTLY_LAYOUT, title="Cote médiane par ligue")
        st.plotly_chart(fig, width="stretch")

        pos_avg = players.groupby("position_label", as_index=False)["market_value_raw"].median()
        fig2 = px.bar(
            pos_avg,
            x="position_label",
            y="market_value_raw",
            labels={"market_value_raw": "Valeur médiane (€)", "position_label": "Poste"},
        )
        fig2.update_traces(marker_color="#E07A3D")
        fig2.update_layout(**PLOTLY_LAYOUT, title="Cote médiane par poste")
        st.plotly_chart(fig2, width="stretch")

    with right:
        st.markdown("#### Tableau d’affichage")
        top = players.nlargest(8, "market_value_raw")[
            ["name", "club_label", "league_label", "position_label", "age", "Buts", "market_value_raw"]
        ].copy()
        top["market_value_raw"] = top["market_value_raw"].map(money)
        top.columns = ["Joueur", "Club", "Ligue", "Poste", "Âge", "Buts", "Cote"]
        st.dataframe(top, hide_index=True, width="stretch")

elif page == "Scout":
    st.markdown('<div class="hero-kicker">Fiche joueur</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Estimer une cote</h1>', unsafe_allow_html=True)
    st.caption("Les champs correspondent aux features du notebook de modélisation.")

    leagues = sorted(players["league"].dropna().unique().tolist())
    clubs_by_league = {
        league: sorted(players.loc[players["league"] == league, "club"].dropna().unique().tolist())
        for league in leagues
    }
    countries = sorted(players["country"].dropna().astype(str).unique().tolist())

    form, result = st.columns((1.05, 1), gap="large")
    with form:
        position = st.selectbox(
            "Poste",
            options=list(POS_LABELS.keys()),
            format_func=lambda x: f"{x} · {POS_LABELS[x]}",
        )
        age = st.slider("Âge", 16, 40, 24)
        league = st.selectbox("Ligue", leagues, format_func=league_label)
        club_options = clubs_by_league.get(league) or sorted(players["club"].unique())
        club = st.selectbox("Club", club_options, format_func=club_label)
        default_country = "France" if "France" in countries else countries[0]
        country = st.selectbox("Nationalité", countries, index=countries.index(default_country))
        c1, c2 = st.columns(2)
        with c1:
            buts = st.number_input("Buts", 0, 60, 10)
            dribbles = st.number_input("Dribbles réussis", 0, 200, 30)
            assists = st.number_input("Passes décisives", 0, 40, 5)
        with c2:
            xg = st.number_input("xG", 0.0, 50.0, 9.5, step=0.1)
            tacles = st.number_input("Tacles", 0, 200, 15)
            passes = st.slider("Passes réussies (%)", 0.0, 100.0, 82.0)
        submitted = st.button("Évaluer la fiche", type="primary", width="stretch")

    payload = {
        "position": position,
        "age": float(age),
        "country": country,
        "Buts": int(buts),
        "xG": float(xg),
        "Succ_dribbles": int(dribbles),
        "Tacles": int(tacles),
        "Assists": int(assists),
        "Passes_Reussies_Pct": float(passes),
        "club": club,
        "league": league,
    }

    with result:
        if submitted or "last_pred" in st.session_state:
            if submitted:
                pred = max(0.0, predict_value(model, payload))
                st.session_state.last_pred = pred
                st.session_state.last_payload = payload
            pred = st.session_state.last_pred
            st.markdown(
                f"""
                <div class="jersey">
                  <div class="label">Estimation modèle</div>
                  <div class="value">{money(pred)}</div>
                  <div class="hint">{POS_LABELS.get(st.session_state.last_payload["position"])}
                  · {int(st.session_state.last_payload["age"])} ans
                  · {club_label(st.session_state.last_payload["club"])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            vector = np.array([[st.session_state.last_payload[c] for c in NUM_COLS]], dtype=float)
            distances, indices = nn.kneighbors(nn_scaler.transform(vector))
            twins = players.iloc[indices[0]].copy()
            twins["distance"] = distances[0]
            twins = twins[twins["name"].notna()].head(5)
            twins["Écart profil"] = twins["distance"].map(lambda d: f"{d:.2f}")
            twins["Cote réelle"] = twins["market_value_raw"].map(money)
            st.markdown("#### Profils proches dans le dataset")
            st.dataframe(
                twins[["name", "club_label", "position_label", "age", "Buts", "Cote réelle", "Écart profil"]].rename(
                    columns={"name": "Joueur", "club_label": "Club", "position_label": "Poste", "age": "Âge"}
                ),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("Remplis la fiche à gauche, puis lance l’évaluation.")
            fig = go.Figure(
                go.Indicator(
                    mode="number",
                    value=players["market_value_raw"].median(),
                    number={"valueformat": ",.0f", "suffix": " €"},
                    title={"text": "Repère : médiane du dataset"},
                )
            )
            fig.update_layout(**PLOTLY_LAYOUT, height=220)
            st.plotly_chart(fig, width="stretch")

else:
    st.markdown('<div class="hero-kicker">Dossier projet</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">Ce que fait le pipeline</h1>', unsafe_allow_html=True)

    steps = [
        ("01 · Collecte", "Notebooks SofaScore : effectifs par club + stats des 5 ligues."),
        ("02 · Transformation", "Pandas fusionne identité et stats, nettoie les noms, produit dataset_final.csv."),
        ("03 · Stockage", "Docker Compose + PostgreSQL 16, tables players / player_stats / players_ml."),
        ("04 · Modèle", "Sklearn : preprocessing, Random Forest, prédiction de market_value_raw."),
        ("05 · Démo", "Cette app Streamlit : lecture CSV, estimation, joueurs comparables."),
    ]
    for title, body in steps:
        st.markdown(f"**{title}**  \n{body}")
