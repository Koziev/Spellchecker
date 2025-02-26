import typing
import re

from emoji import EMOJI_CHARACTER


def tokenize_slowly(text: str):
    special_tokens = list(enumerate(set(re.findall(
        r'(а-ля|тет-а-тет|ва-банк|рок-н-рол\w*|Нью-Йорк\w*|Улан-Удэ|давным-давно|кое у кого|кое о чем|кое о чём|кое о ком|кое на что|кое на кого|кое с чем|кое с кем|кое в кого|кое во что|кое к чему|кое к кому|кое-чем|кое-что|кое-как|кое-куда|кое-где|кое-кто|рок-н-ролл|т\.\s?д\.|т\.\s?к\.|т\.\s?п\.|т\.\s?е\.|н\.\s?э\.|н\.\s?п\.|н\.п\.|по-\w{4,}|кое во что|как-то|где-то|когда-то|зачем-то|почему-то|откуда-то|точь-в-точь)',
        text, flags=re.I))))

    encoding = [(t, f'token{i}') for i, t in special_tokens]
    decoding = dict((encoded, t) for t, encoded in encoding)

    for t, encoding in encoding:
        if t[-1] == '.':
            text = re.sub(r'\b' + re.escape(t), encoding, text)
        else:
            text = re.sub(r'\b' + re.escape(t) + r'(\b|$)', encoding, text)

    # Теперь режем на токены по границам слов.
    tokens = []
    i = 0
    while i < len(text):
        m = re.search(r'([\s\n.,!?\- ;:()\t\n–—⸺«»″”“„"…+]|' + EMOJI_CHARACTER + ')', text[i:])
        if m is None:
            # до конца строки
            token = text[i:]
            tokens.append(token)
            break
        else:
            token = text[i: i+m.span()[0]]
            tokens.append(token)

            delimiter = m.group(0)
            if re.match(r'^\s$', delimiter) is None:
                tokens.append(delimiter)

            i = i + m.span()[1]

    for t in tokens:
        if re.match('^(\w+/){1,}\w+$', t):
            # финансовую/военную  ==> разрезаем на 2 токена: финансовую военную
            for t2 in t.replace('/', ' / ').split(' '):
                if t2:
                    yield decoding.get(t2, t2)
        elif re.match(r'(\w+|){1,}\w+', t):
            # дедушка|человеки
            for t2 in t.replace('|', ' | ').split(' '):
                if t2:
                    yield decoding.get(t2, t2)
        elif re.match(r"'(\w+)'", t):
            yield t[0]
            yield t[1:-1]
            yield t[-1]
        elif t:
            yield decoding.get(t, t)


if __name__ == '__main__':
    tx = list(tokenize_slowly("'''Де́мон''' - название нечистой силы"))
    print(tx)

    # Прогулка по музею-заповеднику В. Д. Поленова.

    tx = list(tokenize_slowly("Бесоёбит)"))
    assert (tx == ["Бесоёбит", ")"])

    tx = list(tokenize_slowly("А-ля клавир"))
    assert (tx == ["А-ля", "клавир"])

    tx = list(tokenize_slowly("по-кавказски"))
    assert (tx == ["по-кавказски"])

    tx = list(tokenize_slowly("поставил жизнь ва-банк"))
    assert (tx == ["поставил", "жизнь", "ва-банк"])

    # 'гадости' шепчет
    tx = list(tokenize_slowly("'гадости' шепчет"))
    assert (tx == ["'", "гадости", "'", "шепчет"])

    tx = list(tokenize_slowly('дедушка|человеки'))
    assert (tx == ['дедушка', '|', 'человеки'])

    tx = list(tokenize_slowly('финансовую/военную'))
    assert (tx == ['финансовую', '/', 'военную'])

    tx = list(tokenize_slowly('до н.э.!'))
    assert '|'.join(tx) == 'до|н.э.|!'

    tx = list(tokenize_slowly('Японию🤣'))
    assert '|'.join(tx) == 'Японию|🤣'

    tx = list(tokenize_slowly('Давай-ка, спроси кое о чём меня-то'))
    assert '|'.join(tx) == 'Давай|-|ка|,|спроси|кое о чём|меня|-|то'

    tx = list(tokenize_slowly('и т.д. и т.п.?'))
    assert '|'.join(tx) == 'и|т.д.|и|т.п.|?'

    tx = list(tokenize_slowly('кошка ловит мышей.'))
    assert '|'.join(tx) == 'кошка|ловит|мышей|.'

    tx = list(tokenize_slowly('т.д.'))
    assert( tx == ['т.д.'])

    tx = list(tokenize_slowly('т.к.'))
    assert( tx == ['т.к.'])

    tx = list(tokenize_slowly('кое-что'))
    assert( tx == ['кое-что'])

    tx = list(tokenize_slowly('т.п.'))
    assert( tx == ['т.п.'])

    tx = list(tokenize_slowly('кое-как'))
    assert( tx == ['кое-как'])

    tx = list(tokenize_slowly('Все как-то просто и по-детски'))
    assert (tx == ['Все', 'как-то', 'просто', 'и', 'по-детски'])

    tx = list(tokenize_slowly('Тет-а-тет я с луной.'))
    assert (tx == ['Тет-а-тет', 'я', 'с', 'луной', '.'])

    tx = list(tokenize_slowly('Про жизнь в Нью-Йорке'))
    assert (tx == ['Про', 'жизнь', 'в', 'Нью-Йорке'])

