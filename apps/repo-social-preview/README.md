# 🍌 Repo Social Preview

Make the 1280 × 640 social preview image for a GitHub repository. Nano Banana paints the background from the repo's description, topics, language and README. The app then draws the repository name and description on top as real text, so they are never misspelled.

This is an original app, not adapted from awesome-llm-apps.

## How it works

1. Enter a public repo (`owner/name` or a URL). The app reads its description, topics, language, stars and README through the GitHub API.
2. Pick a style. The model generates a 16:9 background that is told to contain no text and to keep the left half calm.
3. The app center-crops it to 2:1, adds a soft dark gradient on the left, and draws the title, description and footer with a system font. Long names wrap at hyphens and shrink to fit.
4. Edit the text freely. The preview updates instantly with no new model call.
5. Download the PNG.

## Run it

You need a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

```bash
cd apps/repo-social-preview
pip install -r requirements.txt
export GEMINI_API_KEY=your-key     # or paste it in the sidebar
streamlit run app.py
```

Optional: set `GITHUB_TOKEN` to avoid GitHub's unauthenticated rate limit, and `NANOBANANA_MODEL` to change the default model.

GitHub has no API for social previews, so upload the PNG by hand: repository Settings, General, Social preview, Edit.

## Notes

- **Models.** The sidebar lists the Nano Banana model IDs from Google's [image generation docs](https://ai.google.dev/gemini-api/docs/image-generation) (default `gemini-nano-banana-2.1`). Edit `MODELS` in `nanobanana.py` if one is retired.
- **Fonts.** The text uses Segoe UI, Arial, DejaVu Sans or Helvetica, whichever your system has, and falls back to Pillow's built-in font. The footer uses plain characters only because some fonts lack symbols such as stars.
- **README as context.** A short, cleaned excerpt of the README goes into the image prompt for visual inspiration. Treat it as untrusted text: at worst it nudges the artwork.
- **Cost and watermark.** Image generation is billed by Google. Generated images carry a SynthID watermark.
- **Privacy.** Your key stays in the Streamlit session and is sent only to Google. Only public repo data is read.

## Tests

```bash
pip install pytest
pytest tests
```

The tests check the compositor on real pixels (output size, text stays in its column and off the edges, long names wrap and shrink), the GitHub parsing with mocked responses, and the request the real Google SDK sends to a fake server, plus the full UI flow. They have not been run against the live Google API.
