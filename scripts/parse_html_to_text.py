import os
import re
import html
import shutil
import unicodedata
from bs4 import BeautifulSoup

RAW_DIR = 'data/raw/10k_filings'
TEXT_DIR = 'data/processed/10k_text'

def ensure_output_dirs():
    if os.path.exists(TEXT_DIR):
        shutil.rmtree(TEXT_DIR)
    os.makedirs(TEXT_DIR, exist_ok=True)

    for company in os.listdir(RAW_DIR):
        os.makedirs(os.path.join(TEXT_DIR, company), exist_ok=True)

def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    for tag in soup(['script', 'style', 'footer', 'head', 'nav', 'noscript', 'form']):
        tag.decompose()

    for br in soup.find_all('br'):
        br.replace_with('\n')
    for tag in soup.find_all(['p', 'div', 'center']):
        tag.insert_before('\n')
        tag.insert_after('\n')

    text = soup.get_text(separator='\n')
    text = html.unescape(text)
    text = unicodedata.normalize('NFKD', text)
    text = text.replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
    text = re.sub(r'(FORM)\s*\n\s*(10-K)', r'\1 10-K', text, flags=re.IGNORECASE)
    text = re.sub(r'^.*Form\s+10-K.*Page\s+\d+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Strip lines with known metadata noise at the top
    unwanted_prefixes = re.compile(r'^(aapl:|country:|xbrli:)', re.IGNORECASE)
    lines = [line for line in lines if not unwanted_prefixes.match(line)]

    # Preserve header block
    start_idx, end_idx = 0, 0
    for i, line in enumerate(lines[:150]):
        if 'UNITED STATES SECURITIES AND EXCHANGE COMMISSION' in line.upper():
            start_idx = i
        if 'TABLE OF CONTENTS' in line.upper():
            end_idx = i + 1
            break
    heading_block = lines[start_idx:end_idx]
    heading_text = '\n'.join(heading_block).strip()
    lines = lines[end_idx:]

    # Merge split item lines
    merged_lines = []
    i = 0
    while i < len(lines):
        current = lines[i]
        if re.match(r'^Item\s+\d+[A-Z]?\.$', current, re.IGNORECASE):
            next_line = lines[i+1] if i + 1 < len(lines) else ''
            if next_line and len(next_line.split()) <= 6:
                merged_lines.append(f"{current} {next_line}")
                i += 2
                continue
        merged_lines.append(current)
        i += 1
    lines = merged_lines

    xbrl_noise = re.compile(r'^(P\d+[YMWD]|FY|Q\d|--?\d{2}-\d{2}|0{5,}|[A-Za-z]+:[A-Za-z0-9]+Member|us-gaap:[\w]+|aapl:[\w]+|iso4217:[A-Z]+|country:[A-Z]+|\d{4}-\d{2}-\d{2}|\d{9,}|^\d+(\.\d+)?$)', re.IGNORECASE)

    buffer = []
    cleaned_lines = []

    for line in lines:
        if not line or line.lower() in ['true', 'false']:
            continue
        if xbrl_noise.fullmatch(line.strip()):
            continue

        item_match = re.match(r'^(Item\s+\d+[A-Z]?\.)\s*(.*)', line, re.IGNORECASE)
        part_match = re.match(r'^PART\s+[IVXLC]+\s*$', line.strip(), re.IGNORECASE)

        if item_match:
            if buffer:
                cleaned_lines.append(' '.join(buffer))
                buffer = []
            heading = f"{item_match.group(1).strip()} {item_match.group(2).strip()}"
            cleaned_lines.append(f"\n\n {heading.upper()} \n\n")
        elif part_match:
            if buffer:
                cleaned_lines.append(' '.join(buffer))
                buffer = []
            cleaned_lines.append(f"\n\n {line.strip()} \n")
        else:
            buffer.append(line)

    if buffer:
        cleaned_lines.append(' '.join(buffer))

    return heading_text + '\n\n' + '\n\n'.join(cleaned_lines)

def convert_html_to_text():
    for company in os.listdir(RAW_DIR):
        raw_path = os.path.join(RAW_DIR, company)
        if not os.path.isdir(raw_path):
            continue

        processed_path = os.path.join(TEXT_DIR, company)
        os.makedirs(processed_path, exist_ok=True)

        for filename in os.listdir(raw_path):
            if filename.endswith(('.html', '.htm')):
                in_file = os.path.join(raw_path, filename)
                out_file = os.path.join(processed_path, re.sub(r'[^A-Za-z0-9_\-]', '_', os.path.splitext(filename)[0]) + '.txt')
                try:
                    with open(in_file, 'r', encoding='utf-8', errors='ignore') as f:
                        html_content = f.read()
                    plain_text = extract_text_from_html(html_content)
                    with open(out_file, 'w', encoding='utf-8') as out:
                        out.write(plain_text)
                    print(f"Converted {filename} -> {out_file}")
                except Exception as e:
                    print(f"Error processing {in_file}: {e}")

def scan_text_files_for_html():
    html_pattern = re.compile(r'<[^>]+>')
    for company in os.listdir(TEXT_DIR):
        company_path = os.path.join(TEXT_DIR, company)
        if not os.path.isdir(company_path):
            continue

        for filename in os.listdir(company_path):
            if not filename.endswith('.txt'):
                continue
            file_path = os.path.join(company_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            html_like = html_pattern.findall(text)
            if html_like:
                print(f"[HTML DETECTED] {filename}: {html_like[:3]}")

if __name__ == '__main__':
    ensure_output_dirs()
    convert_html_to_text()
    scan_text_files_for_html()
