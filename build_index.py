# src/build_index.py
import argparse
import os
import json
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma  # <- new package

def load_chunks(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", required=True, help="Path to chunks.jsonl")
    ap.add_argument("--persist_dir", required=True, help="Directory for Chroma storage")
    args = ap.parse_args()

    load_dotenv()
    embed_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embeddings = OpenAIEmbeddings(model=embed_model)

    texts, metadatas = [], []
    for rec in load_chunks(args.chunks):
        texts.append(rec["content"])
        metadatas.append({
            "title": rec["title"],
            "source_url": rec["source_url"],
            "chunk_index": rec["chunk_index"],
            "date_scraped": rec["date_scraped"],
            "tags": ",".join(rec.get("tags", [])),
        })

    vs = Chroma(
        collection_name="govuk_vat",
        embedding_function=embeddings,
        persist_directory=args.persist_dir,  # <- this makes it persistent on disk
    )

    ids = vs.add_texts(texts=texts, metadatas=metadatas)
    print(f"Indexed {len(ids)} chunks into {args.persist_dir}")

if __name__ == "__main__":
    main()