
import streamlit.components.v1 as components

import re
import html
import markdown
import json

from app.latex_config import LATEX_MACROS


# ==================================================
# 1. CONFIGURATION MATHJAX
# ==================================================

macros_json = json.dumps(
    LATEX_MACROS,
    ensure_ascii=False
)


# ==================================================
# 2. RÉCUPÉRATION DES DÉFINITIONS
# ==================================================

def get_definitions(all_data):
    """
    Récupère les mots-clés de toutes les définitions.
    Chaque mot-clé est associé à son titre et son contenu.
    """

    definitions = []

    for item in all_data:

        for keyword in item.get("keywords", []):

            if not isinstance(keyword, str):
                continue

            keyword = keyword.strip()

            if keyword:
                definitions.append({
                    "keyword": keyword,
                    "title": item.get("title", ""),
                    "content": item.get("content", "")
                })

    definitions.sort(
        key=lambda x: len(x["keyword"]),
        reverse=True
    )

    return definitions


# ==================================================
# 3. RECONNAISSANCE DES TERMES
# ==================================================

def render_with_tooltips(content, all_data):
    """
    Recherche les mots-clés dans le texte et les expressions
    LaTeX.

    Les mots du texte sont remplacés par des placeholders.
    Les mots-clés LaTeX sont entourés de \\class pour
    permettre leur identification après le rendu MathJax.
    """

    definitions = get_definitions(all_data)

    if not definitions:
        return content, []

    placeholders = []

    def create_tooltip(definition, matched_text):

        index = len(placeholders)

        placeholders.append({
            "placeholder": f"ZXQTOOLTIP{index}QXZ",
            "matched_text": matched_text,
            "title": definition["title"],
            "content": definition["content"]
        })

        return index

    # ------------------------------------------
    # Séparation des mots-clés
    # ------------------------------------------

    text_definitions = []
    latex_definitions = []

    for definition in definitions:

        keyword = definition["keyword"]

        if "\\" in keyword:

            base = keyword.strip()

            if base.startswith("$$") and base.endswith("$$"):
                base = base[2:-2].strip()

            elif base.startswith("$") and base.endswith("$"):
                base = base[1:-1].strip()

            elif base.startswith(r"\(") and base.endswith(r"\)"):
                base = base[2:-2].strip()

            elif base.startswith(r"\[") and base.endswith(r"\]"):
                base = base[2:-2].strip()

            if base:
                latex_definitions.append({
                    **definition,
                    "base": base
                })

        else:
            text_definitions.append(definition)

    # ------------------------------------------
    # Expressions régulières
    # ------------------------------------------

    def build_regex(definitions_list, latex_mode=False):

        patterns = []

        for index, definition in enumerate(definitions_list):

            if latex_mode:

                base = definition["base"]

                pattern = (
                    r"(?<![A-Za-z])"
                    + re.escape(base)
                    + r"(?![A-Za-z])"
                )

            else:

                keyword = definition["keyword"]

                pattern = (
                    r"(?<!\w)"
                    + re.escape(keyword)
                    + r"(?!\w)"
                )

            patterns.append(
                f"(?P<term{index}>{pattern})"
            )

        if not patterns:
            return None

        return re.compile(
            "|".join(patterns),
            flags=0 if latex_mode else re.IGNORECASE
        )

    text_regex = build_regex(text_definitions)

    latex_regex = build_regex(
        latex_definitions,
        latex_mode=True
    )

    # ------------------------------------------
    # Remplacement du texte ordinaire
    # ------------------------------------------

    def replace_text(text):

        # On commence par les mots-clés textuels.

        if text_regex is not None:

            def replace_text_match(match):

                index = int(
                    match.lastgroup.replace("term", "")
                )

                definition = text_definitions[index]

                tooltip_index = create_tooltip(
                    definition,
                    match.group(0)
                )

                return f"ZXQTOOLTIP{tooltip_index}QXZ"

            text = text_regex.sub(
                replace_text_match,
                text
            )

        # On traite ensuite les commandes LaTeX
        # présentes hors des zones mathématiques.

        if latex_regex is not None:

            def replace_latex_text(match):

                index = int(
                    match.lastgroup.replace("term", "")
                )

                definition = latex_definitions[index]

                tooltip_index = create_tooltip(
                    definition,
                    match.group(0)
                )

                return f"ZXQTOOLTIP{tooltip_index}QXZ"

            text = latex_regex.sub(
                replace_latex_text,
                text
            )

        return text

    # ------------------------------------------
    # Remplacement des expressions LaTeX
    # ------------------------------------------

    def replace_latex(math_content):

        if latex_regex is None:
            return math_content

        def replace(match):

            index = int(
                match.lastgroup.replace("term", "")
            )

            definition = latex_definitions[index]

            tooltip_index = create_tooltip(
                definition,
                match.group(0)
            )

            # La classe term-tooltip est ajoutée directement
            # pour que le style soit immédiatement disponible.

            css_class = (
                f"term-tooltip math-tooltip-{tooltip_index}"
            )

            return (
                rf"\class{{{css_class}}}"
                rf"{{{match.group(0)}}}"
            )

        return latex_regex.sub(
            replace,
            math_content
        )

    # ------------------------------------------
    # Séparation des zones mathématiques
    # ------------------------------------------

    math_pattern = re.compile(
        r"\$\$[\s\S]*?\$\$"
        r"|\\\[[\s\S]*?\\\]"
        r"|(?<!\$)\$(?!\$)(?:\\.|[^$])*?\$(?!\$)"
        r"|\\\([\s\S]*?\\\)"
    )

    result = []
    last_position = 0

    for match in math_pattern.finditer(content):

        text_part = content[
            last_position:match.start()
        ]

        result.append(
            replace_text(text_part)
        )

        math_part = match.group(0)

        result.append(
            replace_latex(math_part)
        )

        last_position = match.end()

    result.append(
        replace_text(content[last_position:])
    )

    processed_content = "".join(result)

    return processed_content, placeholders


# ==================================================
# 4. CONVERSION MARKDOWN
# ==================================================

def convert_markdown(content):
    """
    Convertit le Markdown en HTML en protégeant
    les expressions mathématiques.
    """

    if not content:
        return ""

    math_blocks = []

    def protect_math(match):

        placeholder = (
            f"LATEXBLOCK{len(math_blocks)}PLACEHOLDER"
        )

        math_blocks.append(match.group(0))

        return placeholder

    content = re.sub(
        r"\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]",
        protect_math,
        content
    )

    content = re.sub(
        r"(?<!\$)\$(?!\$)(?:\\.|[^$])*?\$|"
        r"\\\([\s\S]*?\\\)",
        protect_math,
        content
    )

    rendered = markdown.markdown(
        content,
        extensions=[
            "tables",
            "fenced_code",
            "sane_lists",
            "md_in_html"
        ]
    )

    for index, math_block in enumerate(math_blocks):

        rendered = rendered.replace(
            f"LATEXBLOCK{index}PLACEHOLDER",
            math_block
        )

    return rendered


# ==================================================
# 5. AFFICHAGE DES FENÊTRES CONTEXTUELLES
# ==================================================

def display_math_content(content, all_data):
    """
    Affiche un contenu avec :
    - Markdown ;
    - MathJax ;
    - infobulles dans le texte ;
    - infobulles dans les formules ;
    - fenêtres contextuelles interactives.
    """

    processed_content, placeholders = render_with_tooltips(
        content,
        all_data
    )

    rendered_content = convert_markdown(
        processed_content
    )

    # ------------------------------------------
    # Construction des fenêtres contextuelles
    # ------------------------------------------

    templates = []

    for index, entry in enumerate(placeholders):

        tooltip_id = f"tooltip-{index}"

        title = html.escape(
            entry["title"]
        )

        matched_text = html.escape(
            entry["matched_text"]
        )

        tooltip_content = convert_markdown(
            entry["content"]
        )

        tooltip_html = f"""
        <span
            class="term-tooltip"
            data-tooltip-id="{tooltip_id}"
        >
            {matched_text}
        </span>
        """

        rendered_content = rendered_content.replace(
            entry["placeholder"],
            tooltip_html
        )

        templates.append(f"""
        <template id="{tooltip_id}">
            <div class="tooltip-title">
                {title}
            </div>

            <div class="tooltip-content">
                {tooltip_content}
            </div>
        </template>
        """)

    templates_html = "\n".join(templates)

    # ==================================================
    # 6. PAGE HTML
    # ==================================================

    page = f"""
    <!DOCTYPE html>
    <html>

    <head>

        <meta charset="UTF-8">

        <!-- CONFIGURATION MATHJAX -->

        <script>

        window.MathJax = {{

            loader: {{
                load: ['[tex]/html']
            }},

            tex: {{

                inlineMath: [
                    ['$', '$'],
                    ['\\\\(', '\\\\)']
                ],

                displayMath: [
                    ['$$', '$$'],
                    ['\\\\[', '\\\\]']
                ],

                processEscapes: true,

                packages: {{
                    '[+]': ['ams', 'color', 'newcommand', 'html']
                }},

                macros: {macros_json}

            }},

            options: {{

                skipHtmlTags: [
                    'script',
                    'noscript',
                    'style',
                    'textarea',
                    'pre',
                    'code'
                ]

            }}

        }};

        </script>

        <!-- CHARGEMENT MATHJAX -->

        <script
            id="MathJax-script"
            async
            src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">
        </script>


        <!-- CSS -->

        <style>

        * {{
            box-sizing: border-box;
        }}

        body {{

            font-family: Arial, sans-serif;
            font-size: 16px;
            line-height: 1.7;
            color: #333333;
            background: transparent;
            padding: 10px;
            margin: 0;
            overflow-x: hidden;

        }}

        .math-content {{

            width: 100%;
            overflow-wrap: break-word;

        }}

        mjx-container {{

            max-width: 100%;
            overflow-x: auto;
            overflow-y: hidden;

        }}

        /* MOTS ASSOCIÉS À UNE DÉFINITION */

        .term-tooltip {{

            color: #2878c8;
            border-bottom: 1px dotted #2878c8;
            cursor: help;
            font-weight: 500;

        }}

        .term-tooltip:hover {{

            color: #14599c;
            border-bottom: 1px solid #14599c;

        }}

        /* FENÊTRE CONTEXTUELLE */

        #definition-popup {{

            display: none;
            position: fixed;
            z-index: 999999;
            width: 380px;
            max-width: calc(100vw - 24px);
            max-height: 350px;
            overflow-y: auto;
            overflow-x: hidden;
            padding: 16px;
            background: #ffffff;
            color: #222222;
            border: 1px solid #d0d0d0;
            border-radius: 10px;
            box-shadow: 0 5px 25px rgba(0,0,0,0.20);
            font-size: 14px;
            line-height: 1.6;
            overflow-wrap: break-word;
            scrollbar-width: thin;

        }}

        #definition-popup.visible {{
            display: block;
        }}

        .tooltip-title {{

            font-size: 16px;
            font-weight: bold;
            color: #2678c8;
            padding-bottom: 9px;
            margin-bottom: 10px;
            border-bottom: 1px solid #eeeeee;

        }}

        .tooltip-content {{
            display: block;
        }}

        .tooltip-content p {{
            margin: 6px 0;
        }}

        .tooltip-content ul,
        .tooltip-content ol {{
            padding-left: 22px;
        }}

        .tooltip-content mjx-container {{
            font-size: 95% !important;
        }}

        .tooltip-content pre {{

            overflow-x: auto;
            padding: 8px;
            background: #f2f2f2;
            border-radius: 5px;

        }}

        .tooltip-content table {{

            border-collapse: collapse;
            max-width: 100%;

        }}

        .tooltip-content td,
        .tooltip-content th {{

            border: 1px solid #dddddd;
            padding: 5px;

        }}

        </style>

    </head>


    <body>

        <div class="math-content">
            {rendered_content}
        </div>

        <div id="definition-popup"></div>

        {templates_html}


        <!-- JAVASCRIPT -->

        <script>

        const popup = document.getElementById(
            "definition-popup"
        );

        let hideTimeout = null;
        let currentTarget = null;


        // =====================================
        // IDENTIFICATION D'UNE INFOBULLE
        // =====================================

        function getTooltipTarget(node) {{

            if (!(node instanceof Element)) return null;

            const target = node.closest(
                '[data-tooltip-id], [class*="math-tooltip-"]'
            );

            if (!target) return null;

            // Si l'élément ne possède pas encore
            // data-tooltip-id, on récupère son index
            // directement depuis sa classe MathJax.

            if (!target.dataset.tooltipId) {{

                const tooltipClass = Array.from(
                    target.classList
                ).find(name =>
                    name.startsWith("math-tooltip-")
                );

                if (tooltipClass) {{

                    const index = tooltipClass.substring(
                        "math-tooltip-".length
                    );

                    target.dataset.tooltipId =
                        "tooltip-" + index;

                }}

            }}

            return target.dataset.tooltipId
                ? target
                : null;

        }}


        // =====================================
        // ASSOCIATION DES CLASSES MATHJAX
        // =====================================

        function bindMathTooltips(root = document) {{

            const elements = [];

            if (
                root instanceof Element &&
                root.matches('[class*="math-tooltip-"]')
            ) {{
                elements.push(root);
            }}

            elements.push(
                ...root.querySelectorAll(
                    '[class*="math-tooltip-"]'
                )
            );

            elements.forEach(element => {{

                const tooltipClass = Array.from(
                    element.classList
                ).find(name =>
                    name.startsWith("math-tooltip-")
                );

                if (!tooltipClass) return;

                const index = tooltipClass.substring(
                    "math-tooltip-".length
                );

                if (!element.dataset.tooltipId) {{

                    element.dataset.tooltipId =
                        "tooltip-" + index;

                }}

                element.classList.add("term-tooltip");

                element.style.cursor = "help";

            }});

        }}


        // =====================================
        // POSITIONNEMENT INTELLIGENT
        // =====================================

        function positionPopup(target) {{

            if (!target || !target.isConnected) return;

            const rect = target.getBoundingClientRect();

            const margin = 12;
            const gap = 10;

            const popupWidth = Math.min(
                380,
                window.innerWidth - 2 * margin
            );

            const popupHeight = popup.offsetHeight;

            let left = (
                rect.left + rect.width / 2
                - popupWidth / 2
            );

            left = Math.min(
                left,
                window.innerWidth - popupWidth - margin
            );

            left = Math.max(margin, left);

            let top = rect.bottom + gap;

            if (
                top + popupHeight >
                window.innerHeight - margin
            ) {{
                top = rect.top - popupHeight - gap;
            }}

            top = Math.max(
                margin,
                Math.min(
                    top,
                    window.innerHeight - popupHeight - margin
                )
            );

            popup.style.left = left + "px";
            popup.style.top = top + "px";

            popup.style.maxHeight = (
                window.innerHeight - 2 * margin
            ) + "px";

        }}


        // =====================================
        // AFFICHAGE D'UNE DÉFINITION
        // =====================================

        function showTooltip(target) {{

            if (!target) return;

            clearTimeout(hideTimeout);

            currentTarget = target;

            // On récupère aussi l'identifiant depuis
            // la classe si nécessaire.

            target = getTooltipTarget(target);

            if (!target) return;

            currentTarget = target;

            const id = target.dataset.tooltipId;

            if (!id) return;

            const template = document.getElementById(id);

            if (!template) {{

                console.warn(
                    "Template introuvable :",
                    id
                );

                return;

            }}

            popup.innerHTML = template.innerHTML;

            popup.classList.add("visible");

            function renderMath() {{

                if (
                    window.MathJax &&
                    window.MathJax.typesetPromise
                ) {{

                    window.MathJax.typesetClear([popup]);

                    window.MathJax.typesetPromise([popup])

                        .then(() => {{

                            bindMathTooltips(popup);

                            positionPopup(target);

                        }})

                        .catch(error => {{

                            console.error(
                                "Erreur MathJax :",
                                error
                            );

                        }});

                }} else {{

                    positionPopup(target);

                }}

            }}

            positionPopup(target);

            if (
                window.MathJax &&
                window.MathJax.startup &&
                window.MathJax.startup.promise
            ) {{

                window.MathJax.startup.promise.then(
                    renderMath
                );

            }} else {{

                renderMath();

            }}

        }}


        // =====================================
        // MASQUAGE AVEC DÉLAI
        // =====================================

        function hideTooltip() {{

            clearTimeout(hideTimeout);

            hideTimeout = setTimeout(() => {{

                popup.classList.remove("visible");
                currentTarget = null;

            }}, 180);

        }}


        // =====================================
        // ÉVÉNEMENTS SOURIS
        // =====================================

        document.addEventListener(
            "mouseover",
            function(event) {{

                const target = getTooltipTarget(
                    event.target
                );

                if (!target) return;

                if (
                    event.relatedTarget instanceof Node &&
                    target.contains(event.relatedTarget)
                ) {{
                    return;
                }}

                showTooltip(target);

            }}
        );


        document.addEventListener(
            "mouseout",
            function(event) {{

                const target = getTooltipTarget(
                    event.target
                );

                if (!target) return;

                if (
                    event.relatedTarget instanceof Node &&
                    target.contains(event.relatedTarget)
                ) {{
                    return;
                }}

                hideTooltip();

            }}
        );


        // =====================================
        // ÉVÉNEMENTS DE LA FENÊTRE
        // =====================================

        popup.addEventListener(
            "mouseenter",
            function() {{
                clearTimeout(hideTimeout);
            }}
        );


        popup.addEventListener(
            "mouseleave",
            function() {{
                hideTooltip();
            }}
        );


        // =====================================
        // REPOSITIONNEMENT LORS DU SCROLL
        // =====================================

        window.addEventListener(
            "scroll",
            function() {{

                if (
                    popup.classList.contains("visible")
                    && currentTarget
                ) {{
                    positionPopup(currentTarget);
                }}

            }},
            true
        );


        // =====================================
        // REPOSITIONNEMENT LORS DU REDIMENSIONNEMENT
        // =====================================

        window.addEventListener(
            "resize",
            function() {{

                if (
                    popup.classList.contains("visible")
                    && currentTarget
                ) {{
                    positionPopup(currentTarget);
                }}

            }}
        );


        // =====================================
        // SURVEILLANCE DU RENDU MATHJAX
        // =====================================

        const mathContent = document.querySelector(
            ".math-content"
        );

        const mathObserver = new MutationObserver(() => {{

            bindMathTooltips(mathContent);

        }});

        mathObserver.observe(
            mathContent,
            {{
                childList: true,
                subtree: true
            }}
        );


        // =====================================
        // INITIALISATION APRÈS MATHJAX
        // =====================================

        if (
            window.MathJax &&
            window.MathJax.startup
        ) {{

            window.MathJax.startup.promise.then(() => {{

                bindMathTooltips(document);

            }}).catch(error => {{

                console.error(
                    "Erreur lors de l'initialisation MathJax :",
                    error
                );

            }});

        }}

        </script>

    </body>

    </html>
    """

    # ==================================================
    # 7. AFFICHAGE DANS STREAMLIT
    # ==================================================

    components.html(
        page,
        height=250,
        scrolling=True
    )
