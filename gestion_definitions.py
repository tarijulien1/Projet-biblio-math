
import json
import uuid

from pathlib import Path


# ==================================================
# 1. CONFIGURATION DES CHEMINS
# ==================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data" / "Définitions"

DATA_FILE = DATA_DIR / "definitions.json"


# ==================================================
# 2. CHARGEMENT DES DÉFINITIONS
# ==================================================

def load_definitions():
    """
    Charge toutes les définitions depuis definitions.json.

    Retourne une liste vide si le fichier n'existe pas
    encore.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            definitions = json.load(f)

    except json.JSONDecodeError:
        raise ValueError(
            f"Le fichier {DATA_FILE} contient un JSON invalide."
        )

    if not isinstance(definitions, list):
        raise ValueError(
            "Le fichier definitions.json doit contenir une liste."
        )

    return definitions


# ==================================================
# 3. SAUVEGARDE DE TOUTES LES DÉFINITIONS
# ==================================================

def save_all_definitions(definitions):
    """
    Sauvegarde la liste complète des définitions.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(DATA_FILE, "w", encoding="utf-8") as f:

        json.dump(
            definitions,
            f,
            ensure_ascii=False,
            indent=4
        )


# ==================================================
# 4. NORMALISATION DES THÈMES
# ==================================================

def normalize_themes(themes):
    """
    Nettoie une liste de thèmes :
    - supprime les espaces inutiles ;
    - ignore les thèmes vides ;
    - supprime les doublons ;
    - conserve l'ordre initial.
    """

    if isinstance(themes, str):
        themes = themes.split(",")

    if themes is None:
        themes = []

    normalized = []

    for theme in themes:

        if not isinstance(theme, str):
            continue

        theme = theme.strip()

        if theme and theme not in normalized:
            normalized.append(theme)

    return normalized


# ==================================================
# 5. SAUVEGARDE D'UNE DÉFINITION
# ==================================================

def save_definition(item):
    """
    Ajoute ou modifie une définition.

    Si l'identifiant existe déjà, l'ancienne définition
    est remplacée.
    """

    if not isinstance(item, dict):
        raise TypeError(
            "Une définition doit être un dictionnaire."
        )

    if not item.get("id"):
        item["id"] = str(uuid.uuid4())

    item["themes"] = normalize_themes(
        item.get("themes", [])
    )

    definitions = load_definitions()

    # Supprime l'ancienne version si elle existe.
    definitions = [
        definition
        for definition in definitions
        if definition.get("id") != item["id"]
    ]

    definitions.append(item)

    save_all_definitions(definitions)


# ==================================================
# 6. AJOUT D'UNE DÉFINITION
# ==================================================

def add_definition(title, themes, keywords, content):
    """
    Crée une nouvelle définition.

    Paramètres :
    - title : titre de la définition ;
    - themes : liste des thèmes associés ;
    - keywords : mots-clés séparés par des virgules ;
    - content : contenu Markdown / LaTeX.
    """

    if not title or not title.strip():
        raise ValueError(
            "Le titre de la définition ne peut pas être vide."
        )

    selected_themes = normalize_themes(themes)

    if not selected_themes:
        raise ValueError(
            "Une définition doit être associée à au moins un thème."
        )

    if isinstance(keywords, str):

        keywords_list = [
            keyword.strip()
            for keyword in keywords.split(",")
            if keyword.strip()
        ]

    else:

        keywords_list = [
            keyword.strip()
            for keyword in (keywords or [])
            if isinstance(keyword, str) and keyword.strip()
        ]

    item = {

        "id": str(uuid.uuid4()),

        "title": title.strip(),

        "themes": selected_themes,

        "category": "Définitions",

        "keywords": keywords_list,

        "content": content.strip() if isinstance(content, str) else ""

    }

    save_definition(item)

    return item


# ==================================================
# 7. SUPPRESSION D'UNE DÉFINITION
# ==================================================

def delete_definition(item_id):
    """
    Supprime une définition à partir de son identifiant.
    """

    definitions = load_definitions()

    updated_definitions = [
        item
        for item in definitions
        if item.get("id") != item_id
    ]

    save_all_definitions(updated_definitions)


# ==================================================
# 8. RÉCUPÉRATION DES THÈMES DISPONIBLES
# ==================================================

def get_available_themes(definitions=None):
    """
    Retourne tous les thèmes présents dans les définitions.

    Le thème 'Groupes' est toujours disponible afin de
    pouvoir être sélectionné par défaut dans l'application.
    """

    if definitions is None:
        definitions = load_definitions()

    themes = set()

    for item in definitions:

        item_themes = item.get("themes", [])

        if isinstance(item_themes, str):
            item_themes = [item_themes]

        for theme in item_themes:

            if isinstance(theme, str) and theme.strip():
                themes.add(theme.strip())

    themes.add("Groupes")

    return sorted(themes, key=str.casefold)


# ==================================================
# 9. RECHERCHE D'UNE DÉFINITION PAR IDENTIFIANT
# ==================================================

def get_definition_by_id(item_id):
    """
    Retourne une définition à partir de son identifiant.
    Retourne None si elle n'existe pas.
    """

    definitions = load_definitions()

    for item in definitions:

        if item.get("id") == item_id:
            return item

    return None
