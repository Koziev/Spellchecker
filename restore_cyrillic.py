"""
Код замены латинцы на омографичную кириллицу в случае, если ближайший контекст содержит
кириллицу.

03.08.2022 Вынес процедуру сюда из кода подготовки бусидо, так как она будет полезна для
подготовки других соскрапленных текстов.

23.10.2023 Добавлена обработка ëáóúόéýќў

10.10.2024 Добавлена обработка замены цифры 3 на букву З
"""

import re


def restore_cyrillic(text):
    for c, c_cyr in zip('coaxpeyëόáéóýúќўόun', 'соахреуёоаеоуикуоип'):
        rs = r'([абвгдеёжзийклмнопрстуфхцчшщъыьэюя ])('+c+')'
        if re.search(rs, text, flags=re.I) is not None:
            text = re.sub(rs, r'\1'+c_cyr, text, flags=re.I)

        rs = r'('+c+')([абвгдеёжзийклмнопрстуфхцчшщъыьэюя ])'
        if re.search(rs, text, flags=re.I) is not None:
            text = re.sub(rs, c_cyr+r'\2', text, flags=re.I)

    for c, c_cyr in zip('3AKHOPCTMB', 'ЗАКНОРСТМВ'):
        rs = r'([абвгдеёжзийклмнопрстуфхцчшщъыьэюя ])('+c+')'
        if re.search(rs, text) is not None:
            text = re.sub(rs, r'\1'+c_cyr, text)

        rs = r'('+c+')([абвгдеёжзийклмнопрстуфхцчшщъыьэюя ])'
        if re.search(rs, text) is not None:
            text = re.sub(rs, c_cyr+r'\2', text)

    return text


if __name__ == '__main__':
    from generative_poetry.alphabet_sanity_checker import is_correct

    s = restore_cyrillic('3емную')
    assert(s == 'Земную')

    s = restore_cyrillic('детu')
    assert(s == 'дети')

    s = restore_cyrillic('поставлены рядом.')
    assert('p' not in s)
    assert('р' in s)
    assert is_correct(s)


    s = restore_cyrillic('Чак Hоррис никогда не спит. Он ждет.')
    assert('H' not in s)
    assert('Н' in s)
    assert is_correct(s)

    s0 = """напрасно с киберассистенткой
в подсобке заперлись вдвоëм
не подошëл мой нестандартный
разъëм"""
    s = restore_cyrillic(s0)
    assert('ë' not in s)
    assert('ё' in s)
    assert is_correct(s)

    print('All done =)')
