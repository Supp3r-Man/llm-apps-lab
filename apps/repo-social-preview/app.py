import os

import streamlit as st
from google import genai

from compose import compose_preview
from github_repo import RepoLookupError, fetch_repo, parse_repo
from nanobanana import DEFAULT_MODEL, MODELS, ImageGenerationError, generate_image
from prompts import STYLES, background_prompt

st.set_page_config(page_title="Repo Social Preview", page_icon="🍌", layout="wide")
st.title("🍌 Repo Social Preview")
st.caption(
    "Nano Banana paints the background. The repo name and description are drawn as real text, so they are never misspelled."
)

ss = st.session_state
ss.setdefault("info", None)
ss.setdefault("background", None)
ss.setdefault("title", "")
ss.setdefault("subtitle", "")
ss.setdefault("meta", "")

with st.sidebar:
    api_key = st.text_input(
        "Gemini API key",
        value=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "",
        type="password",
        help="Get one at aistudio.google.com/apikey. It is only used for this session.",
    )
    labels = list(MODELS)
    default_index = list(MODELS.values()).index(DEFAULT_MODEL) if DEFAULT_MODEL in MODELS.values() else 0
    model = MODELS[st.selectbox("Model", labels, index=default_index)]
    image_size = st.selectbox("Generation size", ["1K", "2K"], help="1K is plenty for a 1280x640 preview.")
    st.caption("Generated images carry Google's SynthID watermark.")

left, right = st.columns([2, 3])

with left:
    st.subheader("1. Pick a repository")
    repo_text = st.text_input("Public repo", placeholder="owner/name or https://github.com/owner/name")
    if st.button("Fetch repo", disabled=not repo_text.strip()):
        try:
            info = fetch_repo(*parse_repo(repo_text))
        except RepoLookupError as exc:
            st.error(str(exc))
        else:
            ss.info = info
            ss.title = info["name"]
            ss.subtitle = info["description"]
            ss.meta = " · ".join(
                bit for bit in (info["language"], f"{info['stars']:,} stars" if info["stars"] else "") if bit
            )
            ss.background = None
            st.rerun()

    if ss.info:
        st.subheader("2. Background")
        style = st.selectbox("Style", list(STYLES))
        if st.button("Generate background", type="primary", disabled=not api_key):
            client = genai.Client(api_key=api_key)
            with st.spinner("Generating..."):
                try:
                    result = generate_image(
                        client,
                        background_prompt(ss.info, style),
                        model=model,
                        aspect_ratio="16:9",
                        image_size=image_size,
                    )
                except ImageGenerationError as exc:
                    st.error(str(exc))
                else:
                    ss.background = result.png
        if not api_key:
            st.info("Enter your Gemini API key in the sidebar to generate.")

        st.subheader("3. Text")
        st.text_input("Title", key="title", max_chars=60)
        st.text_area("Subtitle", key="subtitle", max_chars=160, height=80)
        st.text_input("Footer line", key="meta", max_chars=60)

with right:
    st.subheader("Preview (1280 × 640)")
    if ss.background is None:
        st.write("Fetch a repo and generate a background to see the preview.")
    else:
        final = compose_preview(ss.background, ss.title or ss.info["name"], ss.subtitle, ss.meta)
        st.image(final, use_container_width=True)
        st.download_button("Download PNG", final, file_name="social-preview.png", mime="image/png")
        st.caption(
            "GitHub has no API for this, so upload it by hand: repository Settings, then General, "
            "then Social preview, then Edit."
        )
