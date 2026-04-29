# AI News Pipeline
### Homework 2 — Generative AI for Business
*An AI-powered news ingestion, relevance scoring, classification, and LinkedIn content generation platform.*

---

## Project Overview

This project is a full-stack AI pipeline that automatically monitors trusted AI industry sources, evaluates each article for business relevance using a large language model, classifies relevant articles into business categories, and generates thought leadership LinkedIn content — all presented through a 6-tab Flask web dashboard.

The pipeline is built around two core stages:
- **Backend:** RSS ingestion → LLM relevance scoring (OpenRouter) → LLM classification (OpenRouter) → SQLite storage
- **Frontend:** Flask web app with live database queries, KOL research, AI-generated LinkedIn posts, and a structured progress report

---

## Domain Focus & Design Choices

### Industry Domain

This pipeline was built around the following focus areas:

- AI-powered SaaS products and platforms
- Consumer AI tools and their latest developments
- Trends and shifts in the AI tools landscape
- Practical AI adoption — tips, frameworks, and real-world use cases
- Agent frameworks and automation tools
- Foundation model updates relevant to end users (GPT, Claude, Gemini, Llama, etc.)

**Target audience:** AI enthusiasts, students, and industry professionals who want a curated, high-signal source of news around AI — to stay current on relevant developments, trends, and applications without manual web searches.

### Data Ingestion Window

Due to the low availability of articles published on any single day (sometimes fewer than 10 per day across all sources), the ingestion pipeline was configured to collect articles published within the **last 7 days** rather than just today. This ensures a meaningful volume of articles (typically 80–130) for analysis while remaining timely and relevant.

### Relevance Criteria

All five relevance criteria from the assignment description were incorporated into the relevance scoring prompt:

- **Strategic impact** — does this article affect how companies position themselves in the AI landscape?
- **Revenue or cost implications** — does it relate to pricing, ROI, or cost efficiency of AI tools?
- **Competitive advantage** — does it signal a shift in competitive dynamics between AI products or platforms?
- **Operational efficiency** — does it relate to productivity, workflow automation, or process improvement?
- **Regulatory or governance considerations** — does it involve AI policy, ethics, or compliance that affects tool accessibility?

Articles are scored 1–10 against these criteria. Only articles scoring **8 or above** are retained for classification and content generation.

### Classification Categories

Relevant articles are classified into one of five business categories:

| Pipeline Category | Homework Mapping |
|---|---|
| New AI Tools & Product Launches | Product and Service Innovation |
| AI Trends & Market Movements | Strategy and Executive Decision-Making |
| Practical AI Use Cases | Industry-Specific AI Use Cases |
| Foundation Models & Platforms | Infrastructure, Models, and Platforms |
| AI Governance & Ethics | Governance, Ethics, and Regulation |

---

## For the Course Instructor

### ✅ No API Keys Required to View the Site

This project includes pre-collected, pre-scored, and pre-classified article data committed directly to the repository. When you clone and run the app, the website will automatically load this seed data and display all content — including relevance scores, classifications, KOL research, and generated LinkedIn posts — without requiring any API credentials.

A status banner on Tab 1 (Pipeline & Sources) will confirm whether you are viewing pre-collected seed data or live pipeline data.

### ▶️ Quickstart — View the Site in 3 Steps

**Step 1 — Clone the repository**
```bash
git clone https://github.com/Totoro-DustBunny/ai-news-pipeline.git
cd ai-news-pipeline
```

**Step 2 — Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 3 — Launch the web app**
```bash
python app.py
```

Then open your browser and go to: **http://localhost:5000**

That's it. No API keys, no pipeline run, no configuration needed.

---

## Project Structure

```
ai-news-pipeline/
├── app.py                        ← Flask web application entry point
├── run_pipeline.py               ← Orchestrates the full pipeline (optional)
├── requirements.txt              ← Python dependencies
├── .env.example                  ← API key template (copy to .env to use)
├── config/
│   ├── sources.yaml              ← RSS feed sources configuration
│   └── domain_profile.yaml       ← Relevance domain definition
├── pipeline/
│   ├── ingest.py                 ← RSS ingestion + seed loader
│   ├── router.py                 ← Relevance scoring via OpenRouter
│   └── classifier.py             ← Article classification via OpenRouter
├── prompts/
│   ├── relevance_prompt.txt      ← LLM prompt for relevance scoring
│   └── classification_prompt.txt ← LLM prompt for classification
├── scripts/
│   ├── fetch_kol_posts.py        ← KOL LinkedIn post research
│   ├── generate_linkedin.py      ← LinkedIn post + image generation
│   └── export_seed.py            ← Exports DB to seed file
├── data/
│   ├── articles_seed.json        ← Pre-collected article data (committed)
│   ├── kol_posts.json            ← KOL research data (committed)
│   └── linkedin_posts.json       ← Generated LinkedIn posts (committed)
├── storage/
│   └── articles.db               ← SQLite database (not committed to GitHub)
├── static/
│   ├── css/styles.css
│   ├── js/main.js
│   └── images/linkedin/          ← Generated LinkedIn post images
└── templates/
    └── index.html                ← Single-page Flask template
```

---

## Web App — Tab Guide

Once the app is running at http://localhost:5000, navigate using the top tab bar:

| Tab | Title | What It Shows |
|---|---|---|
| 01 | Pipeline & Sources | Project overview, monitored sources, domain focus, data status banner |
| 02 | Relevance Scoring | All 122 articles with scores, relevance reasons, and criteria tags |
| 03 | Classification | 61 relevant articles grouped into 5 business categories with chart |
| 04 | KOL Research | LinkedIn analysis of 5 AI thought leaders + post anatomy checklist |
| 05 | LinkedIn Content | 3 AI-generated LinkedIn posts with images, one per category |
| 06 | Progress Report | Workflow architecture, challenges, prompt iterations, lessons learned |


## Optional: Re-Running the Pipeline with Your Own API Keys

The pipeline can be re-run at any time to fetch fresh articles. This step is **entirely optional** for reviewing this homework submission.

### Required API Keys

| Key | Service | Purpose | Get It At |
|---|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter | Relevance scoring + classification + KOL style extraction + LinkedIn text generation | openrouter.ai |
| `OPENAI_API_KEY` | OpenAI | LinkedIn post image generation (DALL-E 3) | platform.openai.com |

### Setup

**1. Create your `.env` file**
```bash
# Mac/Linux:
cp .env.example .env

# Windows PowerShell:
Copy-Item .env.example .env
```

**2. Add your API keys to `.env`**
```
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

**3. Run the full pipeline**
```bash
python run_pipeline.py
```

This will:
1. Reset the database and re-ingest articles from the last 7 days
2. Score all articles for relevance via OpenRouter (Llama 3.3 70B)
3. Classify relevant articles into 5 categories via OpenRouter (Llama 4 Maverick)

**4. Optionally regenerate KOL research and LinkedIn posts**
```bash
python scripts/fetch_kol_posts.py
python scripts/generate_linkedin.py
```

**5. Optionally export a new seed file**
```bash
python scripts/export_seed.py
```

**6. Relaunch the web app**
```bash
python app.py
```

### Models Used

| Step | Model | Role |
|---|---|---|
| Relevance scoring | `meta-llama/llama-3.3-70b-instruct` | Primary scorer |
| Relevance fallback | `mistralai/mistral-nemo` | Fallback if primary fails |
| Classification | `meta-llama/llama-4-maverick` | Primary classifier |
| Classification fallback | `meta-llama/llama-3.3-70b-instruct` | Fallback if primary fails |
| LinkedIn text | `meta-llama/llama-4-maverick` | Post generation |
| LinkedIn images | `dall-e-3` (OpenAI) | Image generation |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| Web framework | Flask |
| Database | SQLite |
| LLM routing | OpenRouter (OpenAI-compatible SDK) |
| Image generation | OpenAI DALL-E 3 |
| RSS parsing | feedparser |
| KOL research | duckduckgo-search |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Version control | GitHub |

---

## Key Design Decisions

**Two-stage LLM pipeline:** A cheaper, faster model (Llama 3.3 70B) acts as a relevance gate, filtering ~50% of articles before the more capable classifier (Llama 4 Maverick) processes only the relevant subset. This reduces token usage by approximately 50% compared to running a single premium model on all articles.

**SQLite over a vector database:** For a pipeline processing 80–130 articles per run, SQLite provides sufficient performance with zero infrastructure overhead. The schema is designed for easy migration to ChromaDB or PostgreSQL if semantic search is added in the future.

**OpenRouter for resilience:** Using OpenRouter's fallback model routing means the pipeline never crashes on a single model outage — every API call has an automatic retry on an alternative model.

**Seed data for portability:** Article data, KOL research, and LinkedIn posts are exported to JSON and committed to the repository, allowing the web app to run without any API keys for review and presentation purposes.

---

*Generative AI for Business — Graduate Course*
*Built with Claude Code · OpenRouter · OpenAI · Flask · SQLite*
