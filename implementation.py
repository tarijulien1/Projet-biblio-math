
import html
import streamlit as st

from app.Définitions.gestion_definitions import (
    load_definitions,
    save_definition,
    delete_definition,
    add_definition,
)

from app.Définitions.affichage_definitions import (
    display_math_content
)

from app.Théorèmes.gestion_theoremes import (
    load_theorems,
    save_theorem,
    delete_theorem,
    add_theorem,
    load_demonstrations,
    get_demonstrations_for_theorem,
    add_demonstration,
    save_demonstration,
    delete_demonstration,
)


# ============================================================
# OUTILS
# ============================================================

def parse_comma_separated(value):
    """Transforme une chaîne séparée par des virgules en liste sans doublons."""

    if not isinstance(value, str):
        return []

    return list(dict.fromkeys(
        element.strip()
        for element in value.split(",")
        if element.strip()
    ))


def get_item_themes(item):
    """Récupère les thèmes d'un élément, même si les données sont anciennes."""

    themes = item.get("themes", item.get("theme", []))

    if isinstance(themes, str):
        themes = [themes]

    if not isinstance(themes, list):
        return []

    return [
        theme.strip()
        for theme in themes
        if isinstance(theme, str) and theme.strip()
    ]


def display_themes(themes):
    """Affiche les thèmes uniquement s'il y en a."""

    if themes:
        st.caption("Thèmes : " + " | ".join(themes))


# ============================================================
# PRÉREQUIS DES DÉMONSTRATIONS
# ============================================================

def build_prerequisite_catalog(definitions, theorems):
    """
    Construit le catalogue des définitions et théorèmes
    pouvant être utilisés comme prérequis.

    Les propriétés pourront être ajoutées au catalogue
    lorsqu'elles disposeront de leur propre source de données.
    """

    catalog = {}

    for item in definitions + theorems:

        item_id = item.get("id")

        if not item_id:
            continue

        category = item.get("category", "Définitions")
        category_lower = category.casefold()

        if "théorème" in category_lower or "theoreme" in category_lower:
            item_type = "theorem"

        elif "propriété" in category_lower or "propriete" in category_lower:
            item_type = "property"

        else:
            item_type = "definition"

        key = f"{item_type}:{item_id}"

        catalog[key] = {
            "id": item_id,
            "type": item_type,
            "title": item.get("title", "Sans titre"),
            "content": item.get("content", "")
        }

    return catalog


def resolve_prerequisite(prerequisite, catalog):
    """Retrouve l'élément associé à un prérequis."""

    if not isinstance(prerequisite, dict):
        return None

    ref_id = prerequisite.get("ref_id")

    if not ref_id:
        return None

    for item in catalog.values():

        if item["id"] == ref_id:
            return item

    return None


def display_prerequisites(prerequisites, catalog):
    """
    Affiche les prérequis :

    - bleu avec infobulle si la référence existe ;
    - rouge si la référence est absente.
    """

    if not prerequisites:
        return

    st.markdown("**Prérequis :**")

    resolved = []
    unresolved = []

    for prerequisite in prerequisites:

        if not isinstance(prerequisite, dict):
            continue

        item = resolve_prerequisite(prerequisite, catalog)
        label = prerequisite.get("label", "")

        if not isinstance(label, str) or not label.strip():
            continue

        if item is not None:

            resolved.append({
                "keyword": label,
                "title": item["title"],
                "content": item["content"]
            })

        else:

            unresolved.append(label)

    # Prérequis référencés : infobulles
    if resolved:

        labels = "\n\n".join(
            f"- {item['keyword']}"
            for item in resolved
        )

        tooltip_data = [
            {
                "keywords": [item["keyword"]],
                "title": item["title"],
                "content": item["content"]
            }
            for item in resolved
        ]

        display_math_content(
            labels,
            tooltip_data
        )

    # Prérequis non référencés : rouge
    if unresolved:

        for label in unresolved:

            safe_label = html.escape(label)

            st.markdown(
                f'<span style="color:#d62728;">'
                f'• {safe_label}'
                f'</span>',
                unsafe_allow_html=True
            )


def prerequisite_editor(
    current_prerequisites,
    catalog,
    key_prefix
):
    """
    Interface de sélection des prérequis.

    Les éléments existants sont sélectionnables.
    Les éléments absents peuvent être saisis librement.
    """

    st.markdown("**Prérequis de la démonstration**")

    options = list(catalog.keys())

    def format_option(key):

        item = catalog[key]

        type_labels = {
            "definition": "Définition",
            "theorem": "Théorème",
            "property": "Propriété"
        }

        return (
            f"{item['title']} "
            f"({type_labels.get(item['type'], item['type'])})"
        )

    selected_keys = []
    missing_labels = []

    for prerequisite in current_prerequisites or []:

        if not isinstance(prerequisite, dict):
            continue

        item = resolve_prerequisite(prerequisite, catalog)

        if item is not None:

            matching_key = next(
                (
                    key
                    for key, value in catalog.items()
                    if value["id"] == item["id"]
                ),
                None
            )

            if matching_key and matching_key not in selected_keys:
                selected_keys.append(matching_key)

        else:

            label = prerequisite.get("label", "")

            if label:
                missing_labels.append(label)

    selected = st.multiselect(
        "Sélectionner les définitions, théorèmes ou propriétés existants",
        options=options,
        default=selected_keys,
        format_func=format_option,
        key=f"{key_prefix}_references"
    )

    missing_text = st.text_area(
        "Autres prérequis non référencés (un par ligne)",
        value="\n".join(missing_labels),
        key=f"{key_prefix}_missing"
    )

    prerequisites = []

    # Prérequis référencés
    for key in selected:

        item = catalog[key]

        prerequisites.append({
            "label": item["title"],
            "type": item["type"],
            "ref_id": item["id"]
        })

    # Prérequis non référencés
    for label in missing_text.splitlines():

        label = label.strip()

        if label:

            prerequisites.append({
                "label": label,
                "type": None,
                "ref_id": None
            })

    return prerequisites


# ============================================================
# FILTRAGE PAR THÈMES
# ============================================================

def select_theme_filters(items, category):

    st.subheader("Filtrer par thèmes")

    available_themes = {
        theme
        for item in items
        for theme in get_item_themes(item)
    }

    available_themes.add("Groupes")

    available_themes = sorted(
        available_themes,
        key=str.casefold
    )

    mode = st.radio(
        "Mode de sélection",
        ["Union", "Intersection"],
        horizontal=True,
        key=f"theme_mode_{category}"
    )

    st.caption("Sélectionner les thèmes souhaités")

    selected_themes = []

    columns = st.columns(3)

    for i, theme in enumerate(available_themes):

        with columns[i % 3]:

            checked = st.checkbox(
                theme,
                value=(theme == "Groupes"),
                key=f"theme_filter_{category}_{theme}"
            )

            if checked:
                selected_themes.append(theme)

    if not selected_themes:

        st.warning("Sélectionne au moins un thème.")

        return []

    selected = set(selected_themes)

    filtered_items = []

    for item in items:

        item_themes = set(get_item_themes(item))

        if mode == "Union":
            match = bool(item_themes & selected)

        else:
            match = selected.issubset(item_themes)

        if match:
            filtered_items.append(item)

    st.caption(
        f"{len(filtered_items)} élément(s) correspondant(s)"
    )

    return filtered_items


# ============================================================
# APPLICATION PRINCIPALE
# ============================================================

def run_app():

    st.set_page_config(
        page_title="Ma bibliothèque mathématique",
        page_icon="📚",
        layout="wide"
    )

    st.title("📚 Ma bibliothèque mathématique")

    st.caption("Ma bibliothèque personnelle de mathématiques")

    # Chargement des données
    definitions = load_definitions()
    theorems = load_theorems()

    # Navigation
    st.sidebar.header("Navigation")

    category = st.sidebar.selectbox(
        "Catégorie",
        [
            "Définitions",
            "Théorèmes"
        ]
    )

    if category == "Définitions":

        run_definitions(definitions)

    elif category == "Théorèmes":

        run_theorems(theorems, definitions)


# ============================================================
# DÉFINITIONS
# ============================================================

def run_definitions(definitions):

    st.header("Définitions")

    tab1, tab2 = st.tabs([
        "Consulter / Modifier",
        "Ajouter"
    ])

    # --------------------------------------------------------
    # CONSULTATION / MODIFICATION
    # --------------------------------------------------------

    with tab1:

        filtered_definitions = select_theme_filters(
            definitions,
            "definitions"
        )

        if not filtered_definitions:

            st.info(
                "Aucune définition ne correspond aux thèmes sélectionnés."
            )

        else:

            selected_id = st.selectbox(
                "Sélectionner une définition",
                options=[
                    item["id"]
                    for item in filtered_definitions
                ],
                format_func=lambda x: next(
                    item["title"]
                    for item in filtered_definitions
                    if item["id"] == x
                ),
                key="select_definition"
            )

            item = next(
                item
                for item in filtered_definitions
                if item["id"] == selected_id
            )

            st.subheader(item["title"])

            display_themes(get_item_themes(item))

            # On transmet toutes les définitions pour conserver
            # les références croisées entre thèmes.
            display_math_content(
                item.get("content", ""),
                definitions
            )

            st.divider()

            # Modification
            with st.form(f"edit_definition_{item['id']}"):

                title = st.text_input(
                    "Titre",
                    value=item.get("title", "")
                )

                themes = st.text_input(
                    "Thèmes associés (séparés par des virgules)",
                    value=", ".join(get_item_themes(item))
                )

                keywords = st.text_input(
                    "Mots-clés séparés par des virgules",
                    value=", ".join(item.get("keywords", []))
                )

                content = st.text_area(
                    "Contenu LaTeX / Markdown",
                    value=item.get("content", ""),
                    height=350
                )

                submitted = st.form_submit_button("Enregistrer")

                if submitted:

                    selected_themes = parse_comma_separated(themes)

                    if not title.strip():

                        st.error("Le titre est obligatoire.")

                    elif not selected_themes:

                        st.error(
                            "Une définition doit avoir au moins un thème."
                        )

                    else:

                        updated_item = item.copy()

                        updated_item["title"] = title.strip()
                        updated_item["themes"] = selected_themes

                        updated_item["keywords"] = parse_comma_separated(
                            keywords
                        )

                        updated_item["content"] = content

                        save_definition(updated_item)

                        st.success("Définition enregistrée.")

                        st.rerun()

            # Suppression
            if st.button(
                "Supprimer cette définition",
                key=f"delete_def_{item['id']}"
            ):

                delete_definition(item["id"])

                st.rerun()

    # --------------------------------------------------------
    # AJOUT
    # --------------------------------------------------------

    with tab2:

        with st.form("add_definition"):

            title = st.text_input("Titre")

            themes = st.text_input(
                "Thèmes associés (séparés par des virgules)",
                value="Groupes"
            )

            keywords = st.text_input(
                "Mots-clés séparés par des virgules"
            )

            content = st.text_area(
                "Contenu LaTeX / Markdown",
                height=350
            )

            submitted = st.form_submit_button("Ajouter la définition")

            if submitted:

                selected_themes = parse_comma_separated(themes)

                if not title.strip():

                    st.error("Le titre est obligatoire.")

                elif not selected_themes:

                    st.error("Il faut associer au moins un thème.")

                else:

                    add_definition(
                        title,
                        selected_themes,
                        keywords,
                        content
                    )

                    st.success("Définition ajoutée.")

                    st.rerun()


# ============================================================
# THÉORÈMES
# ============================================================

def run_theorems(theorems, definitions):

    st.header("Théorèmes")

    # Catalogue utilisé pour les prérequis des démonstrations.
    prerequisite_catalog = build_prerequisite_catalog(
        definitions,
        theorems
    )

    tab1, tab2 = st.tabs([
        "Consulter / Modifier",
        "Ajouter"
    ])

    # --------------------------------------------------------
    # CONSULTATION / MODIFICATION
    # --------------------------------------------------------

    with tab1:

        filtered_theorems = select_theme_filters(
            theorems,
            "theorems"
        )

        if not filtered_theorems:

            st.info(
                "Aucun théorème ne correspond aux thèmes sélectionnés."
            )

        else:

            selected_id = st.selectbox(
                "Sélectionner un théorème",
                options=[
                    item["id"]
                    for item in filtered_theorems
                ],
                format_func=lambda x: next(
                    item["title"]
                    for item in filtered_theorems
                    if item["id"] == x
                ),
                key="select_theorem"
            )

            theorem = next(
                item
                for item in filtered_theorems
                if item["id"] == selected_id
            )

            # =================================================
            # AFFICHAGE DU THÉORÈME
            # =================================================

            st.subheader(theorem["title"])

            display_themes(get_item_themes(theorem))

            display_math_content(
                theorem.get("content", ""),
                definitions
            )

            st.divider()

            # =================================================
            # SÉLECTION ET AFFICHAGE D'UNE DÉMONSTRATION
            # =================================================

            st.subheader("Démonstration")

            demonstrations = get_demonstrations_for_theorem(
                theorem["id"]
            )

            if demonstrations:

                demonstration_ids = [
                    demo["id"]
                    for demo in demonstrations
                ]

                selected_demo_id = st.selectbox(
                    "Sélectionner une démonstration",
                    options=[None] + demonstration_ids,
                    index=0,
                    format_func=lambda demo_id: (
                        "Aucune démonstration sélectionnée"
                        if demo_id is None
                        else next(
                            demo["title"]
                            for demo in demonstrations
                            if demo["id"] == demo_id
                        )
                    ),
                    key=f"select_demonstration_{theorem['id']}"
                )

                # Aucune démonstration n'est affichée par défaut.
                if selected_demo_id is not None:

                    selected_demo = next(
                        demo
                        for demo in demonstrations
                        if demo["id"] == selected_demo_id
                    )

                    # Les thèmes sont affichés au-dessus du contenu.
                    display_themes(
                        get_item_themes(selected_demo)
                    )

                    # Prérequis affichés sous les thèmes.
                    display_prerequisites(
                        selected_demo.get("prerequisites", []),
                        prerequisite_catalog
                    )

                    # Contenu de la démonstration.
                    display_math_content(
                        selected_demo.get("content", ""),
                        definitions
                    )

                    # ------------------------------------------------
                    # MODIFICATION DE LA DÉMONSTRATION
                    # ------------------------------------------------

                    with st.expander(
                        "Modifier cette démonstration",
                        expanded=False
                    ):

                        with st.form(
                            f"edit_demonstration_{selected_demo['id']}"
                        ):

                            demo_title = st.text_input(
                                "Titre de la démonstration",
                                value=selected_demo.get("title", "")
                            )

                            demo_themes = st.text_input(
                                "Thèmes associés (séparés par des virgules)",
                                value=", ".join(
                                    get_item_themes(selected_demo)
                                )
                            )

                            demo_prerequisites = prerequisite_editor(
                                selected_demo.get("prerequisites", []),
                                prerequisite_catalog,
                                f"edit_{selected_demo['id']}"
                            )

                            demo_content = st.text_area(
                                "Contenu de la démonstration",
                                value=selected_demo.get("content", ""),
                                height=350
                            )

                            submitted = st.form_submit_button(
                                "Enregistrer la démonstration"
                            )

                            if submitted:

                                selected_demo_themes = parse_comma_separated(
                                    demo_themes
                                )

                                if not demo_title.strip():

                                    st.error(
                                        "Le titre de la démonstration est obligatoire."
                                    )

                                elif not selected_demo_themes:

                                    st.error(
                                        "Une démonstration doit avoir au moins un thème."
                                    )

                                else:

                                    updated_demo = selected_demo.copy()

                                    updated_demo["title"] = demo_title.strip()

                                    updated_demo["themes"] = selected_demo_themes

                                    updated_demo["content"] = demo_content

                                    updated_demo["prerequisites"] = (
                                        demo_prerequisites
                                    )

                                    save_demonstration(updated_demo)

                                    st.success(
                                        "Démonstration enregistrée."
                                    )

                                    st.rerun()

                        if st.button(
                            "Supprimer cette démonstration",
                            key=f"delete_demo_{selected_demo['id']}"
                        ):

                            delete_demonstration(
                                selected_demo["id"]
                            )

                            st.rerun()

            else:

                st.info(
                    "Aucune démonstration n'est encore associée à ce théorème."
                )

            # =================================================
            # AJOUT D'UNE DÉMONSTRATION
            # =================================================

            with st.expander(
                "Ajouter une démonstration",
                expanded=False
            ):

                with st.form(
                    f"add_demonstration_{theorem['id']}"
                ):

                    demo_title = st.text_input(
                        "Titre de la démonstration",
                        key=f"new_demo_title_{theorem['id']}"
                    )

                    demo_themes = st.text_input(
                        "Thèmes associés (séparés par des virgules)",
                        value="Groupes",
                        key=f"new_demo_themes_{theorem['id']}"
                    )

                    demo_prerequisites = prerequisite_editor(
                        [],
                        prerequisite_catalog,
                        f"add_{theorem['id']}"
                    )

                    demo_content = st.text_area(
                        "Contenu de la démonstration",
                        height=350,
                        key=f"new_demo_content_{theorem['id']}"
                    )

                    submitted = st.form_submit_button(
                        "Ajouter la démonstration"
                    )

                    if submitted:

                        selected_demo_themes = parse_comma_separated(
                            demo_themes
                        )

                        if not demo_title.strip():

                            st.error(
                                "Le titre de la démonstration est obligatoire."
                            )

                        elif not selected_demo_themes:

                            st.error(
                                "Il faut associer au moins un thème à la démonstration."
                            )

                        else:

                            add_demonstration(
                                theorem["id"],
                                demo_title,
                                selected_demo_themes,
                                demo_content,
                                demo_prerequisites
                            )

                            st.success(
                                "Démonstration ajoutée au théorème."
                            )

                            st.rerun()

            st.divider()

            # =================================================
            # MODIFICATION DU THÉORÈME
            # =================================================

            with st.expander(
                "Modifier le théorème",
                expanded=False
            ):

                with st.form(f"edit_theorem_{theorem['id']}"):

                    title = st.text_input(
                        "Titre",
                        value=theorem.get("title", "")
                    )

                    themes = st.text_input(
                        "Thèmes associés (séparés par des virgules)",
                        value=", ".join(get_item_themes(theorem))
                    )

                    content = st.text_area(
                        "Énoncé du théorème",
                        value=theorem.get("content", ""),
                        height=350
                    )

                    submitted = st.form_submit_button(
                        "Enregistrer le théorème"
                    )

                    if submitted:

                        selected_themes = parse_comma_separated(themes)

                        if not title.strip():

                            st.error("Le titre est obligatoire.")

                        elif not selected_themes:

                            st.error(
                                "Un théorème doit avoir au moins un thème."
                            )

                        else:

                            updated_theorem = theorem.copy()

                            updated_theorem["title"] = title.strip()

                            updated_theorem["themes"] = selected_themes

                            updated_theorem["content"] = content

                            save_theorem(updated_theorem)

                            st.success("Théorème enregistré.")

                            st.rerun()

            # =================================================
            # SUPPRESSION DU THÉORÈME
            # =================================================

            if st.button(
                "Supprimer ce théorème et ses démonstrations",
                key=f"delete_theorem_{theorem['id']}"
            ):

                delete_theorem(theorem["id"])

                st.rerun()

    # --------------------------------------------------------
    # AJOUT D'UN THÉORÈME
    # --------------------------------------------------------

    with tab2:

        with st.form("add_theorem"):

            title = st.text_input("Titre")

            themes = st.text_input(
                "Thèmes associés (séparés par des virgules)",
                value="Groupes"
            )

            content = st.text_area(
                "Énoncé du théorème",
                height=350
            )

            submitted = st.form_submit_button("Ajouter le théorème")

            if submitted:

                selected_themes = parse_comma_separated(themes)

                if not title.strip():

                    st.error("Le titre est obligatoire.")

                elif not selected_themes:

                    st.error("Il faut associer au moins un thème.")

                else:

                    add_theorem(
                        title,
                        selected_themes,
                        content
                    )

                    st.success(
                        "Théorème ajouté. Tu peux maintenant lui associer des démonstrations."
                    )

                    st.rerun()
