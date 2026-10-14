# 🍌 Profile Banner Studio

Generate a banner for your GitHub profile README with Google's Nano Banana image models, then refine it by describing changes in plain language ("make the background darker", "add a subtle grid"). Each edit continues the same conversation, so the model changes only what you asked for.

This is an original app, not adapted from awesome-llm-apps.

## What it does

- Prefills your name, bio and most-used languages from your public GitHub profile (optional).
- Builds a prompt from your name, tagline, tech stack and a style, then generates the banner.
- Refines the banner with follow-up instructions through the Interactions API's `previous_interaction_id`.
- Keeps an edit history and exports a PNG resized to 1500 px wide.

## Run it

You need a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
cd apps/profile-banner-studio
pip install -r requirements.txt
export GEMINI_API_KEY=your-key     # or paste it in the sidebar
streamlit run app.py
```

Optional: set `GITHUB_TOKEN` to avoid GitHub's unauthenticated rate limit during prefill, and `NANOBANANA_MODEL` to change the default model.

Then commit the PNG to your profile repo and reference it:

```markdown
![Banner](banner.png)
```

## Notes

- **Models.** The sidebar lists the Nano Banana model IDs from Google's [image generation docs](https://ai.google.dev/gemini-api/docs/image-generation) (default `gemini-nano-banana-2.1`). Model names change, so edit `MODELS` in `nanobanana.py` if one is retired.
- **Shapes.** 4:1, 16:9 and 21:9 are offered. Not every model supports every ratio or size. If one is rejected, the API's message is shown.
- **Text in images.** The model draws the text, so check the spelling of the result. If it is wrong, ask for a fix in the edit box. The sibling app [Repo Social Preview](../repo-social-preview) draws text with a font instead, which avoids this.
- **Cost and watermark.** Image generation is billed by Google. Generated images carry a SynthID watermark.
- **Privacy.** Your key stays in the Streamlit session and is sent only to Google. The GitHub lookup uses public data.

## Tests

```bash
pip install pytest
pytest tests
```

The tests run the real Google SDK against a fake HTTP server, so they check the request the SDK sends (model, `response_format`, `previous_interaction_id`), error handling, the GitHub lookup with mocked responses, and the full generate-then-edit flow through the UI. They have not been run against the live Google API.
