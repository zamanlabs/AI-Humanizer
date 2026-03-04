# postprocessor.py — cleanup pass that runs after the LLM rewrite

import re
import random


# phrases to swap out for more natural-sounding alternatives
AI_TELLTALE_PHRASES = {
    "it is important to note that": [
        "notably,", "worth mentioning:", "one thing to keep in mind —",
        "something to consider:", "here's the thing:",
    ],
    "it's important to note that": [
        "notably,", "keep in mind,", "worth pointing out,",
        "the key point here is", "one thing stands out:",
    ],
    "in conclusion": [
        "all in all,", "at the end of the day,", "to wrap up,",
        "looking at the bigger picture,", "so, putting it all together,",
    ],
    "in summary": [
        "to sum things up,", "so overall,", "all things considered,",
        "the bottom line is,", "wrapping up,",
    ],
    "furthermore": [
        "on top of that,", "plus,", "adding to this,", "what's more,", "also,",
    ],
    "moreover": [
        "beyond that,", "also,", "and there's more —", "on top of that,",
    ],
    "additionally": [
        "on top of that,", "plus,", "also,", "another thing —",
    ],
    "consequently": [
        "so,", "as a result,", "because of this,", "that's why",
    ],
    "nevertheless": [
        "still,", "even so,", "but then again,", "that said,",
    ],
    "it is worth noting": [
        "interestingly,", "it's useful to know", "one detail that stands out",
    ],
    "utilize": ["use",],
    "utilizes": ["uses",],
    "utilizing": ["using",],
    "utilization": ["use",],
    "facilitate": ["help", "enable", "support",],
    "facilitates": ["helps", "enables", "supports",],
    "commenced": ["started", "began", "kicked off",],
    "commence": ["start", "begin", "kick off",],
    "subsequently": ["then,", "after that,", "next,", "later,",],
    "prior to": ["before",],
    "in order to": ["to",],
    "a myriad of": ["many", "lots of", "a range of",],
    "myriad": ["many", "numerous", "a bunch of",],
    "plethora": ["plenty", "a lot", "loads",],
    "delve": ["dig into", "explore", "look at", "examine",],
    "delves": ["digs into", "explores", "looks at", "examines",],
    "delving": ["digging into", "exploring", "looking at",],
    "leverage": ["use", "take advantage of", "tap into",],
    "leveraging": ["using", "tapping into", "taking advantage of",],
    "leverages": ["uses", "taps into",],
    "comprehensive": ["thorough", "complete", "full", "in-depth",],
    "groundbreaking": ["innovative", "new", "fresh", "pioneering",],
    "cutting-edge": ["modern", "latest", "advanced", "new",],
    "paradigm": ["model", "approach", "framework", "way of thinking",],
    "synergy": ["collaboration", "combined effort", "teamwork",],
    "holistic": ["overall", "complete", "full-picture", "well-rounded",],
    "robust": ["strong", "solid", "reliable", "durable",],
    "streamline": ["simplify", "make easier", "smooth out",],
    "streamlines": ["simplifies", "makes easier", "smooths out",],
    "encompasses": ["includes", "covers", "spans",],
    "encompass": ["include", "cover", "span",],
    "pivotal": ["key", "crucial", "central", "critical",],
    "multifaceted": ["complex", "varied", "many-sided",],
    "realm": ["area", "field", "domain", "world",],
    "tapestry": ["mix", "blend", "collection",],
    "navigate": ["handle", "deal with", "manage", "work through",],
    "navigating": ["handling", "dealing with", "managing",],
    "underpins": ["supports", "backs up", "drives",],
    "underpin": ["support", "back up", "drive",],
    "embark": ["start", "begin", "set out on",],
    "embarking": ["starting", "beginning", "setting out on",],
    "testament": ["proof", "sign", "evidence",],
    "in today's world": ["these days,", "nowadays,", "right now,",],
    "in the modern era": ["today,", "these days,", "currently,",],
    "it goes without saying": ["obviously,", "clearly,", "of course,",],
    "in light of": ["considering", "given", "because of",],
}

# overused openers
AI_OVERUSED_STARTERS = [
    r"^This is ",
    r"^It is ",
    r"^There are ",
    r"^There is ",
]


def replace_ai_phrases(text: str, intensity: float = 0.7) -> str:
    result = text
    for ai_phrase, replacements in AI_TELLTALE_PHRASES.items():
        if random.random() < intensity:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(ai_phrase), re.IGNORECASE)
            if pattern.search(result):
                replacement = random.choice(replacements)
                # Match the case of the first character
                match = pattern.search(result)
                if match:
                    original = match.group()
                    if original[0].isupper():
                        replacement = replacement[0].upper() + replacement[1:]
                    result = pattern.sub(replacement, result, count=1)
    return result


def vary_sentence_lengths(text: str) -> str:
    # merge or split sentences if they're suspiciously same-length
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) < 4:
        return text

    lengths = [len(s.split()) for s in sentences]
    avg_len = sum(lengths) / len(lengths)

    variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)

    if variance < 10 and len(sentences) > 4:
        # too uniform, merge a pair
        idx = random.randint(0, len(sentences) - 2)
        # Only merge if both are short-to-medium
        if lengths[idx] < 15 and lengths[idx + 1] < 15:
            connector = random.choice([" — ", ", and ", "; "])
            merged = sentences[idx].rstrip('.!?') + connector + \
                     sentences[idx + 1][0].lower() + sentences[idx + 1][1:]
            sentences[idx] = merged
            sentences.pop(idx + 1)

    return " ".join(sentences)


def remove_preamble(text: str) -> str:
    # strip "Here's the rewritten..." type junk from the top
    preamble_patterns = [
        r"^(?:Here(?:'s| is) (?:the |a |my )?rewritten (?:version|text)[\s:.\-—]*\n*)",
        r"^(?:Sure[,!]?\s*(?:here(?:'s| is))?[\s:.\-—]*\n*)",
        r"^(?:Of course[,!]?\s*(?:here(?:'s| is))?[\s:.\-—]*\n*)",
        r"^(?:Certainly[,!]?\s*(?:here(?:'s| is))?[\s:.\-—]*\n*)",
        r"^(?:Below is[\s:.\-—]*\n*)",
        r"^(?:The following is[\s:.\-—]*\n*)",
        r"^(?:I've rewritten[\s\S]*?:\s*\n*)",
        r"^(?:Here you go[\s:.\-—]*\n*)",
        r"^---\s*\n",
    ]
    result = text.strip()
    for pattern in preamble_patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()

    # same idea but for the end of the text
    trailing_patterns = [
        r"\n*---\s*$",
        r"\n*(?:I hope this (?:helps|works|meets)[\s\S]*?)$",
        r"\n*(?:Let me know if[\s\S]*?)$",
        r"\n*(?:Feel free to[\s\S]*?)$",
        r"\n*(?:Note: [\s\S]*?)$",
    ]
    for pattern in trailing_patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()

    return result


def add_natural_imperfections(text: str, intensity: float = 0.3) -> str:
    # sprinkle in occasional dashes and asides (very lightly)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) < 3:
        return text

    result_sentences = []
    for i, sentence in enumerate(sentences):
        if random.random() < intensity * 0.15 and len(sentence.split()) > 8:
            words = sentence.split()
            if len(words) > 6:
                insert_pos = random.randint(3, len(words) - 3)
                if "—" not in sentence and "-" not in sentence:
                    words[insert_pos] = "— " + words[insert_pos]
                    end_pos = min(insert_pos + random.randint(2, 3), len(words) - 1)
                    words[end_pos] = words[end_pos] + " —"
                    sentence = " ".join(words)

        result_sentences.append(sentence)

    return " ".join(result_sentences)


def postprocess(text: str, tone: str = "normal", intensity: float = 0.7) -> str:
    result = remove_preamble(text)
    result = replace_ai_phrases(result, intensity=intensity)
    result = vary_sentence_lengths(result)

    if tone == "casual":
        result = add_natural_imperfections(result, intensity=intensity * 0.5)
    elif tone == "normal":
        result = add_natural_imperfections(result, intensity=intensity * 0.2)

    result = re.sub(r' +', ' ', result)
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = result.strip()

    return result
