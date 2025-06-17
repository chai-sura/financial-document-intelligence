import os
import re
import shutil
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings

RAW_DIR = 'data/raw/10k_filings'
TEXT_DIR = 'data/processed/10k_text'

def ensure_output_dirs():
    if os.path.exists(TEXT_DIR):
        shutil.rmtree(TEXT_DIR)
    os.makedirs(TEXT_DIR, exist_ok=True)
    for company in os.listdir(RAW_DIR):
        os.makedirs(os.path.join(TEXT_DIR, company), exist_ok=True)

def clean_line(line):
    return line.replace('\xa0', ' ').strip()

def is_junk(line):
    # Remove XBRL, page numbers, one-word lines, numbers, etc.
    if not line or line.lower() in ('true', 'false', 'none', 'document'):
        return True
    if re.fullmatch(r'[a-zA-Z0-9\-_]+:[\w\-_]+', line):  # us-gaap etc.
        return True
    if re.fullmatch(r'[PFYQ]\d*', line):
        return True
    if re.fullmatch(r'\d{6,}', line):
        return True
    if re.fullmatch(r'[0-9\.\-]+', line):
        return True
    if re.fullmatch(r'page\s*\d+', line, re.IGNORECASE):
        return True
    if re.fullmatch(r'\d+\s*$', line):  # single numbers (likely page/line)
        return True
    return False

def table_to_text(table):
    rows = table.find_all('tr')
    lines = []
    for row in rows:
        cols = [clean_line(td.get_text(separator=' ', strip=True)) for td in row.find_all(['td', 'th'])]
        # Remove columns that are just numbers (often page numbers)
        cols = [col for col in cols if not re.fullmatch(r'\d+', col)]
        if any(c for c in cols if c.strip()):
            lines.append("   ".join(cols))
    return '\n'.join(lines)

def extract_text_from_html(html_content):
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
    soup = BeautifulSoup(html_content, 'lxml')
    for tag in soup(['script', 'style', 'footer', 'head', 'nav', 'noscript', 'form']):
        tag.decompose()

    blocks = []
    last_line = None

    # Collect block-level text with spacing
    for elem in soup.body.descendants:
        if elem.name == 'table':
            md = table_to_text(elem)
            if md and md != last_line:
                blocks.append(md)
                last_line = md
        elif elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            text = elem.get_text(separator=' ', strip=True)
            if text and text != last_line:
                blocks.append('\n' + text.upper() + '\n')
                last_line = text
        elif elem.name == 'p':
            text = elem.get_text(separator=' ', strip=True)
            if text and text != last_line:
                blocks.append('\n' + text + '\n')
                last_line = text
        elif elem.name == 'li':
            text = elem.get_text(separator=' ', strip=True)
            if text and text != last_line:
                blocks.append('- ' + text)
                last_line = text
        elif elem.name == 'br':
            continue
        elif elem.string and elem.string.strip():
            text = clean_line(elem.string)
            if text and text != last_line:
                blocks.append(text)
                last_line = text

    # Remove any preamble before the SEC heading
    doc_start_idx = None
    for idx, block in enumerate(blocks):
        if 'SECURITIES AND EXCHANGE COMMISSION' in block.upper():
            doc_start_idx = max(0, idx-1)
            break
    if doc_start_idx is not None:
        blocks = blocks[doc_start_idx:]

    # Remove page numbers, duplicates, and junk lines
    cleaned = []
    seen = set()
    for block in blocks:
        for line in block.splitlines():
            l = clean_line(line)
            if is_junk(l) or not l or l in seen:
                continue
            cleaned.append(l)
            seen.add(l)

    # Merge lines into paragraphs and add spacing between headers/tables/sections
    output = []
    para = ""
    for block in cleaned:
        if (block.isupper() and len(block.split()) < 10) or re.match(r'^(ITEM\s+\d+[A-Z]?\.|PART\s+[IVXLC]+)', block, re.IGNORECASE):
            if para:
                output.append(para.strip())
                para = ""
            output.append('\n' + block.strip() + '\n')
        elif '   ' in block or '\t' in block:  # Table-like block
            if para:
                output.append(para.strip())
                para = ""
            output.append(block.strip())
        else:
            if para:
                if not para.rstrip().endswith(('.', ':', ';', '?', '!', '"', '”')):
                    para += " " + block
                else:
                    output.append(para.strip())
                    para = block
            else:
                para = block
    if para:
        output.append(para.strip())

    # Collapse multiple blank lines and clean up
    text = '\n\n'.join([b for b in output if b.strip()])
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

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
                out_file = os.path.join(
                    processed_path,
                    re.sub(r'[^A-Za-z0-9_\-]', '_', os.path.splitext(filename)[0]) + '.txt'
                )
                try:
                    with open(in_file, 'r', encoding='utf-8', errors='ignore') as f:
                        html_content = f.read()
                    plain_text = extract_text_from_html(html_content)
                    with open(out_file, 'w', encoding='utf-8') as out:
                        out.write(plain_text)
                    print(f"✅ {filename} -> {out_file}")
                except Exception as e:
                    print(f"❌ Error processing {in_file}: {e}")

if __name__ == '__main__':
    ensure_output_dirs()
    convert_html_to_text()
