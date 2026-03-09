"""
Module de chargement des données para natation France.
Sources : Wikipedia (médailles), IPC (médaillés), FFH (résultats nationaux).
"""

import os
import re

import pandas as pd
import streamlit as st


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@st.cache_data(show_spinner="Chargement des médailles paralympiques...")
def load_medals() -> pd.DataFrame:
    """Médailles par nation aux Jeux Paralympiques (1992-2024)."""
    path = os.path.join(DATA_DIR, "paralympic_swimming_medals_1992_2024.xlsx")
    df = pd.read_excel(path)
    # Colonnes attendues : Year, Nation, Gold, Silver, Bronze, Total
    for col in ["Gold", "Silver", "Bronze", "Total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(show_spinner="Chargement des médaillés individuels...")
def load_medalists() -> pd.DataFrame:
    """Médaillés individuels paralympiques (2004-2024)."""
    path = os.path.join(DATA_DIR, "paralympics_swimming_medalists_2004_2024.xlsx")
    df = pd.read_excel(path)
    # Renommer les colonnes (encodage parfois corrompu dans les Excel)
    df.columns = ["Année", "Sexe", "Épreuve", "Classe", "Médaille", "Nom", "Nation"]
    df["Année"] = pd.to_numeric(df["Année"], errors="coerce").astype("Int64")
    # Normaliser le sexe
    df["Sexe"] = df["Sexe"].str.strip()
    # Extraire le type de classe (S, SB, SM) et le numéro
    df["Classe_type"] = df["Classe"].str.extract(r"^(SB|SM|S)")
    df["Classe_num"] = (
        df["Classe"].str.extract(r"(\d+)$", expand=False)
        .astype(float)
        .astype("Int64")
    )
    return df


@st.cache_data(show_spinner="Chargement des résultats FFH...")
def load_ffh() -> pd.DataFrame:
    """Résultats FFH natation handisport France (2018-2025)."""
    path = os.path.join(DATA_DIR, "resultats_ffh_natation_full_2018_2025.xlsx")
    df = pd.read_excel(path)
    # Extraire la saison depuis Source_fichier (ex: "2018-2019" -> Saison)
    df["Saison"] = df["Source_fichier"].str.extract(r"(\d{4}-\d{4})", expand=False)
    df["Year"] = (
        df["Source_fichier"]
        .str.extract(r"\d{4}-(\d{4})", expand=False)
        .astype(float)
        .astype("Int64")
    )
    # Nettoyage des points
    df["Points"] = pd.to_numeric(df["Points"], errors="coerce").fillna(0)
    # Type de classe
    df["Classe_type"] = df["Categorie"].str.extract(r"^(SB|SM|S)")
    # Année de naissance en entier
    df["Annee_naissance"] = pd.to_numeric(
        df["Annee_naissance"], errors="coerce"
    ).astype("Int64")
    return df
