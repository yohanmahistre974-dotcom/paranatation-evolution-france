"""
Évolution & Perspectives de la Para Natation en France
Dashboard pour Jason Denayer — Fédération Française Handisport
Développé par Yohan Mahistre — Data Scientist & IA
"""

import re

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from data_loader import load_medals, load_medalists, load_ffh

# ============================================================
# Configuration
# ============================================================
st.set_page_config(
    page_title="Para Natation France — Évolution",
    page_icon=":swimmer:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Palette variée (lisible sur fond sombre)
AQUA = [
    "#00BCD4", "#0288D1", "#4DD0E1", "#26C6DA", "#00ACC1",
    "#0097A7", "#00838F", "#006064", "#80DEEA", "#B2EBF2",
]
NATION_COLORS = [
    "#FFD166", "#06D6A0", "#EF476F", "#FFC43D", "#F77F00",
    "#9B5DE5", "#F15BB5", "#1B9AAA", "#00BCD4", "#118AB2",
]
PLOTLY_STYLE = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#FAFAFA"),
    colorway=NATION_COLORS,
)
FRANCE_COLOR = "#0055A4"  # Bleu France — Les Bleus
GOLD = "#FFD700"
SILVER = "#C0C0C0"
BRONZE = "#CD7F32"

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { color: #00BCD4; }
    .footer { text-align: center; color: #80DEEA; padding: 20px 0; font-size: 0.85em; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Utilitaires
# ============================================================
def apply_style(fig):
    """Applique le thème Plotly aquatique."""
    fig.update_layout(**PLOTLY_STYLE)
    return fig


def _int_yaxis(fig):
    """Forcer l'axe Y en entiers (pas de 0.5, 1.5…)."""
    all_y = []
    for t in fig.data:
        if hasattr(t, "y") and t.y is not None:
            all_y.extend([v for v in t.y if v is not None])
    if not all_y:
        return
    mx = max(all_y)
    if mx <= 20:
        fig.update_yaxes(dtick=1)
    elif mx <= 50:
        fig.update_yaxes(dtick=5)
    else:
        fig.update_yaxes(dtick=max(1, round(mx / 10)))


def _paralympic_tickaxis(years):
    """Config axe X pour n'afficher que les années paralympiques."""
    yrs = sorted(set(years))
    return dict(tickmode="array", tickvals=yrs, ticktext=[str(int(y)) for y in yrs])


def _highlight_france(fig):
    """Met en avant la France dans un graphique ligne multi-nations."""
    for trace in fig.data:
        if trace.name == "France":
            trace.update(
                line=dict(width=6, color=FRANCE_COLOR),
                marker=dict(color=FRANCE_COLOR, size=10),
            )


def class_sort_key(cls) -> tuple:
    """Tri naturel des classes S1 < S2 < ... < SB1 < ... < SM14."""
    if pd.isna(cls):
        return (3, 99)
    m = re.match(r"^(SB|SM|S)(\d+)$", str(cls))
    if not m:
        return (3, 99)
    order = {"S": 0, "SB": 1, "SM": 2}
    return (order.get(m.group(1), 3), int(m.group(2)))


def sorted_classes(classes) -> list:
    return sorted([c for c in classes if pd.notna(c)], key=class_sort_key)


# ============================================================
# Page 1 — Médailles Paralympiques (1992-2024)
# ============================================================
def page_medals():
    st.title("Médailles Paralympiques en Natation (1992-2024)")
    st.caption(
        "Évolution du nombre de médailles par nation aux Jeux Paralympiques"
    )

    medals = load_medals()
    game_years = sorted(medals["Year"].unique())

    # --- Filtres sidebar ---
    st.sidebar.subheader("Filtres")
    metric = st.sidebar.radio(
        "Type de médaille",
        ["Total", "Gold", "Silver", "Bronze"],
        format_func=lambda x: {
            "Total": "Total", "Gold": "Or",
            "Silver": "Argent", "Bronze": "Bronze",
        }[x],
        key="m_metric",
    )

    # Sélection des nations
    all_nations = sorted(medals["Nation"].unique())
    nation_totals = (
        medals.groupby("Nation")["Total"].sum().sort_values(ascending=False)
    )

    preset = st.sidebar.radio(
        "Sélection rapide",
        ["France seule", "France + Top 5", "Top 10", "Personnalisé"],
        index=1,
        key="m_preset",
    )

    if preset == "France seule":
        selected_nations = ["France"]
    elif preset == "France + Top 5":
        top5 = nation_totals.head(5).index.tolist()
        selected_nations = list(dict.fromkeys(["France"] + top5))
    elif preset == "Top 10":
        selected_nations = nation_totals.head(10).index.tolist()
    else:
        selected_nations = st.sidebar.multiselect(
            "Nations",
            all_nations,
            default=["France"],
            key="m_nations_custom",
        )

    if not selected_nations:
        st.warning("Sélectionnez au moins une nation.")
        return

    df = medals[medals["Nation"].isin(selected_nations)]

    # --- KPIs France ---
    france = medals[medals["Nation"] == "France"]
    if not france.empty:
        latest_games = france["Year"].max()
        fr_latest = france[france["Year"] == latest_games].iloc[0]
        fr_total_all = france["Total"].sum()
        fr_rank = nation_totals.index.tolist().index("France") + 1

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            f"France — Paris {int(latest_games)}",
            f"{fr_latest['Total']} méd.",
        )
        c2.metric(
            f"Or / Argent / Bronze ({int(latest_games)})",
            f"{fr_latest['Gold']} / {fr_latest['Silver']} / {fr_latest['Bronze']}",
        )
        c3.metric("Total historique France", fr_total_all)
        c4.metric("Rang mondial (total)", f"#{fr_rank}")

    st.markdown("---")

    # --- Graphique principal : évolution ---
    metric_label = {
        "Total": "Total des médailles",
        "Gold": "Médailles d'or",
        "Silver": "Médailles d'argent",
        "Bronze": "Médailles de bronze",
    }[metric]

    st.subheader(f"Évolution — {metric_label}")

    fig = px.line(
        df,
        x="Year",
        y=metric,
        color="Nation",
        markers=True,
        labels={"Year": "Jeux", metric: metric_label},
    )
    _highlight_france(fig)
    apply_style(fig)
    fig.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=game_years,
            ticktext=[str(int(y)) for y in game_years],
        )
    )
    _int_yaxis(fig)
    st.plotly_chart(fig, use_container_width=True)

    # --- Progression et palmarès ---
    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Progression des nations")

        # Sélection de la période
        col_start, col_end = st.columns(2)
        with col_start:
            start_year = st.selectbox(
                "De", game_years, index=0, key="m_prog_start"
            )
        with col_end:
            valid_end = [y for y in game_years if y > start_year]
            if not valid_end:
                valid_end = [game_years[-1]]
            end_year = st.selectbox(
                "À",
                valid_end,
                index=len(valid_end) - 1,
                key="m_prog_end",
            )

        n_nations_prog = st.slider(
            "Nombre de nations", 5, 30, 30, key="m_n_prog"
        )

        first = medals[medals["Year"] == start_year].set_index("Nation")[metric]
        last = medals[medals["Year"] == end_year].set_index("Nation")[metric]

        delta_full = (last - first).dropna().sort_values(ascending=False)
        # Montrer les extrêmes : meilleurs + pires progressions
        if n_nations_prog >= len(delta_full):
            delta = delta_full
        else:
            half = n_nations_prog // 2
            top = delta_full.head(half)
            bottom = delta_full.tail(n_nations_prog - half)
            delta = pd.concat([top, bottom])
        delta_df = delta.reset_index()
        delta_df.columns = ["Nation", "Progression"]

        fig = px.bar(
            delta_df,
            x="Nation",
            y="Progression",
            color="Progression",
            color_continuous_scale=["#006064", "#00BCD4", "#FFD700"],
        )
        apply_style(fig)
        fig.update_layout(coloraxis_showscale=False)
        _int_yaxis(fig)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader(
            f"Palmarès total ({int(game_years[0])}-{int(game_years[-1])})"
        )
        totals = (
            medals.groupby("Nation")[["Gold", "Silver", "Bronze", "Total"]]
            .sum()
            .sort_values("Total", ascending=False)
            .head(20)
            .reset_index()
        )
        totals.columns = ["Nation", "Or", "Argent", "Bronze", "Total"]
        totals.index += 1
        st.dataframe(totals, use_container_width=True)


# ============================================================
# Page 2 — Nageurs Médaillés (2004-2024)
# ============================================================
def page_medalists():
    st.title("Nageurs Médaillés Paralympiques (2004-2024)")
    st.caption(
        "Analyse des nageurs médaillés par nation, sexe et classification"
    )

    raw = load_medalists()
    game_years = sorted(raw["Année"].dropna().unique())

    # --- Filtres sidebar ---
    st.sidebar.subheader("Filtres")

    # Nations
    all_nations = sorted(raw["Nation"].unique())
    nation_totals = raw.groupby("Nation").size().sort_values(ascending=False)

    nation_preset = st.sidebar.radio(
        "Nations",
        ["France seule", "France + Top 5", "Top 10", "Personnalisé"],
        index=1,
        key="md_preset",
    )
    if nation_preset == "France seule":
        sel_nations = ["France"]
    elif nation_preset == "France + Top 5":
        top5 = nation_totals.head(5).index.tolist()
        sel_nations = list(dict.fromkeys(["France"] + top5))
    elif nation_preset == "Top 10":
        sel_nations = nation_totals.head(10).index.tolist()
    else:
        sel_nations = st.sidebar.multiselect(
            "Choisir les nations",
            all_nations,
            default=["France"],
            key="md_nations_custom",
        )

    # Sexe
    sex_choice = st.sidebar.radio(
        "Sexe", ["Tous", "Hommes (Men)", "Femmes (Women)"], key="md_sex"
    )

    # Médailles — radio
    medal_choice = st.sidebar.radio(
        "Type de médaille",
        ["Toutes", "Or", "Argent", "Bronze"],
        key="md_medal",
    )
    _medal_map = {"Or": "Gold", "Argent": "Silver", "Bronze": "Bronze"}

    # Classification : type (S/SB/SM) puis numéro
    st.sidebar.markdown("**Classification**")
    class_type_filter = st.sidebar.radio(
        "Type", ["Tous", "S", "SB", "SM"], horizontal=True, key="md_ctype"
    )

    # Numéros disponibles selon le type sélectionné
    if class_type_filter != "Tous":
        available_nums = sorted(
            raw[raw["Classe_type"] == class_type_filter]["Classe_num"]
            .dropna()
            .unique()
            .tolist()
        )
    else:
        available_nums = sorted(
            raw["Classe_num"].dropna().unique().tolist()
        )

    num_options = ["Tous"] + [str(int(n)) for n in available_nums]
    class_num_filter = st.sidebar.selectbox(
        "Numéro de classe", num_options, key="md_cnum"
    )

    # --- Appliquer les filtres ---
    df = raw.copy()

    if sel_nations:
        df = df[df["Nation"].isin(sel_nations)]
    if "Men" in sex_choice:
        df = df[df["Sexe"] == "Men"]
    elif "Women" in sex_choice:
        df = df[df["Sexe"] == "Women"]
    if medal_choice != "Toutes":
        df = df[df["Médaille"] == _medal_map[medal_choice]]
    if class_type_filter != "Tous":
        df = df[df["Classe_type"] == class_type_filter]
    if class_num_filter != "Tous":
        df = df[df["Classe_num"] == int(class_num_filter)]

    if df.empty:
        st.warning("Aucune donnée pour ces filtres.")
        return

    # --- KPIs ---
    fr_in_filter = df[df["Nation"] == "France"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Médaillés (sélection)", df["Nom"].nunique())
    c2.metric("Médailles (sélection)", len(df))
    c3.metric("Médaillés France", fr_in_filter["Nom"].nunique())
    c4.metric("Or France", len(fr_in_filter[fr_in_filter["Médaille"] == "Gold"]))

    st.markdown("---")

    # --- Évolution par nation ---
    st.subheader("Nombre de médaillés par édition et par nation")
    by_year_nation = (
        df.groupby(["Année", "Nation"])["Nom"].nunique().reset_index()
    )
    by_year_nation.columns = ["Année", "Nation", "Médaillés"]

    if len(sel_nations) == 1:
        bar_color = (
            FRANCE_COLOR if sel_nations[0] == "France" else "#00BCD4"
        )
        fig = px.bar(
            by_year_nation,
            x="Année",
            y="Médaillés",
            color_discrete_sequence=[bar_color],
            text="Médaillés",
        )
        fig.update_traces(textposition="outside")
    else:
        fig = px.line(
            by_year_nation,
            x="Année",
            y="Médaillés",
            color="Nation",
            markers=True,
        )
        _highlight_france(fig)
    apply_style(fig)
    fig.update_layout(xaxis=_paralympic_tickaxis(game_years))
    _int_yaxis(fig)
    st.plotly_chart(fig, use_container_width=True)

    # --- Comparaisons par nation : sexe et classification ---
    st.markdown("---")

    # Sélection de la période pour les comparaisons
    st.subheader("Comparaisons par nation")
    col_start, col_end = st.columns(2)
    with col_start:
        cmp_start = st.selectbox(
            "De", game_years, index=0, key="md_cmp_start"
        )
    with col_end:
        valid_end = [y for y in game_years if y >= cmp_start]
        if not valid_end:
            valid_end = [game_years[-1]]
        cmp_end = st.selectbox(
            "À",
            valid_end,
            index=len(valid_end) - 1,
            key="md_cmp_end",
        )

    # Filtrer par période
    df_period = df[(df["Année"] >= cmp_start) & (df["Année"] <= cmp_end)]

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**Comparaison H/F par nation**")
        if "Men" not in sex_choice and "Women" not in sex_choice:
            sex_by_nation = (
                df_period.groupby(["Nation", "Sexe"])["Nom"]
                .nunique()
                .reset_index()
            )
            sex_by_nation.columns = ["Nation", "Sexe", "Médaillés"]
            nation_order = (
                sex_by_nation.groupby("Nation")["Médaillés"]
                .sum()
                .sort_values(ascending=False)
                .index.tolist()
            )
            fig = px.bar(
                sex_by_nation,
                x="Nation",
                y="Médaillés",
                color="Sexe",
                barmode="group",
                color_discrete_map={"Men": "#0288D1", "Women": "#F15BB5"},
                category_orders={"Nation": nation_order},
            )
            apply_style(fig)
            _int_yaxis(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Désélectionnez le filtre Sexe pour voir la comparaison H/F."
            )

    with col_r:
        if class_num_filter != "Tous":
            st.markdown(
                f"**Types de classe ({class_num_filter}) par nation**"
            )
        else:
            st.markdown("**Classification par nation**")
        by_nation_type = (
            df_period.groupby(["Nation", "Classe_type"])["Nom"]
            .nunique()
            .reset_index()
        )
        by_nation_type.columns = ["Nation", "Type", "Médaillés"]
        by_nation_type = by_nation_type.dropna(subset=["Type"])
        if not by_nation_type.empty:
            nation_order = (
                by_nation_type.groupby("Nation")["Médaillés"]
                .sum()
                .sort_values(ascending=False)
                .index.tolist()
            )
            fig = px.bar(
                by_nation_type,
                x="Nation",
                y="Médaillés",
                color="Type",
                barmode="group",
                category_orders={"Nation": nation_order},
            )
            apply_style(fig)
            _int_yaxis(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas de données de classification disponibles.")

    # --- Évolution par classe (si type sélectionné et pas de numéro) ---
    if class_type_filter != "Tous" and class_num_filter == "Tous":
        st.markdown("---")
        st.subheader(f"Évolution par classe {class_type_filter}")
        by_class = (
            df.groupby(["Année", "Classe"])["Nom"].nunique().reset_index()
        )
        by_class.columns = ["Année", "Classe", "Médaillés"]
        fig = px.line(
            by_class,
            x="Année",
            y="Médaillés",
            color="Classe",
            markers=True,
        )
        apply_style(fig)
        fig.update_layout(xaxis=_paralympic_tickaxis(game_years))
        _int_yaxis(fig)
        st.plotly_chart(fig, use_container_width=True)

    # --- Détail des médaillés ---
    st.markdown("---")
    st.subheader("Détail des médaillés")
    detail = df_period.sort_values(["Année", "Nation", "Médaille"]).reset_index(
        drop=True
    )
    detail.index += 1
    st.dataframe(
        detail[
            ["Année", "Nom", "Nation", "Épreuve", "Classe", "Médaille", "Sexe"]
        ],
        use_container_width=True,
        height=400,
    )


# ============================================================
# Filtres FFH communs (pages 3 et 4)
# ============================================================
def _ffh_sidebar_filters(raw, key_prefix):
    """Filtres sidebar pour les pages FFH : catégorie d'âge + classification."""
    st.sidebar.subheader("Filtres")

    # Catégorie d'âge — radio
    age_choice = st.sidebar.radio(
        "Catégorie d'âge",
        ["Toutes", "Avenir", "Jeune", "Junior", "Master", "Senior"],
        key=f"{key_prefix}_age",
    )

    # Classification : type (S/SB/SM) puis numéro
    st.sidebar.markdown("**Classification**")
    cls_type = st.sidebar.radio(
        "Type", ["Tous", "S", "SB", "SM"], horizontal=True,
        key=f"{key_prefix}_ctype",
    )

    if cls_type != "Tous":
        available_nums = sorted(
            raw[raw["Classe_type"] == cls_type]["Categorie"]
            .str.extract(r"(\d+)$", expand=False)
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )
    else:
        available_nums = sorted(
            raw["Categorie"]
            .str.extract(r"(\d+)$", expand=False)
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )
    num_options = ["Tous"] + [str(n) for n in available_nums]
    cls_num = st.sidebar.selectbox(
        "Numéro de classe", num_options, key=f"{key_prefix}_cnum"
    )

    # Appliquer les filtres
    df = raw.copy()
    if age_choice != "Toutes":
        df = df[df["Categorie_age"].str.upper() == age_choice.upper()]
    if cls_type != "Tous":
        df = df[df["Classe_type"] == cls_type]
    if cls_num != "Tous":
        df = df[
            df["Categorie"].str.extract(r"(\d+)$", expand=False).astype(float)
            == int(cls_num)
        ]
    # Exclure N.E par défaut
    df = df[df["Categorie"] != "N.E"]

    return df, age_choice, cls_type, cls_num


# ============================================================
# Page 3 — Pratique en France (FFH 2018-2025)
# ============================================================
def page_france_practice():
    st.title("Pratique Compétitive en France (2018-2025)")
    st.caption(
        "Évolution du nombre de compétiteurs, par catégorie d'âge et classification — FFH"
    )

    raw = load_ffh()
    ffh, age_choice, cls_type, cls_num = _ffh_sidebar_filters(raw, "ff")

    if ffh.empty:
        st.warning("Aucune donnée pour ces filtres.")
        return

    # --- KPIs ---
    saisons = sorted(ffh["Saison"].dropna().unique())
    latest = saisons[-1] if saisons else "—"
    prev = saisons[-2] if len(saisons) >= 2 else None

    n_ath = ffh[ffh["Saison"] == latest]["Nom"].nunique()
    n_ath_prev = ffh[ffh["Saison"] == prev]["Nom"].nunique() if prev else n_ath
    n_clubs = ffh[ffh["Saison"] == latest]["Club"].nunique()
    total_ath = ffh["Nom"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        f"Athlètes {latest}",
        n_ath,
        f"{n_ath - n_ath_prev:+d}" if n_ath != n_ath_prev else None,
    )
    c2.metric(f"Clubs {latest}", n_clubs)
    c3.metric("Total athlètes (toutes saisons)", total_ath)
    c4.metric("Saisons", len(saisons))

    st.markdown("---")

    # --- Évolution du nombre d'athlètes ---
    st.subheader("Évolution du nombre d'athlètes distincts")

    ath_by_season = (
        ffh.groupby("Saison")["Nom"].nunique().reset_index()
    )
    ath_by_season.columns = ["Saison", "Athlètes"]

    fig = px.bar(
        ath_by_season,
        x="Saison",
        y="Athlètes",
        color_discrete_sequence=["#00BCD4"],
        text="Athlètes",
    )
    apply_style(fig)
    fig.update_traces(textposition="outside")
    _int_yaxis(fig)
    st.plotly_chart(fig, use_container_width=True)

    # --- Ventilation par catégorie d'âge et classification ---
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Par catégorie d'âge")
        by_age_cat = (
            ffh.groupby(["Saison", "Categorie_age"])["Nom"]
            .nunique()
            .reset_index()
        )
        by_age_cat.columns = ["Saison", "Catégorie", "Athlètes"]
        fig = px.bar(
            by_age_cat,
            x="Saison",
            y="Athlètes",
            color="Catégorie",
            barmode="stack",
        )
        apply_style(fig)
        _int_yaxis(fig)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Par type de classification")
        by_cls = (
            ffh.groupby(["Saison", "Classe_type"])["Nom"]
            .nunique()
            .reset_index()
        )
        by_cls.columns = ["Saison", "Type", "Athlètes"]
        by_cls = by_cls.dropna(subset=["Type"])
        fig = px.bar(
            by_cls,
            x="Saison",
            y="Athlètes",
            color="Type",
            barmode="group",
        )
        apply_style(fig)
        _int_yaxis(fig)
        st.plotly_chart(fig, use_container_width=True)

    # --- Détail par classification ---
    if cls_num == "Tous":
        st.markdown("---")
        title_cls = (
            f"Athlètes par classe {cls_type}"
            if cls_type != "Tous"
            else "Athlètes par classe"
        )
        st.subheader(title_cls)
        by_cls_detail = (
            ffh.groupby(["Saison", "Categorie"])["Nom"]
            .nunique()
            .reset_index()
        )
        by_cls_detail.columns = ["Saison", "Classe", "Athlètes"]
        cls_order = sorted(
            by_cls_detail["Classe"].unique(), key=class_sort_key
        )
        fig = px.line(
            by_cls_detail,
            x="Saison",
            y="Athlètes",
            color="Classe",
            markers=True,
            category_orders={"Classe": cls_order},
        )
        apply_style(fig)
        _int_yaxis(fig)
        st.plotly_chart(fig, use_container_width=True)

    # --- Top clubs ---
    st.markdown("---")
    st.subheader(f"Top 15 clubs — {latest}")
    top_clubs = (
        ffh[ffh["Saison"] == latest]
        .groupby("Club")["Nom"]
        .nunique()
        .nlargest(15)
        .reset_index()
    )
    top_clubs.columns = ["Club", "Athlètes"]
    fig = px.bar(
        top_clubs,
        x="Club",
        y="Athlètes",
        color_discrete_sequence=["#00BCD4"],
    )
    apply_style(fig)
    fig.update_layout(xaxis_tickangle=-45)
    _int_yaxis(fig)
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# Page 4 — Niveau Français (Points)
# ============================================================
def page_france_level():
    st.title("Niveau des Nageurs Français (2018-2025)")
    st.caption(
        "Évolution du niveau basé sur les points FFH — "
        "plus les points sont élevés, meilleure est la performance"
    )

    raw = load_ffh()
    # Ne garder que les résultats avec points significatifs
    raw = raw[raw["Points"] > 10]

    ffh, age_choice, cls_type, cls_num = _ffh_sidebar_filters(raw, "lv")

    if ffh.empty:
        st.warning("Aucune donnée pour ces filtres.")
        return

    # --- KPIs ---
    saisons = sorted(ffh["Saison"].dropna().unique())
    latest = saisons[-1] if saisons else "—"
    prev = saisons[-2] if len(saisons) >= 2 else None

    pts_latest = ffh[ffh["Saison"] == latest]["Points"].mean()
    pts_prev = ffh[ffh["Saison"] == prev]["Points"].mean() if prev else pts_latest
    max_pts = ffh[ffh["Saison"] == latest]["Points"].max()

    c1, c2, c3 = st.columns(3)
    c1.metric(
        f"Points moyens {latest}",
        f"{pts_latest:.0f}",
        f"{pts_latest - pts_prev:+.0f}" if prev else None,
    )
    c2.metric(f"Meilleur score {latest}", f"{max_pts:.0f}")
    c3.metric("Résultats analysés", f"{len(ffh):,}")

    st.markdown("---")

    # --- Évolution des points moyens ---
    st.subheader("Évolution du niveau moyen (points)")

    pts_by_season = (
        ffh.groupby("Saison")["Points"]
        .agg(["mean", "median", "max"])
        .reset_index()
    )
    pts_by_season.columns = ["Saison", "Moyenne", "Médiane", "Maximum"]

    fig = px.line(
        pts_by_season.melt(
            id_vars="Saison",
            value_vars=["Moyenne", "Médiane"],
            var_name="Indicateur",
            value_name="Points",
        ),
        x="Saison",
        y="Points",
        color="Indicateur",
        markers=True,
        color_discrete_map={"Moyenne": "#00BCD4", "Médiane": "#FFD166"},
    )
    apply_style(fig)
    st.plotly_chart(fig, use_container_width=True)

    # --- Par catégorie d'âge et classification ---
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Points moyens par catégorie d'âge")
        pts_age = (
            ffh.groupby(["Saison", "Categorie_age"])["Points"]
            .mean()
            .reset_index()
        )
        pts_age.columns = ["Saison", "Catégorie", "Points moyens"]
        fig = px.line(
            pts_age,
            x="Saison",
            y="Points moyens",
            color="Catégorie",
            markers=True,
        )
        apply_style(fig)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Points moyens par classification")
        pts_cls = (
            ffh.groupby(["Saison", "Categorie"])["Points"]
            .mean()
            .reset_index()
        )
        pts_cls.columns = ["Saison", "Classe", "Points moyens"]
        # Trier les classes dans l'ordre naturel
        cls_order = sorted(
            pts_cls["Classe"].unique(), key=class_sort_key
        )
        fig = px.line(
            pts_cls,
            x="Saison",
            y="Points moyens",
            color="Classe",
            markers=True,
            category_orders={"Classe": cls_order},
        )
        apply_style(fig)
        st.plotly_chart(fig, use_container_width=True)

    # --- Distribution des points ---
    st.markdown("---")
    st.subheader("Distribution des points par saison")

    fig = px.box(
        ffh,
        x="Saison",
        y="Points",
        color_discrete_sequence=["#00BCD4"],
    )
    apply_style(fig)
    st.plotly_chart(fig, use_container_width=True)

    # --- Top athlètes ---
    st.markdown("---")
    st.subheader(f"Top 20 athlètes — {latest} (meilleur score)")
    top_ath = (
        ffh[ffh["Saison"] == latest]
        .sort_values("Points", ascending=False)
        .drop_duplicates(subset=["Nom"])
        .head(20)
    )
    display = top_ath[
        ["Nom", "Categorie", "Categorie_age", "Club", "Epreuve", "Points"]
    ].reset_index(drop=True)
    display.columns = [
        "Nom", "Classe", "Catégorie", "Club", "Épreuve", "Points",
    ]
    display.index += 1
    st.dataframe(display, use_container_width=True)


# ============================================================
# Navigation principale
# ============================================================
st.sidebar.title("Para Natation France")
st.sidebar.caption("Évolution & Perspectives")
st.sidebar.markdown("---")

PAGES = {
    "Médailles Paralympiques": page_medals,
    "Nageurs Médaillés": page_medalists,
    "Pratique en France (FFH)": page_france_practice,
    "Niveau Français (Points)": page_france_level,
}

page = st.sidebar.radio(
    "Navigation", list(PAGES.keys()), label_visibility="collapsed"
)
st.sidebar.markdown("---")
st.sidebar.caption(
    "Données :\n"
    "- Médailles : Wikipedia\n"
    "- Médaillés : IPC SDMS\n"
    "- FFH : Fédération Française Handisport"
)

# Afficher la page
PAGES[page]()

# Footer
st.markdown("---")
st.markdown(
    '<div class="footer">'
    'Développé par <a href="https://yohan-mahistre.pages.dev" target="_blank" '
    'style="color: #80DEEA; text-decoration: none;"><strong>Yohan Mahistre</strong></a> · '
    "Données : IPC SDMS, FFH, Wikipedia"
    "</div>",
    unsafe_allow_html=True,
)
