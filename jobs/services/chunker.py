def chunk_text(text: str, max_chars: int = 4000) -> list:
    chunks = []
    start = 0
    index = 0

    while start < len(text):
        end = start + max_chars
        chunks.append((index, text[start:end]))
        start = end
        index += 1

    return chunks
