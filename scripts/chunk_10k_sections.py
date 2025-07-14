import os
import re
import json
import argparse

def chunk_txt_file(input_path):
    """
    Splits a 10-K text file into sections (by PART/ITEM headers) and returns a list of dicts.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    section_re = re.compile(r'^(PART\s+[IVXLC]+|ITEM\s+\d+[A-Z]?\.?.*)$', re.IGNORECASE)
    chunks = []
    current_chunk = {
        "header": None,
        "content": ""
    }

    for line in lines:
        line = line.strip()
        if section_re.match(line):
            # Save previous chunk if it has content
            if current_chunk["header"] and current_chunk["content"].strip():
                chunks.append(current_chunk)
            # Start new chunk
            current_chunk = {
                "header": line,
                "content": ""
            }
        else:
            # Append content to current chunk
            if line:
                if current_chunk["content"]:
                    current_chunk["content"] += "\n"
                current_chunk["content"] += line

    # Save last chunk
    if current_chunk["header"] and current_chunk["content"].strip():
        chunks.append(current_chunk)
    return chunks

def chunk_txt_dir(txt_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for company in os.listdir(txt_dir):
        company_dir = os.path.join(txt_dir, company)
        if not os.path.isdir(company_dir):
            continue
        for filename in os.listdir(company_dir):
            if filename.endswith('.txt'):
                input_path = os.path.join(company_dir, filename)
                chunks = chunk_txt_file(input_path)
                output_company_dir = os.path.join(output_dir, company)
                os.makedirs(output_company_dir, exist_ok=True)
                out_json = os.path.join(output_company_dir, filename.replace('.txt', '_chunks.json'))
                with open(out_json, 'w', encoding='utf-8') as out:
                    json.dump(chunks, out, indent=2)
                print(f"Chunked {input_path} -> {out_json}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk 10-K text files by PART/ITEM section headers.")
    parser.add_argument('--txt_dir', type=str, required=True, help="Input directory (processed/10k_text)")
    parser.add_argument('--output_dir', type=str, required=True, help="Output directory for chunked JSON files")
    args = parser.parse_args()

    chunk_txt_dir(args.txt_dir, args.output_dir)
