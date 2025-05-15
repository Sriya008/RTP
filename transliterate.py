from indicnlp.transliterate.unicode_transliterate import UnicodeIndicTransliterator
from aksharamukha import transliterate

def transliterate_text(text, target_lang="Tamil"):
    """Uses IndicTrans & Aksharamukha for accurate transliteration."""
    # First transliterate with IndicTrans
    indic_translated = UnicodeIndicTransliterator.transliterate(text, "hi", target_lang)
    # Then refine with Aksharamukha
    final_translit = transliterate.process("Devanagari", target_lang, indic_translated)
    return final_translit

# Example usage
# text = "भारत एक महान देश है।"
# print(transliterate_text(text, "Tamil"))
