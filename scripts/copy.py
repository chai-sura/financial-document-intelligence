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

def html_to_markdown_lines(html_content):
    # Configure html2text to preserve heading markers
    text_maker = html2text.HTML2Text()
    text_maker.body_width = 0
    text_maker.ignore_links = True
    text_maker.ignore_images = True
    text_maker.single_line_break = True
    text_maker.ignore_emphasis = False
    markdown_text = text_maker.handle(html_content)
    # Remove any html2text '***' lines (markdown horizontal rules)
    markdown_text = re.sub(r'^\*{3,}$', '', markdown_text, flags=re.MULTILINE)
    return markdown_text.splitlines()

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


def align_tables_and_format(lines):
    output = []
    table_block = []
    for line in lines + [""]:  # Add a sentinel for the last block
        # Detect lines with at least two pipes as a table row
        if line.count('|') >= 2:
            table_block.append(line)
        else:
            # If there was a table block collected, process it
            if table_block:
                # Split each row into cells
                table_rows = [
                    [cell.strip() for cell in row.split('|')]
                    for row in table_block
                ]
                # Pad all rows to the same number of columns
                max_cols = max(len(row) for row in table_rows)
                for row in table_rows:
                    row += [''] * (max_cols - len(row))
                # Find max width for each column
                col_widths = [max(len(row[i]) for row in table_rows) for i in range(max_cols)]
                # Output: blank line before table
                output.append('')
                # Format each row with left-aligned columns
                for row in table_rows:
                    output.append('  '.join(row[i].ljust(col_widths[i]) for i in range(max_cols)))
                # Output: blank line after table
                output.append('')
                table_block = []
            # For non-table lines, just append as is
            if line.strip() != '' or (output and output[-1] != ''):
                output.append(line.strip())
    # Remove excess blank lines at end
    while output and output[-1] == '':
        output.pop()
    return output

def process_lines_for_toc(lines):
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


def add_blank_lines(lines):
    """
    Add a blank line after every heading, and between every paragraph.
    """
    output = []
    heading_re = re.compile(r"^(#{1,6}\s|PART\s+[IVXLC]+|ITEM\s*\d+[A-Z]?\.?)", re.IGNORECASE)
    prev_was_heading = False
    prev_blank = True
    for i, line in enumerate(lines):
        stripped = line.strip()
        is_heading = bool(heading_re.match(stripped))
        # Add blank line before heading if not already blank
        if is_heading and output and not output[-1] == "":
            output.append("")
        output.append(stripped)
        # Add blank line after heading or after a paragraph, unless next is already blank
        if is_heading or (stripped and (i+1)<len(lines) and lines[i+1].strip()):
            output.append("")
    # Remove accidental trailing blanks
    while output and output[-1] == "":
        output.pop()
    return output

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
                    lines = html_to_markdown_lines(html_content)
                    lines = process_lines_for_toc(lines)
                    lines = clean_xbrl_junk_lines(lines)
                    lines = align_tables_and_format(lines)
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
