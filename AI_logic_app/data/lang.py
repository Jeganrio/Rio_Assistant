
def input_lang(lang):
    lang = lang.lower()
    
    if 'french' in lang:
        lang = 'fr'
        return lang
    elif 'english' in lang:
        lang = 'en'
        return lang
    elif 'hindi' in lang:
        lang = 'hi'
        return lang
    elif 'tamil' in lang:
        lang = 'ta'
        return lang
    elif 'bengali' in lang:
        lang = 'bn'
        return lang
    elif 'telugu' in lang:
        lang = 'te'
        return lang
    elif 'marathi' in lang:
        lang = 'mr'
        return lang
    elif 'gujarati' in lang:
        lang = 'gu'
        return lang
    elif 'urdu' in lang:
        lang = 'ur'
        return lang
    elif 'kannada' in lang:
        lang = 'kn'
        return lang
    elif 'oriya' in lang:
        lang = 'or'
        return lang
    elif 'punjab' in lang:
        lang = 'pa'
        return lang
    else:
        lang = 0
        return lang    
