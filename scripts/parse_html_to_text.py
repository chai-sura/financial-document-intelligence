import os
from bs4 import BeautifulSoup
import re
import html
import unicodedata


# ----------- CONFIGURATION -----------
RAW_DIR = 'data/raw/10k_filings'               # Input folder with downloaded .htm/.html files
TEXT_DIR = 'data/processed/10k_text'           # Output folder for plain text files       # Output folder for extracted tables


def ensure_output_dirs():
    """Create processed text directories for each company."""
    os.makedirs(TEXT_DIR, exist_ok=True)
    for company in os.listdir(RAW_DIR):
        company_dir = os.path.join(TEXT_DIR, company)
        os.makedirs(company_dir, exist_ok=True)


def extract_text_from_html(html_content):
    """Extracts clean, readable paragraphs from an HTML 10-K filing while preserving section headers."""
    from bs4 import BeautifulSoup
    import re

    soup = BeautifulSoup(html_content, 'html.parser')

    # Remove unwanted tags
    for tag in soup(['script', 'style', 'footer', 'head', 'nav', 'noscript', 'form', 'table']):
        tag.decompose()

    # Replace <br> with newlines
    for br in soup.find_all('br'):
        br.replace_with('\n')

    # Insert spacing around headings
    for tag in soup.find_all(['h1', 'h2', 'h3', 'b', 'strong']):
        text = tag.get_text(strip=True)
        if text and len(text.split()) < 20:  # likely a heading
            tag.insert_before(f'\n\n## {text.strip()} ##\n\n')

            #tag.insert_before('\n\n' + text + '\n\n')

    # Get full text
    text = soup.get_text(separator='\n')

    # Normalize and clean text
    text = html.unescape(text)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')
    text = text.replace('®', '').replace('™', '')

    lines = text.split('\n')
    cleaned_lines = []
    buffer = []

    for line in lines:
        line = line.strip()

        # Skip junk lines: empty, pure numbers/dates/symbols, single characters
        if not line or re.fullmatch(r'[\d\s\-\.,:/]+', line) or len(line) <= 2:
            continue

        # Skip XBRL tags and financial instrument labels
        if re.match(r'^(us-gaap:|ifrs:|aapl:|dei:|srt:)', line.lower()):
            continue

        # Skip ISO 8601 durations like P1Y, P6M, etc.
        if re.fullmatch(r'P\d+[YMWD]', line.strip()):
            continue

        # Skip repeated form footers or branding
        if 'form 10-k' in line.lower() and 'apple inc' in line.lower():
            continue

        # Remove machine metadata like country/currency tags, units, XBRL taxonomy
        if re.match(r'^(country:|iso4217:|xbrli:|dei:|us-gaap:|ifrs:|srt:)', line.lower()):
            continue

        # Remove boolean terms
        if line.lower() in ['true', 'false']:
            continue

        # Merge consecutive lines into a paragraph unless it's a header
        if re.match(r'^Item\s+\d+[A-Z]?[\.\s]', line, re.IGNORECASE) or (line.isupper() and len(line.split()) < 10) or  (line.endswith(':') and len(line.split()) < 10):
            # Flush current paragraph buffer
            if buffer:
                cleaned_lines.append(' '.join(buffer))
                buffer = []
            cleaned_lines.append(line)
        else:
            #buffer.append(line)
            # If previous line exists and current is likely continuation (e.g., a date)
            if buffer and len(line.split()) < 6 and re.match(r'^[A-Z][a-z]+\s\d{1,2},\s\d{4}', line):
                buffer[-1] += ' ' + line
            else:
                buffer.append(line)

    # Add last paragraph
    if buffer:
        cleaned_lines.append(' '.join(buffer))

    # Combine and clean excessive line breaks
    cleaned_text = '\n\n'.join(cleaned_lines)
    #cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

    return cleaned_text



def convert_html_to_text():
    """Convert all .html/.htm files into .txt files with cleaned text."""
    for company in os.listdir(RAW_DIR):
        raw_path = os.path.join(RAW_DIR, company)

        if not os.path.isdir(raw_path):
            continue

        processed_path = os.path.join(TEXT_DIR, company)
        os.makedirs(processed_path, exist_ok=True)

        for filename in os.listdir(raw_path):
            if filename.endswith(('.html', '.htm')):
                file_path = os.path.join(raw_path, filename)
                base_name = re.sub(r'[^A-Za-z0-9_\-]', '_', os.path.splitext(filename)[0])
                out_file = os.path.join(processed_path, base_name + '.txt')

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        html_content = f.read()
                    plain_text = extract_text_from_html(html_content)

                    with open(out_file, 'w', encoding='utf-8') as out:
                        out.write(plain_text)

                    print(f" Converted {filename} -> {base_name}.txt")

                except Exception as e:
                    print(f" Error processing {file_path}: {e}")

if __name__ == '__main__':
    ensure_output_dirs()
    convert_html_to_text()