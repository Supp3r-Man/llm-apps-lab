# LLM Apps Lab

Four LLM apps adapted from the open-source
[awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) collection.
The original code is by Shubham Saboo and contributors; see
[Attribution](#attribution). You bring your own API keys. Nothing is stored.

| App | What it does | Stack | Keys / needs |
|---|---|---|---|
| [Video Moment Finder](apps/video-moment-finder) | Search a video by screenshot or text description and jump to the moment. No transcription. | Gemini Embedding 2, ChromaDB, FastAPI, Next.js | Google AI key, `ffmpeg` |
| [Needle](apps/needle-semantic-find) | Find-in-page by meaning. Highlights the sentence that answers your query. Chrome extension plus React app. | Node 22.12+, React, TypeSafe Jev via Vercel AI Gateway | Vercel AI Gateway key with credits |
| [Ripple](apps/ripple-edit-impact) | Edit one fact in a Google Doc and see which other sentences now disagree, with suggested fixes. | Chrome extension, Node 22+, TypeSafe Jev, Gemini | TypeSafe key, Gemini key |
| [Critique & Improvement Loop](apps/critique-improvement-loop) | Generate an answer, critique it, revise it, repeat for one to three rounds. | Streamlit, GPT-OSS on Groq | Groq key |

Each app has its own README with setup steps.

## Attribution

These apps are adapted from
[awesome-llm-apps](https://github.com/Shubhamsaboo/awesome-llm-apps) by
Shubham Saboo and contributors, under the Apache License 2.0. See
[NOTICE](NOTICE) and [LICENSE](LICENSE).
