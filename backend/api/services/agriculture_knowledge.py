import re


STOP_WORDS = {
    "about", "after", "all", "also", "and", "are", "because", "can", "could",
    "do", "does", "for", "from", "farmer", "farmers", "have", "how", "i", "into",
    "is", "it", "may", "me", "might", "my", "of", "on", "or", "should", "the",
    "this", "that", "there", "they", "to", "turn", "use", "using", "was", "what",
    "when", "where", "which", "why", "with", "would", "you", "your",
}


def normalize_word(word):
    word = word.lower()
    if word == "leaves":
        return "leaf"
    if len(word) > 5 and word.endswith("ing"):
        word = word[:-3]
        if len(word) > 2 and word[-1] == word[-2]:
            word = word[:-1]
        return word
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def retrieve_knowledge(question, context, limit=4):
    terms = {
        normalize_word(word)
        for word in re.findall(r"[A-Za-z]{3,}", question)
        if word.lower() not in STOP_WORDS
    }
    if not terms:
        return "", []

    ranked = []
    minimum_score = 1 if len(terms) == 1 else 2
    for paragraph in re.split(r"\n\s*\n", context):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        words = {normalize_word(word) for word in re.findall(r"[A-Za-z]{3,}", paragraph)}
        score = len(terms & words)
        if score >= minimum_score:
            ranked.append((score, paragraph))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = [paragraph for _, paragraph in ranked[:limit]]

    sources = []
    for paragraph in selected:
        for line in paragraph.splitlines():
            match = re.match(r"\s*(?:source|title)\s*:\s*(.+)", line, re.IGNORECASE)
            if match and match.group(1).strip() not in sources:
                sources.append(match.group(1).strip())
    return "\n\n".join(selected), sources
