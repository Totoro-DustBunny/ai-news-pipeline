# AI News Pipeline

AI-powered news ingestion, relevance routing, and classification pipeline focused on AI tools,
AI-powered SaaS, and emerging AI developments. Built for a graduate course in Generative AI for Business.

## Project Structure

```
ai-news-pipeline/
├── config/           # Source feeds and domain profile configuration
├── pipeline/         # Core pipeline modules (ingest, router, classifier)
├── prompts/          # LLM prompt templates
├── storage/          # SQLite database (created at runtime)
└── outputs/          # Generated content (e.g., LinkedIn posts)
```

## Setup

1. Copy `.env.example` to `.env` and fill in your API key.
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your sources in `config/sources.yaml`.
