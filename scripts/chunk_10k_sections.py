import os
import re
import json
import argparse

def is_heading(line):
    if re.match(r'^(PART\s+[IVXLC]+|ITEM\s+\d+[A-Z]?\.?.*)$', line, re.IGNORECASE):
        return True
    if len(line) > 3 and (line.isupper() or re.match(r'^([A-Z][a-z]+(\s+|$))+', line)):
        return True
    return False

def is_table_line(line):
    if '|' in line:
        return True
    if re.search(r'\s{2,}', line) and re.search(r'\d', line):
        return True
    return False


def chunk_txt_file_section_based(input_path, company=None, year=None, min_chunk_words=8):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f.readlines()]

    chunks = []
    chunk_counter = 1

    # Add special first chunk: company + year
    info_text = f"COMPANY: {company}\nYEAR: {year}"
    chunks.append({
        "chunk_id": chunk_counter,
        "text": info_text,
        "section": None,
        "type": "info",
        "company": company,
        "year": year
    })
    chunk_counter += 1

    section_lines = []
    section_heading = None

    for idx, line in enumerate(lines):
        line_strip = line.strip()
        # Start of new section (heading)
        if is_heading(line_strip):
            # If we have collected a section, flush it
            if section_heading and section_lines:
                content = "\n".join(section_lines).strip()
                if len(content.split()) >= min_chunk_words:
                    chunks.append({
                        "chunk_id": chunk_counter,
                        "text": content,
                        "section": section_heading,
                        "type": "section",
                        "company": company,
                        "year": year
                    })
                    chunk_counter += 1
            # Start new section
            section_heading = line_strip
            section_lines = []
        else:
            if section_heading:  # Only collect lines after the first heading
                section_lines.append(line_strip)

    # Flush the last section if any
    if section_heading and section_lines:
        content = "\n".join(section_lines).strip()
        if len(content.split()) >= min_chunk_words:
            chunks.append({
                "chunk_id": chunk_counter,
                "text": content,
                "section": section_heading,
                "type": "section",
                "company": company,
                "year": year
            })

    return chunks


def chunk_txt_file_fine(input_path, company=None, year=None, max_paragraph_len=800, min_chunk_words=8):
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f.readlines()]

    chunks = []
    chunk_counter = 1

    # Add special first chunk: company + year
    info_text = f"COMPANY: {company}\nYEAR: {year}"
    chunks.append({
        "chunk_id": chunk_counter,
        "text": info_text,
        "section": None,
        "subheading": None,
        "type": "info",
        "start": 0,
        "end": len(info_text),
        "company": company,
        "year": year
    })
    chunk_counter += 1

    parent_section = None
    current_subheading = None
    last_heading = None
    buffer = []
    char_cursor = len(info_text) + 1  # Account for info chunk
    current_type = "paragraph"

    def flush_chunk():
        nonlocal buffer, parent_section, current_subheading, last_heading, chunk_counter, char_cursor
        if buffer:
            content = "\n".join(buffer).strip()
            if last_heading:
                content = f"{last_heading}\n{content}"
                last_heading = None
            if content and len(content.split()) >= min_chunk_words:
                start = char_cursor
                end = start + len(content)
                chunks.append({
                    "chunk_id": chunk_counter,
                    "text": content,
                    "section": parent_section,
                    "subheading": current_subheading,
                    "type": current_type,
                    "start": start,
                    "end": end,
                    "company": company,
                    "year": year
                })
                chunk_counter += 1
                char_cursor = end + 1
        buffer.clear()
        

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        line_strip = line.strip()
        if not line_strip:
            if buffer and len("\n".join(buffer)) > max_paragraph_len:
                flush_chunk()
            char_cursor += len(line) + 1
            idx += 1
            continue

        if is_heading(line_strip):
            flush_chunk()
            if re.match(r'^(PART\s+[IVXLC]+|ITEM\s+\d+[A-Z]?\.?.*)$', line_strip, re.IGNORECASE):
                parent_section = line_strip
                current_subheading = None
            else:
                current_subheading = line_strip
            last_heading = line_strip
            idx += 1
            continue

        if is_table_line(line_strip):
            flush_chunk()
            table_buffer = [line_strip]
            current_type = "table"
            next_idx = idx + 1
            while next_idx < len(lines):
                next_line = lines[next_idx].strip()
                if next_line and is_table_line(next_line):
                    table_buffer.append(next_line)
                    next_idx += 1
                else:
                    break
            table_content = "\n".join(table_buffer).strip()
            if len(table_content.split()) >= min_chunk_words:
                start = char_cursor
                end = start + len(table_content)
                chunks.append({
                    "chunk_id": chunk_counter,
                    "text": table_content,
                    "section": parent_section,
                    "subheading": current_subheading,
                    "type": "table",
                    "start": start,
                    "end": end,
                    "company": company,
                    "year": year
                })
                chunk_counter += 1
                char_cursor = end + 1
            idx = next_idx
            buffer.clear()
            current_type = "paragraph"
            continue

        if current_type != "paragraph":
            flush_chunk()
        buffer.append(line_strip)
        current_type = "paragraph"
        if len("\n".join(buffer)) > max_paragraph_len:
            flush_chunk()
        char_cursor += len(line) + 1
        idx += 1

    flush_chunk()
    return chunks

def chunk_txt_dir_fine(txt_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for company in os.listdir(txt_dir):
        company_dir = os.path.join(txt_dir, company)
        if not os.path.isdir(company_dir):
            continue
        for filename in os.listdir(company_dir):
            if filename.endswith('.txt'):
                input_path = os.path.join(company_dir, filename)
                # Extract year from filename (expects a 4-digit year in filename)
                match = re.search(r'(20\d{2})', filename)
                year = match.group(1) if match else None
                chunks = chunk_txt_file_section_based(input_path, company=company, year=year)
                output_company_dir = os.path.join(output_dir, company)
                os.makedirs(output_company_dir, exist_ok=True)
                out_json = os.path.join(output_company_dir, filename.replace('.txt', '_fine_chunks.json'))
                with open(out_json, 'w', encoding='utf-8') as out:
                    json.dump(chunks, out, indent=2)
                print(f"Chunked {input_path} -> {out_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine chunk 10-K text files for RAG.")
    parser.add_argument('--txt_dir', type=str, required=True, help="Input directory (processed/10k_text)")
    parser.add_argument('--output_dir', type=str, required=True, help="Output directory for chunked JSON files")
    args = parser.parse_args()
    chunk_txt_dir_fine(args.txt_dir, args.output_dir)
