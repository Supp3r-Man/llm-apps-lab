"""Prompt builder for the background art."""

STYLES = {
    "Abstract gradient": "smooth abstract gradients and flowing shapes",
    "Isometric tech": "clean isometric 3D shapes and blocks",
    "Circuit board": "glowing circuit-board traces and nodes",
    "Network graph": "an elegant network of connected nodes and lines",
    "Paper cutout": "layered paper-cut shapes with soft shadows",
    "Synthwave": "a synthwave sunset with a perspective grid",
}


def background_prompt(info: dict, style: str) -> str:
    topics = ", ".join(info.get("topics", [])[:5])
    theme_bits = [
        f"a software project called {info['name']}",
        f"described as: {info['description']}" if info.get("description") else "",
        f"topics: {topics}" if topics else "",
        f"written mainly in {info['language']}" if info.get("language") else "",
    ]
    theme = "; ".join(b for b in theme_bits if b)
    context = info.get("readme_excerpt", "")[:600]
    parts = [
        "Create a wide background illustration for a software repository social preview image.",
        f"Theme: {theme}.",
        f"Visual style: {STYLES.get(style, style)}, polished and modern.",
        "Use a rich, fairly dark color palette.",
        "Keep the left half simple and calm with low detail, and put the visual interest on the right.",
        "Do not include any text, letters, numbers, logos or watermarks.",
    ]
    if context:
        parts.append(f"For visual inspiration only, the project's README begins: {context}")
    return " ".join(parts)
