"""Prompt builders for the banner."""

STYLES = {
    "Clean dark": "a clean, modern dark theme with a subtle gradient and soft glow accents",
    "Minimal light": "a minimal light theme with lots of whitespace and one calm accent color",
    "Cyberpunk neon": "a cyberpunk look with neon magenta and cyan lines on a deep navy background",
    "Retro pixel art": "retro pixel art with a limited color palette and crisp pixel edges",
    "Watercolor": "soft watercolor washes with gentle hand-painted texture",
    "Blueprint": "a technical blueprint look with white linework on deep blue and a faint grid",
}

ASPECT_RATIOS = {
    "4:1 banner": "4:1",
    "16:9 wide": "16:9",
    "21:9 ultrawide": "21:9",
}


def banner_prompt(name: str, tagline: str, stack: list[str], style: str) -> str:
    stack_line = ", ".join(stack) if stack else "software and code in general"
    parts = [
        "Design a wide GitHub profile README banner.",
        f"Visual style: {STYLES.get(style, style)}.",
        f'Show the name "{name}" in large, clear lettering.',
    ]
    if tagline:
        parts.append(f'Show the tagline "{tagline}" beneath it in smaller lettering.')
    parts += [
        f"Add small, tasteful motifs that hint at: {stack_line}.",
        "Render the text exactly as written and spelled correctly.",
        "Keep generous margins so nothing touches the edges.",
        "Use no other words, no real company logos and no people.",
    ]
    return " ".join(parts)


def edit_prompt(change: str) -> str:
    return f"{change.strip()} Keep everything else in the banner unchanged, including the text."
