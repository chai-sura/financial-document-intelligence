import os
import shutil
import html2text
import re

def ensure_output_dirs(raw_dir, text_dir):
    if os.path.exists(text_dir):
        shutil.rmtree(text_dir)
    os.makedirs(text_dir, exist_ok=True)
    for company in os.listdir(raw_dir):
        os.makedirs(os.path.join(text_dir, company), exist_ok=True)


def process_lines_for_toc(lines):
    """
    Remove TOC page numbers, pipes, and keep just "Item X. Heading" lines.
    """
    output = []
    in_toc = False
    toc_line = re.compile(r'^(Item\s*\d+[A-Z]?\.?)\s*\|\s*([^|]+?)\s*\|\s*\d+\s*$', re.IGNORECASE)
    heading_line = re.compile(r'^(Item\s*\d+[A-Z]?\.?)(?:\s*\|\s*([^\|]+))?$', re.IGNORECASE)
    table_of_contents = re.compile(r'^\s*TABLE OF CONTENTS', re.IGNORECASE)
    page_only = re.compile(r'^\s*Page\s*$', re.IGNORECASE)
    for line in lines:
        line_strip = line.strip()
        if table_of_contents.match(line_strip):
            in_toc = True
            continue
        if page_only.match(line_strip):
            continue
        if in_toc:
            if not line_strip:
                in_toc = False
                continue
            m = toc_line.match(line_strip)
            if m:
                output.append(f"{m.group(1)} {m.group(2).strip()}")
                continue
            m = heading_line.match(line_strip)
            if m and m.group(2):
                output.append(f"{m.group(1)} {m.group(2).strip()}")
                continue
            elif m:
                output.append(m.group(1))
            continue
        output.append(line)
    return output

def process_lines_remove_tables_and_pipes(lines):
    """
    Flatten simple tables and clean up extra pipes, while marking start/end of table with blank lines.
    """
    output = []
    in_table = False
    for i, line in enumerate(lines):
        line_strip = line.strip()
        if not line_strip or all(c in {'|', '-'} for c in line_strip):
            continue
        # Remove markdown images
        if line_strip.startswith('![') or re.search(r"\.(jpg|jpeg|png|gif)(\)|$)", line_strip, re.IGNORECASE):
            continue
        if '|' in line_strip:
            # Table start: add blank line if not already in_table
            if not in_table:
                output.append("")
                in_table = True
            # Clean and add line
            parts = [part.strip() for part in line_strip.split('|') if part.strip()]
            cleaned = ' | '.join(parts)
            if cleaned:
                output.append(cleaned)
        else:
            if in_table:
                # End of table: add blank line
                output.append("")
                in_table = False
            output.append(line_strip)
    # Ensure table end adds a blank line
    if in_table:
        output.append("")
    return output

def add_blank_lines(lines):
    output = []
    paragraph = []
    heading_re = re.compile(r"^(PART\s+[IVXLC]+|ITEM\s*\d+[A-Z]?\.?)(\s|$)", re.IGNORECASE)

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Paragraph break
            if paragraph:
                output.append(' '.join(paragraph))
                paragraph = []
            # Add a blank line if the last line wasn't already blank
            if not output or output[-1] != "":
                output.append("")
        elif heading_re.match(stripped) or (stripped.isupper() and len(stripped) < 80):
            # Heading
            if paragraph:
                output.append(' '.join(paragraph))
                paragraph = []
            if output and output[-1] != "":
                output.append("")
            output.append(stripped)
            output.append("")  # Always a blank after heading
        else:
            paragraph.append(stripped)
    # Handle trailing paragraph
    if paragraph:
        output.append(' '.join(paragraph))
    # Remove leading/trailing blank lines
    while output and output[0] == "":
        output.pop(0)
    while output and output[-1] == "":
        output.pop()
    return output



def clean_xbrl_junk_lines(lines):
    output_lines = []
    start_copying = False
    footer_re = re.compile(
        r"^[\w\s\.\-&]+?\|\s*\d{4}\s*Form\s*10-K\s*\|\s*\d+$", re.IGNORECASE
    )
    image_re = re.compile(r"!\[.*\]\(.*\.(jpg|jpeg|png|gif)\)", re.IGNORECASE)
    for line in lines:
        line_strip = line.strip()
        if line_strip and all(c in {'|', '-'} for c in line_strip):
            continue
        if footer_re.match(line_strip):
            continue
        if image_re.search(line_strip):
            continue
        if not start_copying and (
            "SECURITIES AND EXCHANGE COMMISSION" in line_strip.upper() or
            "FORM 10-K" in line_strip.upper()
        ):
            start_copying = True
        if start_copying:
            output_lines.append(line)
    if not output_lines:
        output_lines = lines
    return output_lines

def convert_html_to_text_with_html2text(raw_dir, text_dir):
    ensure_output_dirs(raw_dir, text_dir)
    for company in os.listdir(raw_dir):
        raw_path = os.path.join(raw_dir, company)
        if not os.path.isdir(raw_path):
            continue
        processed_path = os.path.join(text_dir, company)
        os.makedirs(processed_path, exist_ok=True)
        for filename in os.listdir(raw_path):
            if filename.endswith(('.html', '.htm')):
                in_file = os.path.join(raw_path, filename)
                out_file = os.path.join(processed_path, os.path.splitext(filename)[0] + '.txt')
                try:
                    with open(in_file, 'r', encoding='utf-8', errors='ignore') as f:
                        html_content = f.read()
                    text = html2text.html2text(html_content)
                    lines = text.splitlines()
                    lines = process_lines_for_toc(lines)
                    lines = process_lines_remove_tables_and_pipes(lines)
                    lines = clean_xbrl_junk_lines(lines)   # <---- USE FUNCTION, NOT FILE!
                    lines = add_blank_lines(lines)
                    clean_text = '\n'.join(lines)
                    with open(out_file, 'w', encoding='utf-8') as out:
                        out.write(clean_text)
                    print(f"{filename} -> {out_file}")
                except Exception as e:
                    print(f"Error processing {in_file}: {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Convert 10-K HTML to plain text using html2text.")
    parser.add_argument('--raw_dir', type=str, help='Directory with company folders of HTML files')
    parser.add_argument('--text_dir', type=str, help='Directory to save processed text')
    args = parser.parse_args()

    if args.raw_dir and args.text_dir:
        convert_html_to_text_with_html2text(args.raw_dir, args.text_dir)
    else:
        print("Provide --raw_dir and --text_dir.")
