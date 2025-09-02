# src/scrape_govuk.py

#
#<main>
#<h1>Register for VAT</h1>
#<p>You must register if ...</p>
#<ul><li>Turnover over £90,000</li><li>Expect to exceed in 30 days</li></ul>
#<p>If you register late ...</p>
#</main>

#Register for VAT

#You must register if ...

#• Turnover over £90,000

#• Expect to exceed in 30 days

#If you register late ...


import argparse, os, re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

def extract_main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find("article") or soup
    for tag in main.find_all(["nav","aside","footer","script","style"]):
        tag.decompose()
    for li in main.find_all("li"):
        if not li.text.strip().startswith("•"):
            li.insert(0, "• ")
    text = main.get_text("\n\n", strip=True)
    m = re.search(r"(Register for VAT|How VAT works|VAT thresholds|When to register for VAT)", text, re.I)
    if m:
        text = text[m.start():]
    return text

def fetch_url(url, timeout=30):
    resp = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    for url in args.urls:
        html = fetch_url(url)

        text = extract_main_text(html)

        #https://www.gov.uk/register-for-vat → data/raw/register-for-vat.txt
        #https://www.gov.uk/how-vat-works/vat-thresholds → data/raw/how-vat-works_vat-thresholds.txt

        path = urlparse(url).path.strip("/").replace("/", "_") or "index"
        fname = f"{path}.txt"
        with open(os.path.join(args.out, fname), "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {fname} ({len(text.split())} words)")

if __name__ == "__main__":
    main()
