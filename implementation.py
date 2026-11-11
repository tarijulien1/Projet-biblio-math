
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

                    # Contenu de la démonstration.
                    display_math_content(
                        selected_demo.get("content", ""),
                        definitions
                    )

                    # Modification de la démonstration sélectionnée.
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
                                demo_content
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
