from pathlib import Path
import re
import json
import html
import random

RAW_DIR = Path("documents/raw")
CLEANED_DIR = Path("documents/cleaned")
CHUNKS_DIR = Path("documents/chunks")

CHUNK_SIZE = 3500  # characters, roughly 700-900 tokens
OVERLAP = 500      # characters, roughly 100-150 tokens


def load_documents(raw_dir: Path):
    """
    Load all .txt files from data/raw.
    Returns a list of document dictionaries.
    """
    documents = []

    for file_path in raw_dir.glob("*.txt"):
        text = file_path.read_text(encoding="utf-8")

        documents.append({
            "source_file": file_path.name,
            "text": text
        })

    return documents


def clean_text(text: str) -> str:
    """
    Clean raw document text.
    Removes HTML artifacts, extra whitespace, and common boilerplate.
    """

    # Convert HTML entities like &amp; and &nbsp;
    text = html.unescape(text)

    # Remove HTML tags if any got copied
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove common web boilerplate phrases
    boilerplate_patterns = [
        r"Share this.*",
        r"Read more.*",
        r"Log in.*",
        r"Sign up.*",
        r"Cookie.*",
        r"Accept cookies.*",
        r"Advertisement.*",
    ]

    for pattern in boilerplate_patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    # Normalize whitespace
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def split_into_paragraphs(text: str):
    """
    Split text into paragraphs.
    """
    paragraphs = text.split("\n\n")
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP):
    """
    Recursive-ish chunking:
    1. Prefer paragraph boundaries.
    2. Build chunks up to chunk_size.
    3. Add overlap from the end of the previous chunk.
    """

    paragraphs = split_into_paragraphs(text)

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        # If a single paragraph is too long, split it by sentences.
        if len(paragraph) > chunk_size:
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                    current_chunk += " " + sentence
                else:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())

                    overlap_text = current_chunk[-overlap:] if overlap > 0 else ""
                    current_chunk = overlap_text + " " + sentence
            continue

        # Normal paragraph-based chunking
        if len(current_chunk) + len(paragraph) + 2 <= chunk_size:
            current_chunk += "\n\n" + paragraph
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            overlap_text = current_chunk[-overlap:] if overlap > 0 else ""
            current_chunk = overlap_text + "\n\n" + paragraph

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Remove empty or tiny chunks
    chunks = [chunk.strip() for chunk in chunks if len(chunk.strip()) > 50]

    return chunks


def save_cleaned_documents(documents):
    """
    Save cleaned text files to data/cleaned.
    """
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)

    cleaned_documents = []

    for doc in documents:
        cleaned = clean_text(doc["text"])

        output_path = CLEANED_DIR / doc["source_file"]
        output_path.write_text(cleaned, encoding="utf-8")

        cleaned_documents.append({
            "source_file": doc["source_file"],
            "text": cleaned
        })

    return cleaned_documents


def create_chunks(cleaned_documents):
    """
    Chunk all cleaned documents and attach metadata.
    """
    all_chunks = []

    for doc in cleaned_documents:
        chunks = chunk_text(doc["text"])

        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "chunk_id": f"{doc['source_file']}_chunk_{i}",
                "source_file": doc["source_file"],
                "chunk_index": i,
                "text": chunk
            })

    return all_chunks


def save_chunks(chunks):
    """
    Save chunks as JSONL.
    Each line is one chunk.
    """
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = CHUNKS_DIR / "chunks.jsonl"

    with output_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    return output_path


def inspect_chunks(chunks, n=5):
    """
    Print representative chunks for manual inspection.
    """
    print("\n==============================")
    print(f"Total chunks created: {len(chunks)}")
    print("==============================\n")

    for chunk in chunks[:n]:
        print("---------- CHUNK ----------")
        print(f"ID: {chunk['chunk_id']}")
        print(f"Source: {chunk['source_file']}")
        print(f"Length: {len(chunk['text'])} characters")
        print()
        print(chunk["text"][:1200])
        print()


def main():
    print("Loading raw documents...")
    raw_documents = load_documents(RAW_DIR)
    print(f"Loaded {len(raw_documents)} documents.")

    print("Cleaning documents...")
    cleaned_documents = save_cleaned_documents(raw_documents)
    print(f"Saved cleaned documents to {CLEANED_DIR}")

    print("Chunking documents...")
    chunks = create_chunks(cleaned_documents)

    print("Saving chunks...")
    output_path = save_chunks(chunks)
    print(f"Saved chunks to {output_path}")

    #inspect_chunks(chunks, n=5)
    random_chunks = random.sample(chunks, min(5, len(chunks)))
    inspect_chunks(random_chunks, n=5)


if __name__ == "__main__":
    main()