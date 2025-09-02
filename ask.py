# src/ask.py
import argparse
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma  # <- moved from langchain_community.vectorstores
from langchain_core.prompts import ChatPromptTemplate

PROMPT_TMPL = '''You are a precise UK VAT assistant. Answer the user question ONLY using the context.
If something is unknown or not in the context, say you do not know and suggest checking the GOV.UK source.

Question:
{question}

Context (top {k} chunks):
{context}

Instructions:
- Cite your sources at the end under "Sources:" as markdown bullet points with [title](url).
- Keep the answer brief and factual.
'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persist_dir", required=True)
    ap.add_argument("--query", required=True)
    ap.add_argument("--k", type=int, default=3)
    args = ap.parse_args()

    load_dotenv()
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    embed_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    embeddings = OpenAIEmbeddings(model=embed_model)
    vs = Chroma(
        collection_name="govuk_vat",
        embedding_function=embeddings,
        persist_directory=args.persist_dir,
    )
    retriever = vs.as_retriever(search_kwargs={"k": args.k})

    # Updated API: use invoke() instead of get_relevant_documents()
    docs = retriever.invoke(args.query)

    # Build context for the prompt
    context = "\n\n".join(
        f"[{i+1}] {d.page_content}\n"
        f"(meta: title={d.metadata.get('title')}, "
        f"url={d.metadata.get('source_url')}, "
        f"chunk={d.metadata.get('chunk_index')})"
        for i, d in enumerate(docs)
    )

    # Build unique source list (avoid duplicates)
    sources, seen = [], set()
    for d in docs:
        title = d.metadata.get("title", "GOV.UK")
        url = d.metadata.get("source_url", "")
        key = (title, url)
        if key in seen:
            continue
        seen.add(key)
        chunk_idx = d.metadata.get("chunk_index")
        suffix = f" – chunk {chunk_idx}" if chunk_idx else ""
        sources.append(f"- [{title}{suffix}]({url})")

    prompt = ChatPromptTemplate.from_template(PROMPT_TMPL).format_messages(
        question=args.query,
        context=context,
        k=len(docs),
    )
    llm = ChatOpenAI(model=llm_model, temperature=0)
    resp = llm.invoke(prompt)
    text = resp.content.strip()

    if "Sources:" not in text:
        text += "\n\nSources:\n" + "\n".join(sources)

    print(text)

#App → (query embed) → Chroma → (top-k chunks) → App → (build prompt) → LLM → (grounded answer + citations)
#
Chunks are embedded & stored

Each chunk’s text → embedding vector (using your EMBEDDING_MODEL, e.g. text-embedding-3-small).

Chroma stores: {vector, page_content, metadata} for every chunk.

Query is embedded

The user’s question → another vector using the same embedding model.

Similarity search

Chroma computes similarity (cosine distance by default) between the query vector and all stored vectors.

It ranks chunks by similarity and returns the top K; your code sets k = 3.

You pass those 3 chunks to the LLM

They’re concatenated into Context and fed to the prompt; you also show their citations from metadata.
if __name__ == "__main__":
    main()