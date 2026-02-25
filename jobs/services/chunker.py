def chunk_text(text: str, max_chars: int = 4000) -> list:
    """
    Split a long string into smaller chunks of a maximum number of characters.

    Each chunk is returned as a tuple containing its index and the text segment.
    The chunks are contiguous and preserve the original text order.

    Args:
        text (str): The input string to be split into chunks.
        max_chars (int, optional): Maximum number of characters per chunk. Defaults to 4000.

    Returns:
        list of tuples: A list where each tuple is (index, chunk_text), with
                        `index` starting from 0.
    """
    chunks = []
    start = 0
    index = 0

    while start < len(text):
        end = start + max_chars
        chunks.append((index, text[start:end]))
        start = end
        index += 1

    return chunks
