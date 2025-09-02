# RAG Demo (LangChain + Chroma + OpenAI)

A minimal, modular Retrieval-Augmented Generation (RAG) pipeline for UK VAT guidance.  
It **scrapes** GOV.UK pages, **chunks** the text, **indexes** it locally with **Chroma**, and **answers questions** with **LangChain + OpenAI** using grounded context and **citations**.

## Features
- 🔎 **Scrape & clean** GOV.UK pages (navigation/boilerplate removed; lists preserved as bullets)
- ✂️ **Chunking** (~100–300 words) with rich metadata (`title`, `source_url`, `tags`, `date_scraped`, `chunk_index`)
- 📦 **Local** Chroma index (DuckDB/Parquet on disk — no cloud)
- 💬 **RAG QA**: retrieve **top-k** chunks (default 3), inject into prompt, return grounded answers with **citations**
- ⚙️ Clear modules & CLI entry points: `scrape → chunk → index → ask`
- 📝 Ready for demos: `.env.example`, `README`, and a small FAQ/LLD

---

## How it works (RAG in 30 seconds)
1. **Ingest**: scrape target URLs and save cleaned text snapshots.
2. **Prepare**: split snapshots into paragraph-like blocks and merge to size-bounded chunks (100–300 words).
3. **Index**: embed chunks and store vectors + metadata in **Chroma** (local).
4. **Answer**: embed the user’s question, retrieve **top-k** similar chunks, inject as **Context** to the LLM, and return a concise answer + **Sources**.

```
URLs → scrape_govuk.py → data/raw/*.txt
           ↓
        chunker.py → data/processed/chunks.jsonl
           ↓
      build_index.py → ./chroma (local vector DB)
           ↓
           ask.py → top-k chunks → LLM → grounded answer + citations
```

---

## Repo structure
```
.
├─ src/
│  ├─ scrape_govuk.py     # Requests + BeautifulSoup → clean text snapshots
│  ├─ chunker.py          # Paragraph-aware chunking (100–300 words) → JSONL
│  ├─ build_index.py      # Build Chroma index (local, persistent)
│  └─ ask.py              # Retrieve top-k, prompt LLM, print answer + Sources
├─ data/
│  ├─ raw/                # Scraped .txt snapshots (input to chunker)
│  └─ processed/
│     └─ chunks.jsonl     # Chunked corpus with metadata
├─ chroma/                # (generated) local vector DB
├─ .env.example           # Template for API keys/models
├─ requirements.txt
├─ README.md
└─ FAQ_RAG_VAT.md         # (optional) client-friendly FAQ & walkthrough
```

---

## Requirements
- Python **3.10+** (3.11 recommended)
- OpenAI API key
- Internet access (for scraping and LLM calls)

> Uses the current **`langchain-chroma`** package (the old `langchain_community.vectorstores.Chroma` is deprecated).

---

## Quickstart

```bash
# 1) Clone / open the repo, then:
python -m venv .venv
# mac/linux
source .venv/bin/activate
# windows (powershell)
# .venv\Scripts\Activate.ps1

# 2) Install deps
pip install -r requirements.txt

# 3) Configure environment
cp .env.example .env
# open .env and set:
# OPENAI_API_KEY=sk-...
# (optional) LLM_MODEL=gpt-4o-mini
# (optional) EMBEDDING_MODEL=text-embedding-3-small

# 4) (Optional) Re-scrape fresh pages
python -m src.scrape_govuk --urls   https://www.gov.uk/register-for-vat   https://www.gov.uk/how-vat-works/vat-thresholds   --out data/raw

# 5) Chunk the text (100–300 words)
python -m src.chunker --raw_dir data/raw --out data/processed/chunks.jsonl

# 6) Build the local Chroma index
# (if re-running, clear old index to avoid duplicates)
rm -rf chroma   # windows: rd /s /q chroma
python -m src.build_index --chunks data/processed/chunks.jsonl --persist_dir ./chroma

# 7) Ask questions (top-3 retrieval + citations)
python -m src.ask --persist_dir ./chroma --query "When must I register for VAT?"
```

**Example queries**
```bash
python -m src.ask --persist_dir ./chroma --query "I exceeded the VAT threshold last month—what's my effective registration date?"
python -m src.ask --persist_dir ./chroma --query "Under what turnover can I cancel VAT registration?"
```

---

## Configuration

### `.env`
```ini
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini                 # or gpt-4o
EMBEDDING_MODEL=text-embedding-3-small  # or text-embedding-3-large
```

### Retrieval settings (at runtime)
- Default top-k = **3**. Change per call:
  ```bash
  python -m src.ask --persist_dir ./chroma --query "..." --k 5
  ```
- (Optional) MMR for more diverse chunks (edit `ask.py`):
  ```python
  retriever = vs.as_retriever(
      search_type="mmr",
      search_kwargs={"k": args.k, "fetch_k": 20, "lambda_mult": 0.5}
  )
  ```

---

## Key implementation notes

### `scrape_govuk.py`
- Parses HTML with BeautifulSoup, keeps `<main>`/`<article>`, removes `nav/aside/footer/script/style`.
- Converts `<li>` to bullet lines so lists survive in plain text.
- Uses `get_text("\n\n", strip=True)` to introduce **blank lines** between blocks (the chunker splits on these).

### `chunker.py`
- Splits on blank lines via regex and merges to ~100–300-word chunks.
- Adds metadata:
  - `title`, `source_url`, `tags`, `date_scraped`, `chunk_index`
- `chunk_index` starts at 1 per source page (useful for citations and debugging).

### `build_index.py`
- **Imports** from `langchain_chroma import Chroma` (new package).
- Creates a persistent local index with `persist_directory=...`.
- Embeds with `OpenAIEmbeddings` and `add_texts(texts, metadatas)`.

### `ask.py`
- Builds a **Context** block from the **top-k** retrieved chunks:
  ```
  [1] <chunk text...>
  (meta: title=..., url=..., chunk=3)
  ```
- Prompts an LLM with the **question + context** and prints a concise answer plus **Sources** (deduped URLs/titles).

---

## Troubleshooting

- **Deprecation warnings** about Chroma  
  Use `langchain-chroma` (already in the code). If you see older warnings, upgrade:
  ```bash
  pip install -U langchain-chroma chromadb langchain langchain-openai
  ```

- **Old index / duplicates**  
  Delete `./chroma` and re-run `build_index`.

- **No API key detected**  
  Ensure `.env` is in the project root and populated. Our scripts call `load_dotenv()`.

- **“Module not found” in your IDE**  
  Use **module name** (e.g., `src.ask`) in run configs and set **working directory** to the project root.

- **Answer seems outdated (e.g., thresholds)**  
  Re-scrape the target GOV.UK pages and rebuild the index to ensure the latest content is in context.

---

## Development

- **Adjust chunk sizes**:
  ```bash
  python -m src.chunker --raw_dir data/raw --out data/processed/chunks.jsonl     --min_words 120 --max_words 280
  ```
- **Add more sources**: pass more URLs to the scraper, then re-chunk/re-index.
- **Show chunk numbers in citations**: tweak `ask.py` to append `– chunk {chunk_index}`.

---

## Roadmap (nice-to-haves)
- FastAPI endpoint for `ask` → returns `{ answer, sources }` JSON
- Manifest of exact `source_url` per file (or embed URL as the first line of each `.txt`)
- RAG evaluation harness (small Q/A set and accuracy metrics)
- Hybrid retrieval (keyword + vector) and light reranking

---

## Security & data notes
- Only public GOV.UK content is ingested.
- API keys live in `.env` (never commit them).
- Chroma data is local to `./chroma` unless you change the path.

---

## License
MIT (or your preferred license). Update this section if needed.

---

## Credits
Built with **LangChain**, **Chroma**, **OpenAI**, **BeautifulSoup**, and **Requests**.
