# src/chunker.py
import argparse, os, json, re, datetime

def read_all_txt(raw_dir):
    for name in sorted(os.listdir(raw_dir)):
        if name.endswith(".txt"):
            with open(os.path.join(raw_dir, name), "r", encoding="utf-8") as f:
                yield name, f.read()

def chunk_text(text, min_words=100, max_words=300):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf, wc = [], [], 0
    for p in paragraphs:
        words = p.split()
        if wc + len(words) <= max_words:
            buf.append(p); wc += len(words)
        else:
            if wc >= min_words or buf:
                chunks.append(" ".join(buf)); buf, wc = [p], len(words)
            else:
                buf.append(p); wc += len(words)
                chunks.append(" ".join(buf)); buf, wc = [], 0
    if buf: chunks.append(" ".join(buf))
    fixed = []
    for c in chunks:
        w = c.split()
        if len(w) > max_words:
            for i in range(0, len(w), max_words):
                fixed.append(" ".join(w[i:i+max_words]))
        else:
            fixed.append(c)
    return fixed

def infer_title(name):
    if "register-for-vat" in name: return "When to register for VAT"
    if "how-vat-works_vat-thresholds" in name: return "VAT thresholds"
    return name.replace("_"," ").replace(".txt","").title()

def infer_url(name):
    if "register-for-vat" in name: return "https://www.gov.uk/register-for-vat"
    if "how-vat-works_vat-thresholds" in name: return "https://www.gov.uk/how-vat-works/vat-thresholds"
    return "https://www.gov.uk/" + name.replace(".txt","").replace("_","/")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw_dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min_words", type=int, default=100)
    ap.add_argument("--max_words", type=int, default=300)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    today = datetime.date.today().isoformat()
    with open(args.out, "w", encoding="utf-8") as out:
        for name, text in read_all_txt(args.raw_dir):
            title, url = infer_title(name), infer_url(name)
            tags = ["vat","govuk","hmrc"]
            for i, chunk in enumerate(chunk_text(text, args.min_words, args.max_words), 1):
                rec = {
                    "id": f"{title.lower().replace(' ','-')}-{i}",
                    "title": title,
                    "source_url": url,
                    "tags": tags,
                    "date_scraped": today,
                    "chunk_index": i,
                    "content": chunk.strip()
                }
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote chunks to {args.out}")

if __name__ == "__main__":
    main()
