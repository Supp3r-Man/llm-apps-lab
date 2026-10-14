import os

import streamlit as st
from google import genai

from github_profile import GitHubLookupError, lookup_profile
from nanobanana import DEFAULT_MODEL, MODELS, ImageGenerationError, fit_to_width, generate_image
from prompts import ASPECT_RATIOS, STYLES, banner_prompt, edit_prompt

OUTPUT_WIDTH = 1500

st.set_page_config(page_title="Profile Banner Studio", page_icon="🍌", layout="wide")
st.title("🍌 Profile Banner Studio")
st.caption("Generate a GitHub profile banner with Nano Banana, then refine it by describing changes.")

ss = st.session_state
ss.setdefault("png", None)
ss.setdefault("interaction_id", None)
ss.setdefault("history", [])
ss.setdefault("form", {"handle": "", "name": "", "tagline": "", "stack": ""})

with st.sidebar:
    api_key = st.text_input(
        "Gemini API key",
        value=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "",
        type="password",
        help="Get one at aistudio.google.com/apikey. It is only used for this session.",
    )
    model_labels = list(MODELS)
    default_index = list(MODELS.values()).index(DEFAULT_MODEL) if DEFAULT_MODEL in MODELS.values() else 0
    model = MODELS[st.selectbox("Model", model_labels, index=default_index)]
    image_size = st.selectbox("Generation size", ["1K", "2K"], help="2K costs more and takes longer.")
    st.caption("Generated images carry Google's SynthID watermark.")

left, right = st.columns([2, 3])

with left:
    st.subheader("1. About you")
    handle = st.text_input("GitHub handle (optional)", value=ss.form["handle"], placeholder="octocat")
    if st.button("Prefill from GitHub", disabled=not handle):
        try:
            info = lookup_profile(handle)
            ss.form = {
                "handle": info["handle"],
                "name": info["name"],
                "tagline": info["bio"][:90],
                "stack": ", ".join(info["languages"]),
            }
            st.rerun()
        except GitHubLookupError as exc:
            st.error(str(exc))

    name = st.text_input("Name on the banner", value=ss.form["name"], max_chars=40)
    tagline = st.text_input("Tagline", value=ss.form["tagline"], max_chars=90)
    stack = st.text_input("Tech stack (comma separated)", value=ss.form["stack"])
    style = st.selectbox("Style", list(STYLES))
    aspect_label = st.selectbox("Shape", list(ASPECT_RATIOS))

    if st.button("Generate banner", type="primary", disabled=not (api_key and name.strip())):
        client = genai.Client(api_key=api_key)
        prompt = banner_prompt(name.strip(), tagline.strip(), [s.strip() for s in stack.split(",") if s.strip()], style)
        with st.spinner("Generating..."):
            try:
                result = generate_image(
                    client, prompt, model=model, aspect_ratio=ASPECT_RATIOS[aspect_label], image_size=image_size
                )
            except ImageGenerationError as exc:
                st.error(str(exc))
            else:
                ss.png, ss.interaction_id = result.png, result.interaction_id
                ss.history = [("Generated", result.png)]
    if not api_key:
        st.info("Enter your Gemini API key in the sidebar to start.")

with right:
    st.subheader("2. Preview and refine")
    if ss.png is None:
        st.write("Your banner will appear here.")
    else:
        st.image(ss.png, use_container_width=True)
        change = st.text_input("Describe a change", placeholder="Make the background darker and add a subtle grid")
        if st.button("Apply change", disabled=not (change.strip() and ss.interaction_id and api_key)):
            client = genai.Client(api_key=api_key)
            with st.spinner("Editing..."):
                try:
                    result = generate_image(
                        client,
                        edit_prompt(change),
                        model=model,
                        aspect_ratio=ASPECT_RATIOS[aspect_label],
                        image_size=image_size,
                        previous_interaction_id=ss.interaction_id,
                    )
                except ImageGenerationError as exc:
                    st.error(str(exc))
                else:
                    ss.png, ss.interaction_id = result.png, result.interaction_id
                    ss.history.append((change.strip(), result.png))
                    st.rerun()

        final = fit_to_width(ss.png, OUTPUT_WIDTH)
        st.download_button("Download PNG", final, file_name="banner.png", mime="image/png")
        st.code("![Banner](banner.png)", language="markdown")

        if len(ss.history) > 1:
            with st.expander(f"Edit history ({len(ss.history)} versions)"):
                for label, png in ss.history:
                    st.caption(label)
                    st.image(png, use_container_width=True)
