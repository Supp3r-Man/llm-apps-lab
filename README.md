# LLM Apps Lab

Eight LLM apps: six adapted from the open-source
[awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) collection,
and two original apps built on Google's Nano Banana image models. The adapted code
is by Shubham Saboo and contributors; see [Attribution](#attribution). You bring your own API keys. Nothing is stored.

| App | What it does | Stack | Keys / needs |
|---|---|---|---|
| [Video Moment Finder](apps/video-moment-finder) | Search a video by screenshot or text description and jump to the moment. No transcription. | Gemini Embedding 2, ChromaDB, FastAPI, Next.js | Google AI key, `ffmpeg` |
| [Needle](apps/needle-semantic-find) | Find-in-page by meaning. Highlights the sentence that answers your query. Chrome extension plus React app. | Node 22.12+, React, TypeSafe Jev via Vercel AI Gateway | Vercel AI Gateway key with credits |
| [Ripple](apps/ripple-edit-impact) | Edit one fact in a Google Doc and see which other sentences now disagree, with suggested fixes. | Chrome extension, Node 22+, TypeSafe Jev, Gemini | TypeSafe key, Gemini key |
| [Critique & Improvement Loop](apps/critique-improvement-loop) | Generate an answer, critique it, revise it, repeat for one to three rounds. | Streamlit, GPT-OSS on Groq | Groq key |
| [Headroom Context Optimization](apps/headroom-context-optimization) | Compresses bulky tool output before it reaches the model. The demo runs the real library and checks that the key facts survive. Measured 40.5% fewer tokens on its sample. | Headroom | None for the demo |
| [Toonify Token Optimization](apps/toonify-token-optimization) | Compares JSON with the more compact TOON format, with token counts and a cost calculator. Streamlit app. | Toonify, tiktoken | None for the demo |
| [Profile Banner Studio](apps/profile-banner-studio) *(original)* | Generate a GitHub profile banner with Nano Banana, then refine it with follow-up instructions. Prefills from your GitHub profile. | Nano Banana, Streamlit | Google AI key |
| [Repo Social Preview](apps/repo-social-preview) *(original)* | Make a repo's 1280x640 social preview: AI background plus crisp, correctly spelled text drawn by Pillow. | Nano Banana, Pillow, Streamlit | Google AI key |

Each app has its own README with setup steps.

## Attribution

Profile Banner Studio and Repo Social Preview are original work, released under the same
Apache License 2.0. The other six apps are adapted from
[awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) by
Shubham Saboo and contributors, under the Apache License 2.0. See
[NOTICE](NOTICE) and [LICENSE](LICENSE).
