"""Target word list. Each word has the phonemes a typically developing speaker is
expected to produce, so recordings can be compared against them.

Word choice covers sounds that are commonly affected in SSD: affricates, fricatives,
retroflex stops (Hindi), dental stops (Hindi), clusters and /r/, /l/, /θ/ (English).
The phoneme lists are a starting point and should be reviewed by a speech-language
pathologist before clinical use.
"""

WORDS = [
    # Hindi
    {"id": "hi_machhli", "lang": "hi", "text": "मछली", "roman": "machhli", "gloss": "fish",
     "ipa": ["m", "ə", "tʃ", "l", "i"], "target": "affricate /tʃʰ/, /l/"},
    {"id": "hi_kamal", "lang": "hi", "text": "कमल", "roman": "kamal", "gloss": "lotus",
     "ipa": ["k", "ə", "m", "ə", "l"], "target": "velar /k/"},
    {"id": "hi_seb", "lang": "hi", "text": "सेब", "roman": "seb", "gloss": "apple",
     "ipa": ["s", "e", "b"], "target": "fricative /s/"},
    {"id": "hi_paani", "lang": "hi", "text": "पानी", "roman": "paani", "gloss": "water",
     "ipa": ["p", "a", "n", "i"], "target": "bilabial /p/, nasal /n/"},
    {"id": "hi_gaay", "lang": "hi", "text": "गाय", "roman": "gaay", "gloss": "cow",
     "ipa": ["g", "a", "j"], "target": "velar /g/"},
    {"id": "hi_taala", "lang": "hi", "text": "ताला", "roman": "taala", "gloss": "lock",
     "ipa": ["t", "a", "l", "a"], "target": "dental /t̪/"},
    {"id": "hi_laddoo", "lang": "hi", "text": "लड्डू", "roman": "laddoo", "gloss": "sweet ball",
     "ipa": ["l", "ə", "ɖ", "u"], "target": "retroflex /ɖ/"},
    {"id": "hi_jhaadu", "lang": "hi", "text": "झाड़ू", "roman": "jhaadu", "gloss": "broom",
     "ipa": ["dʒ", "a", "ɽ", "u"], "target": "affricate /dʒ/, flap /ɽ/"},
    {"id": "hi_sher", "lang": "hi", "text": "शेर", "roman": "sher", "gloss": "lion",
     "ipa": ["ʃ", "e", "r"], "target": "fricative /ʃ/, /r/"},
    # English
    {"id": "en_fish", "lang": "en", "text": "fish", "roman": "fish", "gloss": "",
     "ipa": ["f", "ɪ", "ʃ"], "target": "/f/, /ʃ/"},
    {"id": "en_ship", "lang": "en", "text": "ship", "roman": "ship", "gloss": "",
     "ipa": ["ʃ", "ɪ", "p"], "target": "/ʃ/"},
    {"id": "en_rabbit", "lang": "en", "text": "rabbit", "roman": "rabbit", "gloss": "",
     "ipa": ["r", "æ", "b", "ɪ", "t"], "target": "/r/"},
    {"id": "en_thumb", "lang": "en", "text": "thumb", "roman": "thumb", "gloss": "",
     "ipa": ["θ", "ʌ", "m"], "target": "/θ/"},
    {"id": "en_spoon", "lang": "en", "text": "spoon", "roman": "spoon", "gloss": "",
     "ipa": ["s", "p", "u", "n"], "target": "cluster /sp/"},
    {"id": "en_zebra", "lang": "en", "text": "zebra", "roman": "zebra", "gloss": "",
     "ipa": ["z", "i", "b", "r", "ə"], "target": "/z/, cluster /br/"},
    {"id": "en_cheese", "lang": "en", "text": "cheese", "roman": "cheese", "gloss": "",
     "ipa": ["tʃ", "i", "z"], "target": "affricate /tʃ/"},
    {"id": "en_yellow", "lang": "en", "text": "yellow", "roman": "yellow", "gloss": "",
     "ipa": ["j", "ɛ", "l", "oʊ"], "target": "/j/, /l/"},
]

_BY_ID = {w["id"]: w for w in WORDS}


def get_word(word_id):
    return _BY_ID.get(word_id)


def words_for(language):
    """'mixed' interleaves Hindi and English, mirroring how bilingual children speak."""
    if language in ("hi", "en"):
        return [w for w in WORDS if w["lang"] == language]
    hi = [w for w in WORDS if w["lang"] == "hi"]
    en = [w for w in WORDS if w["lang"] == "en"]
    out = []
    for i in range(max(len(hi), len(en))):
        if i < len(hi):
            out.append(hi[i])
        if i < len(en):
            out.append(en[i])
    return out
