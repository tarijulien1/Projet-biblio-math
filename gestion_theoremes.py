
import json
import uuid
from pathlib import Path


# ============================================================
# CHEMINS DES FICHIERS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "Théorèmes"

THEOREMS_FILE = DATA_DIR / "theorems.json"
DEMONSTRATIONS_FILE = DATA_DIR / "demonstrations.json"


# ============================================================
# OUTILS GÉNÉRAUX
# ============================================================

def ensure_data_files():
    """Crée le dossier et les fichiers JSON s'ils n'existent pas."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not THEOREMS_FILE.exists():
        save_all_theorems([])

    if not DEMONSTRATIONS_FILE.exists():
        save_all_demonstrations([])


def normalize_themes(themes):
    """
    Transforme les thèmes en une liste propre :
    - accepte une chaîne séparée par des virgules ;
    - supprime les espaces inutiles ;
    - supprime les doublons.
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


def normalize_keywords(keywords):
    """Normalise une liste de mots-clés."""

    if isinstance(keywords, str):
        keywords = keywords.split(",")

    if keywords is None:
        keywords = []

    normalized = []

    for keyword in keywords:
        if not isinstance(keyword, str):
            continue

        keyword = keyword.strip()

        if keyword and keyword not in normalized:
            normalized.append(keyword)

    return normalized


def load_json_file(file_path):
    """Charge un fichier JSON contenant une liste."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not file_path.exists():
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Le fichier {file_path} contient un JSON invalide."
        ) from error

    if not isinstance(data, list):
        raise ValueError(
            f"Le fichier {file_path} doit contenir une liste."
        )

    return data


def save_json_file(file_path, data):
    """Enregistre une liste dans un fichier JSON."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


# ============================================================
# CHARGEMENT ET SAUVEGARDE DES THÉORÈMES
# ============================================================

def load_theorems():
    """Charge tous les théorèmes."""

    return load_json_file(THEOREMS_FILE)


def save_all_theorems(theorems):
    """Enregistre tous les théorèmes."""

    save_json_file(THEOREMS_FILE, theorems)


def save_theorem(item):
    """
    Ajoute ou met à jour un théorème.

    Structure d'un théorème :
    {
        "id": "...",
        "title": "...",
        "themes": ["Groupes", "Algèbre"],
        "category": "Théorèmes",
        "content": "...",
        "demonstration_ids": ["...", "..."]
    }
    """

    if not isinstance(item, dict):
        raise TypeError("Un théorème doit être un dictionnaire.")

    if not item.get("id"):
        item["id"] = str(uuid.uuid4())

    item["themes"] = normalize_themes(
        item.get("themes", [])
    )

    item["demonstration_ids"] = list(dict.fromkeys(
        item.get("demonstration_ids", [])
    ))

    item["category"] = "Théorèmes"

    theorems = load_theorems()

    theorems = [
        theorem
        for theorem in theorems
        if theorem.get("id") != item["id"]
    ]

    theorems.append(item)

    save_all_theorems(theorems)


def add_theorem(title, themes, content):
    """Crée un nouveau théorème."""

    if not isinstance(title, str) or not title.strip():
        raise ValueError("Le titre du théorème ne peut pas être vide.")

    selected_themes = normalize_themes(themes)

    if not selected_themes:
        raise ValueError(
            "Un théorème doit être associé à au moins un thème."
        )

    item = {
        "id": str(uuid.uuid4()),
        "title": title.strip(),
        "themes": selected_themes,
        "category": "Théorèmes",
        "content": content.strip() if isinstance(content, str) else "",
        "demonstration_ids": []
    }

    save_theorem(item)

    return item


def delete_theorem(item_id):
    """
    Supprime un théorème et toutes ses démonstrations associées.
    """

    theorems = load_theorems()

    theorem = next(
        (item for item in theorems if item.get("id") == item_id),
        None
    )

    if theorem is None:
        return

    demonstration_ids = set(
        theorem.get("demonstration_ids", [])
    )

    updated_theorems = [
        item
        for item in theorems
        if item.get("id") != item_id
    ]

    save_all_theorems(updated_theorems)

    demonstrations = load_demonstrations()

    updated_demonstrations = [
        demo
        for demo in demonstrations
        if demo.get("id") not in demonstration_ids
    ]

    save_all_demonstrations(updated_demonstrations)


def get_theorem_by_id(item_id):
    """Récupère un théorème à partir de son identifiant."""

    for theorem in load_theorems():
        if theorem.get("id") == item_id:
            return theorem

    return None


def get_available_theorem_themes(theorems=None):
    """Retourne tous les thèmes utilisés par les théorèmes."""

    if theorems is None:
        theorems = load_theorems()

    themes = set()

    for theorem in theorems:
        themes.update(
            normalize_themes(theorem.get("themes", []))
        )

    themes.add("Groupes")

    return sorted(themes, key=str.casefold)


# ============================================================
# CHARGEMENT ET SAUVEGARDE DES DÉMONSTRATIONS
# ============================================================

def load_demonstrations():
    """Charge toutes les démonstrations."""

    return load_json_file(DEMONSTRATIONS_FILE)


def save_all_demonstrations(demonstrations):
    """Enregistre toutes les démonstrations."""

    save_json_file(DEMONSTRATIONS_FILE, demonstrations)


def save_demonstration(item):
    """
    Ajoute ou met à jour une démonstration.

    Structure d'une démonstration :
    {
        "id": "...",
        "theorem_id": "...",
        "title": "...",
        "themes": ["Groupes", "Algèbre"],
        "category": "Démonstrations",
        "content": "..."
    }
    """

    if not isinstance(item, dict):
        raise TypeError("Une démonstration doit être un dictionnaire.")

    if not item.get("id"):
        item["id"] = str(uuid.uuid4())

    theorem_id = item.get("theorem_id")

    if not theorem_id:
        raise ValueError(
            "Une démonstration doit être associée à un théorème."
        )

    if get_theorem_by_id(theorem_id) is None:
        raise ValueError(
            "Le théorème associé à cette démonstration n'existe pas."
        )

    item["themes"] = normalize_themes(
        item.get("themes", [])
    )

    item["category"] = "Démonstrations"

    demonstrations = load_demonstrations()

    demonstrations = [
        demo
        for demo in demonstrations
        if demo.get("id") != item["id"]
    ]

    demonstrations.append(item)

    save_all_demonstrations(demonstrations)

    # Assure également le lien depuis le théorème.
    theorem = get_theorem_by_id(theorem_id)

    demonstration_ids = theorem.get("demonstration_ids", [])

    if item["id"] not in demonstration_ids:
        theorem["demonstration_ids"] = demonstration_ids + [
            item["id"]
        ]

        save_theorem(theorem)


def add_demonstration(theorem_id, title, themes, content):
    """Crée une démonstration et l'associe à un théorème."""

    if not isinstance(title, str) or not title.strip():
        raise ValueError(
            "Le titre de la démonstration ne peut pas être vide."
        )

    if get_theorem_by_id(theorem_id) is None:
        raise ValueError(
            "Le théorème associé n'existe pas."
        )

    selected_themes = normalize_themes(themes)

    if not selected_themes:
        raise ValueError(
            "Une démonstration doit être associée à au moins un thème."
        )

    item = {
        "id": str(uuid.uuid4()),
        "theorem_id": theorem_id,
        "title": title.strip(),
        "themes": selected_themes,
        "category": "Démonstrations",
        "content": content.strip() if isinstance(content, str) else ""
    }

    save_demonstration(item)

    return item


def get_demonstration_by_id(item_id):
    """Récupère une démonstration à partir de son identifiant."""

    for demo in load_demonstrations():
        if demo.get("id") == item_id:
            return demo

    return None


def get_demonstrations_for_theorem(theorem_id):
    """
    Retourne les démonstrations associées à un théorème,
    dans l'ordre de leur identifiant dans le théorème.
    """

    theorem = get_theorem_by_id(theorem_id)

    if theorem is None:
        return []

    demonstrations = load_demonstrations()

    demonstrations_by_id = {
        demo.get("id"): demo
        for demo in demonstrations
    }

    result = []

    for demonstration_id in theorem.get("demonstration_ids", []):
        demo = demonstrations_by_id.get(demonstration_id)

        if demo is not None:
            result.append(demo)

    return result


def delete_demonstration(item_id):
    """Supprime une démonstration et son lien avec le théorème."""

    demonstrations = load_demonstrations()

    demonstration = next(
        (demo for demo in demonstrations if demo.get("id") == item_id),
        None
    )

    if demonstration is None:
        return

    updated_demonstrations = [
        demo
        for demo in demonstrations
        if demo.get("id") != item_id
    ]

    save_all_demonstrations(updated_demonstrations)

    theorem = get_theorem_by_id(
        demonstration.get("theorem_id")
    )

    if theorem is not None:
        theorem["demonstration_ids"] = [
            demo_id
            for demo_id in theorem.get("demonstration_ids", [])
            if demo_id != item_id
        ]

        save_theorem(theorem)


def get_available_demonstration_themes(demonstrations=None):
    """Retourne tous les thèmes utilisés par les démonstrations."""

    if demonstrations is None:
        demonstrations = load_demonstrations()

    themes = set()

    for demo in demonstrations:
        themes.update(
            normalize_themes(demo.get("themes", []))
        )

    themes.add("Groupes")

    return sorted(themes, key=str.casefold)


# ============================================================
# INITIALISATION
# ============================================================

ensure_data_files()
