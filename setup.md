# mac/linux
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt


python -m src.scrape_govuk --urls https://www.gov.uk/register-for-vat https://www.gov.uk/how-vat-works/vat-thresholds --out data/raw
python -m src.chunker --raw_dir data/raw --out data/processed/chunks.jsonl
rm -rf chroma                  # Windows: rd /s /q chroma
python -m src.build_index --chunks data/processed/chunks.jsonl --persist_dir ./chroma
python -m src.ask --persist_dir ./chroma --query "When must I register for VAT?"



python -m src.ask --persist_dir ./chroma --query "When must I register for VAT?"
python -m src.ask --persist_dir ./chroma --query "I exceeded the VAT threshold last month—what's my effective registration date?"
python -m src.ask --persist_dir ./chroma --query "Under what turnover can I cancel VAT registration?"



