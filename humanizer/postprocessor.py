# postprocessor.py — cleanup pass that runs after the LLM rewrite
# targets perplexity + burstiness metrics used by turnitin and similar detectors

import re
import random
import string


# ========================================================================
# 1. AI TELLTALE PHRASE DICTIONARY (expanded — 120+ entries)
# ========================================================================

AI_TELLTALE_PHRASES = {
    # --- overused hedging / filler that screams AI ---
    "it is important to note that": [
        "notably,", "worth mentioning:", "one thing to keep in mind —",
        "something to consider:", "here's the thing:",
    ],
    "it's important to note that": [
        "notably,", "keep in mind,", "worth pointing out,",
        "the key point here is", "one thing stands out:",
    ],
    "it is worth noting that": [
        "interestingly,", "it's useful to know that", "one detail that stands out is",
    ],
    "it's worth noting that": [
        "interestingly enough,", "one thing that jumps out:", "a helpful detail here:",
    ],
    "it should be noted that": [
        "notably,", "keep in mind that", "a relevant point:",
    ],
    "it is essential to": [
        "you really need to", "it matters to", "the key is to",
    ],
    "it is crucial to": [
        "you've got to", "it's vital to", "the important thing is to",
    ],
    "plays a crucial role": [
        "matters a lot", "is really important", "is a big part of",
    ],
    "plays a vital role": [
        "is an important factor", "has a huge impact", "is central to",
    ],
    "plays a significant role": [
        "is a big deal", "matters quite a bit", "weighs heavily",
    ],
    "it goes without saying": ["obviously,", "clearly,", "of course,",],

    # --- AI transition words / connectors ---
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
    "nonetheless": [
        "still,", "even so,", "regardless,", "all the same,",
    ],
    "subsequently": ["then,", "after that,", "next,", "later,",],
    "henceforth": ["from now on,", "going forward,", "after this,",],
    "thereby": ["which means", "so", "and that way",],
    "thus": ["so", "because of that,", "which means",],
    "hence": ["so", "that's why", "for that reason,",],
    "notwithstanding": ["despite that,", "even with that,", "regardless,",],
    "in light of": ["considering", "given", "because of",],
    "in the context of": ["when it comes to", "with regard to", "talking about",],
    "with regard to": ["about", "when it comes to", "on the topic of",],
    "with respect to": ["about", "regarding", "when it comes to",],
    "pertaining to": ["about", "related to", "on",],
    "on the other hand": ["then again,", "but,", "at the same time,",],
    "as a matter of fact": ["actually,", "in fact,", "really,",],

    # --- AI vocabulary (overly formal / robotic words) ---
    "utilize": ["use",],
    "utilizes": ["uses",],
    "utilizing": ["using",],
    "utilization": ["use",],
    "facilitate": ["help", "enable", "support",],
    "facilitates": ["helps", "enables", "supports",],
    "facilitating": ["helping", "enabling", "supporting",],
    "commenced": ["started", "began", "kicked off",],
    "commence": ["start", "begin", "kick off",],
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
    "in today's society": ["nowadays,", "these days,", "in the current climate,",],
    "in contemporary society": ["these days,", "nowadays,", "currently,",],

    # --- more AI giveaways that turnitin flags ---
    "it can be argued that": ["you could say", "one way to look at it:", "arguably,",],
    "one could argue that": ["you might say", "there's a case for", "arguably,",],
    "it is evident that": ["clearly,", "you can see that", "it's obvious —",],
    "it is apparent that": ["it's clear that", "obviously,", "you can tell",],
    "particularly noteworthy": ["especially interesting", "what sticks out", "worth a mention",],
    "of paramount importance": ["really important", "absolutely key", "critical",],
    "significant impact": ["big effect", "real influence", "major difference",],
    "profound impact": ["huge effect", "deep influence", "massive difference",],
    "serves as a": ["works as a", "acts like a", "functions as a",],
    "aimed at": ["meant to", "designed to", "intended for",],
    "shed light on": ["clarify", "explain", "clear up",],
    "sheds light on": ["clarifies", "explains", "clears up",],
    "a deeper understanding": ["a better grasp", "more insight", "a clearer picture",],
    "gain a deeper understanding": ["get a better sense", "understand more about", "grasp",],
    "foster": ["encourage", "support", "build", "promote",],
    "fostering": ["encouraging", "supporting", "building", "promoting",],
    "nuanced": ["subtle", "detailed", "layered", "complex",],
    "intricate": ["complex", "detailed", "involved",],
    "intricacies": ["details", "complexities", "ins and outs",],
    "meticulous": ["careful", "detailed", "thorough", "precise",],
    "burgeoning": ["growing", "expanding", "rising",],
    "aligns with": ["matches", "fits with", "goes hand in hand with",],
    "resonates with": ["connects with", "hits home for", "speaks to",],
    "underscores": ["highlights", "shows", "points to",],
    "underscore": ["highlight", "show", "point to",],
    "juxtaposition": ["contrast", "comparison", "side-by-side look",],
    "dichotomy": ["split", "divide", "contrast",],
    "myriad of challenges": ["a bunch of problems", "plenty of hurdles", "lots of obstacles",],
    "indispensable": ["essential", "needed", "necessary",],
    "exponentially": ["dramatically", "quickly", "massively",],
    "in a nutshell": ["basically,", "in short,", "put simply,",],
}


# ========================================================================
# 2. CONTRACTION MAP — AI underuses contractions, humans love them
# ========================================================================

CONTRACTION_MAP = {
    "it is": "it's",
    "he is": "he's",
    "she is": "she's",
    "that is": "that's",
    "there is": "there's",
    "what is": "what's",
    "who is": "who's",
    "here is": "here's",
    "how is": "how's",
    "where is": "where's",
    "it has": "it's",
    "he has": "he's",
    "she has": "she's",
    "that has": "that's",
    "who has": "who's",
    "i am": "I'm",
    "you are": "you're",
    "we are": "we're",
    "they are": "they're",
    "i have": "I've",
    "you have": "you've",
    "we have": "we've",
    "they have": "they've",
    "i will": "I'll",
    "you will": "you'll",
    "he will": "he'll",
    "she will": "she'll",
    "we will": "we'll",
    "they will": "they'll",
    "it will": "it'll",
    "that will": "that'll",
    "would have": "would've",
    "could have": "could've",
    "should have": "should've",
    "would not": "wouldn't",
    "could not": "couldn't",
    "should not": "shouldn't",
    "do not": "don't",
    "does not": "doesn't",
    "did not": "didn't",
    "is not": "isn't",
    "are not": "aren't",
    "was not": "wasn't",
    "were not": "weren't",
    "has not": "hasn't",
    "have not": "haven't",
    "had not": "hadn't",
    "will not": "won't",
    "can not": "can't",
    "cannot": "can't",
    "must not": "mustn't",
    "need not": "needn't",
    "let us": "let's",
}


# ========================================================================
# 3. SENTENCE STARTERS TO DIVERSIFY — breaks AI's repetitive openers
# ========================================================================

HUMAN_STARTERS = {
    "agreement": [
        "Sure enough, ", "No surprise, ", "As expected, ", "True to form, ",
        "Predictably, ", "Right on cue, ",
    ],
    "contrast": [
        "But here's the thing — ", "Then again, ", "Flip side though, ",
        "That said, ", "On the flip side, ", "And yet, ",
    ],
    "emphasis": [
        "The big takeaway? ", "What really matters here: ", "Here's what counts — ",
        "The real point is ", "At its core, ", "Bottom line, ",
    ],
    "continuation": [
        "Building on that, ", "Going further, ", "Along those lines, ",
        "Tied to that, ", "In a similar vein, ", "Related to this, ",
    ],
    "example": [
        "Take for instance ", "A good example: ", "Case in point — ",
        "You can see this in ", "Consider how ", "Think about ",
    ],
}


# ========================================================================
# 4. PATTERNS AI DETECTORS FLAG — repeated sentence structure openers
# ========================================================================

AI_REPETITIVE_OPENERS = [
    r"^This (?:is|was|has|provides|represents|demonstrates|shows|highlights|illustrates|ensures|allows)",
    r"^It (?:is|was|has|provides|represents|demonstrates|shows|highlights|illustrates|can be)",
    r"^There (?:are|is|were|was|have been|has been)",
    r"^These (?:are|were|have|include|represent|provide|demonstrate|show)",
    r"^The (?:use|implementation|application|concept|idea|importance|significance|impact|role|process) of",
    r"^(?:One|Another) (?:key|important|significant|notable|crucial|major) (?:aspect|factor|element|point|consideration)",
]


# ========================================================================
# FILTER FUNCTIONS
# ========================================================================


def replace_ai_phrases(text: str, intensity: float = 0.7) -> str:
    # swap out flagged phrases for something a person would actually write
    result = text
    for ai_phrase, replacements in AI_TELLTALE_PHRASES.items():
        if random.random() < intensity:
            pattern = re.compile(re.escape(ai_phrase), re.IGNORECASE)
            if pattern.search(result):
                replacement = random.choice(replacements)
                match = pattern.search(result)
                if match:
                    original = match.group()
                    if original[0].isupper():
                        replacement = replacement[0].upper() + replacement[1:]
                    result = pattern.sub(replacement, result, count=1)
    return result


def inject_contractions(text: str, rate: float = 0.75) -> str:
    # humans use contractions constantly — AI almost never does
    # this single filter has a massive impact on turnitin scores
    result = text
    for full_form, contraction in CONTRACTION_MAP.items():
        if random.random() < rate:
            pattern = re.compile(r'\b' + re.escape(full_form) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(result))
            for match in matches:
                # skip if inside quotes — quoted material should stay as-is
                before = result[:match.start()]
                if before.count('"') % 2 == 1:
                    continue
                original = match.group()
                replacement = contraction
                # try to match the original casing
                if original[0].isupper() and not original.isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                elif original.isupper():
                    replacement = replacement.upper()
                result = result[:match.start()] + replacement + result[match.end():]
                break  # only replace first occurrence per pass to keep it natural
    return result


def vary_sentence_lengths(text: str) -> str:
    # AI writes sentences that are all ~15-20 words — dead giveaway
    # humans have wild variation: 3 words, then 25, then 8, then 30.
    # this tries to force that burstiness pattern
    paragraphs = text.split("\n\n")
    result_paragraphs = []

    for para in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', para)
        if len(sentences) < 3:
            result_paragraphs.append(para)
            continue

        lengths = [len(s.split()) for s in sentences]
        avg_len = sum(lengths) / len(lengths) if lengths else 0
        variance = sum((ln - avg_len) ** 2 for ln in lengths) / len(lengths) if lengths else 999

        new_sentences = list(sentences)

        # if variance is too low → everything is same length → AI-like
        if variance < 15:
            ops_done = 0
            i = 0
            while i < len(new_sentences) - 1 and ops_done < 3:
                words_a = new_sentences[i].split()
                words_b = new_sentences[i + 1].split()

                # merge two short sentences to create a long one (boosts burstiness)
                if len(words_a) < 14 and len(words_b) < 14 and random.random() < 0.5:
                    connector = random.choice([
                        " — and ", ", and ", "; ", " — which means ", ", so ",
                        " — ", ", plus ", " and at the same time, ",
                    ])
                    second_start = new_sentences[i + 1][0].lower() + new_sentences[i + 1][1:]
                    merged = new_sentences[i].rstrip('.!?,;') + connector + second_start
                    new_sentences[i] = merged
                    new_sentences.pop(i + 1)
                    ops_done += 1
                    continue

                # split a long sentence to create a short punchy one
                if len(words_a) > 18 and random.random() < 0.5:
                    split_point = random.randint(
                        max(5, len(words_a) // 3),
                        min(len(words_a) - 4, 2 * len(words_a) // 3)
                    )
                    part1 = " ".join(words_a[:split_point]).rstrip(',;:') + "."
                    part2 = " ".join(words_a[split_point:])
                    if part2 and part2[0].islower():
                        part2 = part2[0].upper() + part2[1:]
                    new_sentences[i] = part1
                    new_sentences.insert(i + 1, part2)
                    ops_done += 1
                    i += 2
                    continue

                i += 1

        # occasionally insert a very short sentence for punch (2-5 words)
        if len(new_sentences) > 5 and random.random() < 0.3:
            short_inserts = [
                "That matters.", "This is key.", "Think about it.",
                "It adds up.", "Simple as that.", "Makes sense.",
                "Big difference.", "Worth noting.", "Fair point.",
                "And it shows.", "No small thing.", "Hard to ignore.",
            ]
            insert_pos = random.randint(2, len(new_sentences) - 1)
            new_sentences.insert(insert_pos, random.choice(short_inserts))

        result_paragraphs.append(" ".join(new_sentences))

    return "\n\n".join(result_paragraphs)


def diversify_openers(text: str) -> str:
    # if too many sentences start with the same word / pattern → flag
    paragraphs = text.split("\n\n")
    result_paragraphs = []

    for para in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', para)
        if len(sentences) < 3:
            result_paragraphs.append(para)
            continue

        # count first words
        first_words = [s.split()[0].lower() if s.split() else "" for s in sentences]
        word_counts = {}
        for w in first_words:
            word_counts[w] = word_counts.get(w, 0) + 1

        # find which sentences start with an overused word
        new_sentences = list(sentences)
        for i, sent in enumerate(new_sentences):
            fw = sent.split()[0].lower() if sent.split() else ""
            if word_counts.get(fw, 0) >= 3 and random.random() < 0.6:
                # check if it matches a flagged AI opener pattern
                for pattern in AI_REPETITIVE_OPENERS:
                    if re.match(pattern, sent, re.IGNORECASE):
                        # pick a random category and prepend a human-sounding opener
                        cat = random.choice(list(HUMAN_STARTERS.keys()))
                        starter = random.choice(HUMAN_STARTERS[cat])
                        lower_sent = sent[0].lower() + sent[1:]
                        new_sentences[i] = starter + lower_sent
                        word_counts[fw] -= 1
                        break

        result_paragraphs.append(" ".join(new_sentences))

    return "\n\n".join(result_paragraphs)


def shuffle_clause_order(text: str) -> str:
    # AI always puts clauses in the same order; humans flip them around
    # "Because X happened, Y resulted" → "Y resulted because X happened"
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = []
    for sent in sentences:
        if random.random() < 0.25:
            # try to flip "Because/Since/Although X, Y" → "Y because/since/although X"
            m = re.match(
                r'^(Because|Since|Although|While|When|If|Given that|Considering that)\s+(.+?),\s+(.+)$',
                sent,
                re.IGNORECASE,
            )
            if m:
                conjunction = m.group(1).lower()
                clause_a = m.group(2).strip().rstrip('.,')
                clause_b = m.group(3).strip()
                # capitalize B, lowercase the conjunction
                if clause_b and clause_b[0].islower():
                    clause_b = clause_b[0].upper() + clause_b[1:]
                flipped = f"{clause_b.rstrip('.')} {conjunction} {clause_a}."
                result.append(flipped)
                continue

        result.append(sent)
    return " ".join(result)


def vary_paragraph_lengths(text: str) -> str:
    # AI loves making every paragraph 3-4 sentences. humans don't.
    paragraphs = text.split("\n\n")
    if len(paragraphs) < 3:
        return text

    result = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        sentences = re.split(r'(?<=[.!?])\s+', para)

        # occasionally merge a short paragraph into the previous one
        if i > 0 and len(sentences) <= 2 and len(result) > 0 and random.random() < 0.35:
            result[-1] = result[-1] + " " + para
            i += 1
            continue

        # occasionally split a long paragraph in two
        if len(sentences) > 5 and random.random() < 0.4:
            split_at = random.randint(2, len(sentences) - 2)
            para1 = " ".join(sentences[:split_at])
            para2 = " ".join(sentences[split_at:])
            result.append(para1)
            result.append(para2)
            i += 1
            continue

        result.append(para)
        i += 1

    return "\n\n".join(result)


def reduce_transition_density(text: str) -> str:
    # AI puts a transition word at the start of almost every sentence
    # humans skip transitions and just... start the next thought
    heavy_transitions = [
        r'^Furthermore,?\s+',
        r'^Moreover,?\s+',
        r'^Additionally,?\s+',
        r'^Consequently,?\s+',
        r'^Subsequently,?\s+',
        r'^Nevertheless,?\s+',
        r'^Nonetheless,?\s+',
        r'^In addition,?\s+',
        r'^As a result,?\s+',
    ]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    transition_count = 0
    stripped_count = 0

    for i, sent in enumerate(sentences):
        for pat in heavy_transitions:
            if re.match(pat, sent, re.IGNORECASE):
                transition_count += 1
                break

    # if more than 30% of sentences start with transitions → strip some
    if len(sentences) > 0 and transition_count / len(sentences) > 0.25:
        new_sentences = []
        for sent in sentences:
            stripped = False
            if stripped_count < transition_count // 2:
                for pat in heavy_transitions:
                    m = re.match(pat, sent, re.IGNORECASE)
                    if m and random.random() < 0.6:
                        remainder = sent[m.end():]
                        if remainder:
                            remainder = remainder[0].upper() + remainder[1:]
                        new_sentences.append(remainder)
                        stripped = True
                        stripped_count += 1
                        break
            if not stripped:
                new_sentences.append(sent)
        return " ".join(new_sentences)

    return text


def add_natural_imperfections(text: str, intensity: float = 0.3) -> str:
    # sprinkle in occasional dashes, parenthetical asides, and human quirks
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) < 3:
        return text

    result_sentences = []
    for i, sentence in enumerate(sentences):
        # em-dash aside insertion
        if random.random() < intensity * 0.12 and len(sentence.split()) > 8:
            words = sentence.split()
            if len(words) > 6:
                insert_pos = random.randint(3, len(words) - 3)
                if "—" not in sentence and "-" not in sentence:
                    words[insert_pos] = "— " + words[insert_pos]
                    end_pos = min(insert_pos + random.randint(2, 3), len(words) - 1)
                    words[end_pos] = words[end_pos] + " —"
                    sentence = " ".join(words)

        # parenthetical aside (humans do this all the time)
        if random.random() < intensity * 0.08 and len(sentence.split()) > 10:
            asides = [
                "(or something close to it)",
                "(at least in theory)",
                "(which is interesting)",
                "(no surprise there)",
                "(and this matters)",
                "(more or less)",
                "(to put it mildly)",
                "(to be fair)",
                "(arguably)",
                "(in a sense)",
            ]
            words = sentence.split()
            pos = random.randint(4, len(words) - 2)
            words.insert(pos, random.choice(asides))
            sentence = " ".join(words)

        result_sentences.append(sentence)

    return " ".join(result_sentences)


def remove_preamble(text: str) -> str:
    # strip "Here's the rewritten..." type junk from the top
    preamble_patterns = [
        r"^(?:Here(?:'s| is) (?:the |a |my )?(?:rewritten|revised|updated|humanized) (?:version|text|content)[\s:.\-—]*\n*)",
        r"^(?:Sure[,!]?\s*(?:here(?:'s| is))?[\s:.\-—]*\n*)",
        r"^(?:Of course[,!]?\s*(?:here(?:'s| is))?[\s:.\-—]*\n*)",
        r"^(?:Certainly[,!]?\s*(?:here(?:'s| is))?[\s:.\-—]*\n*)",
        r"^(?:Absolutely[,!]?\s*(?:here(?:'s| is))?[\s:.\-—]*\n*)",
        r"^(?:Below is[\s:.\-—]*\n*)",
        r"^(?:The following is[\s:.\-—]*\n*)",
        r"^(?:I've (?:rewritten|revised|updated|reworked)[\s\S]*?:\s*\n*)",
        r"^(?:Here you go[\s:.\-—]*\n*)",
        r"^(?:I (?:rewrote|revised|updated|reworked)[\s\S]*?:\s*\n*)",
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
        r"\n*(?:Would you like[\s\S]*?)$",
        r"\n*(?:If you (?:need|want|have)[\s\S]*?)$",
        r"\n*(?:\*This (?:text|response|content) (?:has been|was)[\s\S]*?)$",
    ]
    for pattern in trailing_patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()

    return result


def perplexity_boost(text: str) -> str:
    # turnitin looks for low perplexity (= predictable word sequences)
    # this injects controlled unpredictability by varying word order
    # and adding occasional unexpected but grammatically valid phrases

    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) < 2:
        return text

    result = []
    for sent in sentences:
        # sometimes rearrange a "X and Y" structure to "Y — along with X"
        if random.random() < 0.15:
            m = re.match(r'^(.+?)\s+and\s+(.+?)(\.\s*)$', sent)
            if m and len(m.group(1).split()) > 3 and len(m.group(2).split()) > 3:
                part_b = m.group(2).strip().rstrip('.')
                part_a = m.group(1).strip()
                if part_b and part_b[0].islower():
                    part_b = part_b[0].upper() + part_b[1:]
                if part_a and part_a[0].isupper():
                    part_a = part_a[0].lower() + part_a[1:]
                sent = f"{part_b} — along with {part_a}."
                result.append(sent)
                continue

        # sometimes replace "X is Y" with "Y — that's X" (inverted structure)
        if random.random() < 0.08:
            m = re.match(r'^(.{10,40})\s+is\s+(.{10,60})(\.\s*)$', sent)
            if m:
                subject = m.group(1).strip()
                predicate = m.group(2).strip().rstrip('.')
                if predicate[0].islower():
                    predicate = predicate[0].upper() + predicate[1:]
                sent = f"{predicate} — that's what {subject.lower()} comes down to."
                result.append(sent)
                continue

        result.append(sent)

    return " ".join(result)


def normalize_whitespace(text: str) -> str:
    # final cleanup pass
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' ([.,;:!?])', r'\1', text)  # fix space before punctuation
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)  # fix missing space after period
    text = re.sub(r'——+', '—', text)  # fix double em-dashes
    text = re.sub(r'— —', '—', text)  # fix spaced double dashes
    return text.strip()


# ========================================================================
# MAIN PIPELINE — order matters here, each step builds on the last
# ========================================================================

def postprocess(text: str, tone: str = "normal", intensity: float = 0.7) -> str:
    # step 1: strip LLM junk (preamble, trailing notes)
    result = remove_preamble(text)

    # step 2: replace known AI-flagged phrases with human alternatives
    result = replace_ai_phrases(result, intensity=intensity)

    # step 3: inject contractions (huge impact — turnitin heavily weights this)
    contraction_rate = 0.85 if tone == "casual" else (0.5 if tone == "academic" else 0.7)
    result = inject_contractions(result, rate=contraction_rate)

    # step 4: strip excess transition words that AI overuses
    result = reduce_transition_density(result)

    # step 5: diversify sentence openers so they don't all start the same
    result = diversify_openers(result)

    # step 6: vary sentence lengths to boost the burstiness score
    result = vary_sentence_lengths(result)

    # step 7: shuffle some clause orders for structural unpredictability
    result = shuffle_clause_order(result)

    # step 8: vary paragraph sizes — AI makes them all the same length
    result = vary_paragraph_lengths(result)

    # step 9: boost perplexity with controlled structural variations
    result = perplexity_boost(result)

    # step 10: add human-like imperfections (dashes, asides, parentheticals)
    if tone == "casual":
        result = add_natural_imperfections(result, intensity=intensity * 0.5)
    elif tone == "normal":
        result = add_natural_imperfections(result, intensity=intensity * 0.25)
    elif tone == "academic":
        result = add_natural_imperfections(result, intensity=intensity * 0.1)

    # final cleanup
    result = normalize_whitespace(result)

    return result
