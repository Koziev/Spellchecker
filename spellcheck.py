import re
import os
import string
import collections
import json
import pickle
import glob
import traceback

from spellchecker import SpellChecker

from restore_cyrillic import restore_cyrillic
from tokenization_utils import tokenize_slowly
from emoji import EMOJI_CHARACTER


def Aa(s):
    return s[0].upper() + s[1:]


class TrieNode:
    def __init__(self):
        self.result_word = None
        self.children = {}

    def insert(self, word, result_word):
        node = self
        for letter in word:
            if letter not in node.children:
                node.children[letter] = TrieNode()

            node = node.children[letter]

        node.result_word = result_word

    def search(self, tail):
        if len(tail) == 0:
            if self.result_word:
                return self.result_word
            else:
                return None
        else:
            if tail[0] in self.children:
                return self.children[tail[0]].search(tail[1:])

            return None


class PoeticSpellchecker(object):
    def __init__(self, parser, allow_norwig_speller=False):
        self.parser = parser
        self.allow_norwig_speller = allow_norwig_speller

    def compile(self, data_dir, output_dir):
        self.known_words = set()
        self.word2upos = collections.defaultdict(set)

        #self.acceptable_edits = set()
        #with open(os.path.join(data_dir, 'speller', 'acceptable_edits.json')) as f:
        #    for edit, freq in json.load(f):
        #        self.acceptable_edits.add(edit)

        #self.repl_rx_1 = []
        #self.repl_rx_1.append((r'\b(откуда|где|куда|почему|как|так|какой|какая|какое|какие|какого|какую|каких|каким|какими) \-?\s?(то)(\b)', '\\1-то'),)

        all_replx = [(r'не до любил(\w*)', 'недолюбил\\1'), (r'однокласн(\w+)', 'одноклассн\\1'),
                     (r'некч(е|ё)мн(\w+)', 'никч\\1мн\\2'),
                     (r'когда то([.!?])', 'когда-то\\1'),
                     (r'какой то([.!?])', 'какой-то\\1'),
                     (r'почему то([.!?])', 'почему-то\\1'),
                     (r'куда то([.!?])', 'куда-то\\1'),
                     (r'не в дом(е|ё)к', 'невдом\\1к'), (r'не вдом(е|ё)к', 'невдом\\1к'),
                     ]

        self.repl_rx = []
        self.repl_rx__1 = []  # замены с префиксом по-
        self.word_replaces = []

        for bad, good in all_replx:
            if re.search('[a-z]', good, flags=re.I):
                print(f'ERROR: латиница в замене {bad} ==> {good}')
                exit(0)

            if re.match(r'^по\-\w+', bad) is not None:
                self.repl_rx__1.append((bad, good))
            elif re.search(r'\W', bad) is None:
                self.word_replaces.append((bad, good))
            elif re.search(r'(\w[ ]?)\-([ ]?\w)', bad):
                bad2 = re.sub(r'(\w)\-(\w)', r'\1\-\2', bad)
                self.repl_rx.append((bad2, good))
            else:
                self.repl_rx.append((bad, good))

        # переделать на левенштейна + таблицу матов
        uncensoring = [('нах*ярился', 'нахуярился'), ('п*зды', 'пизды'), ('х*й', 'хуй'), ('на**й', 'нахуй'), ('с%уя', 'схуя'),
                       ('х*еплеты', 'хуеплеты'), ('нарк*тик', 'наркотик'), ('п*дарасов', 'пидарасов'), ('пи*дюк', 'пиздюк'),
                       ('нах*я', 'нахуя'), ('з**бало', 'заебало'), ('на*бывая', 'наёбывая'), ('на@бал', 'наебал'),
                       ('оху*тельных', 'охуительных'), ('наеб*ниться', 'наебениться'), ('бл*ди', 'бляди'), ('еб*ть', 'ебать'),
                       ('х*рово', 'херово'), ('шл*ха', 'шлюха'), ('пох*й', 'похуй'), ('разъ*бёт', 'разъебёт'), ('су*а', 'сука'),
                       ('п*здец', 'пиздец'), ('х*р', 'хер'), ('бл*', 'бля'), ('с*чка', 'сучка'), ('х*йня', 'хуйня'),
                       ('съ*бался', 'съебался'), ('гер*ин', 'героин'), ('пизд*ки', 'пиздюки'), ('за*бало', 'заебало'),
                       ('спи*дил', 'спиздил'), ('бл@ть', 'блядь'), ('о@уенно', 'охуенно'), ('зае&али', 'заебали'),
                       ('долбо*б', 'долбоёб'), ('долбо*бы', 'долбоёбы'), ('е*ало', 'ебало'), ('ст*рва', 'стерва'),
                       ('з*дница', 'задница'), ('бл*дство', 'блядство'), ('ж**у', 'жопу'), ('за**ись', 'заебись'),
                       ('с*кса', 'секса'), ('х*як', 'хуяк'), ('ох*евших', 'охуевших'), ('пох*изме', 'похуизме'),
                       ('оху*тельно', 'охуительно'), ('ох*ительно', 'охуительно'), ('п*ебать', 'поебать'),
                       ('пи**ишь', 'пиздишь'), ('сос*ть', 'сосать'), ('с*кс', 'секс'), ('пи*дят', 'пиздят'),
                       ('мр**ей', 'мразей'), ('у*баться', 'уебаться'), ('на*бал', 'наебал'), ('еб*ле', 'ебале'),
                       ('пи*дит', 'пиздит'), ('х*еплёты', 'хуеплёты'), ('х*еплёт', 'хуеплёт'), ('х*ровый', 'херовый'),
                       ('х*я', 'хуя'), ('п*здуй', 'пиздуй'), ('зло*бучим', 'злоебучим'), ('по**й', 'похуй'),
                       ('е**ть', 'ебать'), ('е**нутый', 'ебанутый'), ('з**бал', 'заебал'), ('с*ка', 'сука'),
                       ('по*баться', 'поебаться'), ('б*ядства', 'блядства'), ('по*баться', 'поебаться'), ('б*дло', 'быдло'),
                       ('с*ки', 'суки'), ('пиз*ец', 'пиздец'), ('е*ать', 'ебать'), ('пи*дюлей', 'пиздюлей'),
                       ('пиз*ят', 'пиздят'), ('за*бали', 'заебали'), ('пи*ды', 'пизды'), ('е*анутый', 'ебанутый'),
                       ('невмеру', 'не в меру'), ('ху*той', 'хуетой'), ('на*бывали', 'наёбывали'), ('обо@@ать', 'обосрать'),
                       ('еб@нцой', 'ебанцой'), ('по@лядуй', 'поблядуй'), ('бля@cтвом', 'блядcтвом'), ('е@альник', 'ебальник'),
                       ('за@рали', 'засрали'), ('ж@па', 'жопа'), ('от**бись', 'отъебись'), ('ох*еешь', 'охуеешь'),
                       ('нае@али', 'наебали'), ('с@ка', 'сука'), ('пук@ли', 'пукали'), ('не@бабельная', 'неебабельная'),
                       ('е#ли', 'ебли'), ('отпиз#у', 'отпизжу'), ('*уй', 'хуй'), ('бл..и', 'бляди'), ('на##уй', 'нахуй'),
                       ('по##й', 'похуй'), ('п*здец', 'пиздец'), ('ох*еешь', 'охуеешь'), ('дол*оеб', 'долбоеб'), ('ни*уя', 'нихуя'),
                       ('збсь', 'заебись'), ('дол*оеб', 'долбоеб'), ('за***ло', 'заебало'), ('по*уй', 'похуй'), ('до*уя', 'дохуя'),
                       ('пи*ди', 'пизди'), ('пиз*уйте', 'пиздуйте'), ('на*ер', 'нахер'), ('*уетень', 'хуетень'),
                       ('от*издит', 'отпиздит'), ('*банутым', 'ебанутым'), ('бл*дская', 'блядская'), ('бл*дский', 'блядский'),
                       ('бл*дское', 'блядское'), ('бл*дские', 'блядские'), ('*идорасы', 'пидорасы'), ('*идорас', 'пидорас'),
                       ('*идорасу', 'пидорасу'), ('*идорасе', 'пидорасе'), ('*идорасов', 'пидорасов'), ('*идорасом', 'пидорасом'),
                       ('*идорасам', 'пидорасам'), ('*идорасах', 'пидорасах'), ('*идорасами', 'пидорасами'),
                       ('зае*ала', 'заебала'), ('зае*ало', 'заебало'), ('зае*ал', 'заебал'), ('зае*али', 'заебали'),
                       ('е*ашу', 'ебашу'), ('е*ашим', 'ебашим'), ('е*ашишь', 'ебашишь'), ('е*ашите', 'ебашите'),
                       ('е*ашит', 'ебашит'), ('е*ашил', 'ебашил'), ('е*ашили', 'ебашили'), ('е*ашила', 'ебашила'),
                       ('е*ашило', 'ебашило'), ('е*ашат', 'ебашат'),  ('а*уевший', 'ахуевший'), ('а*уевшая', 'ахуевшая'),
                       ('а*уевшее', 'ахуевшее'), ('а*уевшего', 'ахуевшего'), ('а*уевшей', 'ахуевшей'), ('а*уевших', 'ахуевших'),
                       ('пох*р', 'похер'), ('расп*здяй', 'распиздяй'), ('расп*здяю', 'распиздяю'), ('расп*здяе', 'распиздяе'),
                       ('расп*здяем', 'распиздяем'), ('расп*здяи', 'распиздяи'), ('расп*здяями', 'распиздяями'),
                       ('расп*здяям', 'распиздяям'), ('расп*здяев', 'распиздяев'), ('пох*уй', 'похуй'),
                       ('п*здят', 'пиздят'), ('нех*й', 'нехуй'), ('п*здаболов', 'п*здаболов'), ('п*здаболом', 'п*здаболом'),
                       ('п*здаболами', 'п*здаболами'), ('п*здаболах', 'п*здаболах'), ('п*здабол', 'п*здабол'),
                       ('п*здаболе', 'п*здаболе'), ('п*здаболы', 'п*здаболы'), ('п*здаболов', 'пиздаболов'),
                       ('с*кам', 'сукам'), ('п*дор', 'пидор'), ('п*дора', 'пидора'), ('п*дору', 'пидору'), ('п*доре', 'пидоре'),
                       ('п*дором', 'пидором'), ('п*доров', 'пидоров'), ('п*дорах', 'пидорах'), ('*лядь', 'блядь'),
                       ('п*дорасы', 'пидорасы'), ('п*дорасов', 'пидорасов'), ('п*дорасам', 'пидорасам'),
                       ('п*дорасах', 'пидорасах'), ('е*анный', 'ебанный'), ('у*бком', 'уебком'),
                       ('у*бке', 'уебке'), ('у*бка', 'уебка'), ('у*бку', 'уебку'), ('е**шить', 'ебашить'),
                       ('нах*й', 'нахуй'), ('пи*дец', 'пиздец'), ('бл*дь', 'блядь'), ('ж*пе', 'жопе'),
                       ('*издец', 'пиздец'), ('д*рьмо', 'дерьмо'), ('про*бали', 'проебали'),
                       ('f**k', 'fuck'), ('с*кой', 'сукой'), ('них*ево', 'нихуево'), ('п*нис', 'пенис'),
                       ('е*ал', 'ебал'), ('на*уй', 'нахуй'), ('бл*', 'бля'), ('*ексом', 'сексом'),
                       ('*екс', 'секс'), ('*изды', 'пизды'), ('с*ксуально', 'сексуально'),
                       ('с*ксуальном', 'сексуальном'), ('трах#ть', 'трахать'), ('бл**ь', 'блядь'), ('г@вно', 'говно'),
                       ('х#я', 'хуя'), ('нах#й', 'нахуй'), ('с&ука', 'сука'), ('долбо**ы', 'долбоебы'),
                       ('на**я', 'нахуя'), ('х....ня', 'хуйня'), ('еб*л', 'ебал'), ('заеб@ло', 'заебало'),
                       ('ж*ой', 'жопой'), ('бл&дь', 'блядь'), ('г**не', 'говне'), ('зае@ашу', 'заебашу'),
                       ('е*бать', 'ебать'), ('еб*чие', 'ебучие'), ('блдь', 'блядь'), ('дох*я', 'дохуя'),
                       ('прих*ели', 'прихуели'), ('о*уительных', 'охуительных'), ('про%б', 'проёб'),
                       ('пи***жом', 'пиздежом'), ('х..р', 'хер'), ('пиз...дец', 'пиздец'), ('обос@@ть', 'обосрать'),
                       ('ё#аные', 'ёбаные'), ('бл..и', 'бляди'), ('@уй', 'хуй'), ('пиз#ец', 'пиздец'), ('бл#', 'бля'),
                       ('п####ц', 'пиздец'), ('о&уевать', 'охуевать'), ('б***ь', 'блядь'), ('х@ями', 'хуями'),
                       ('б...ть', 'блять'), ('н@еб@ли', 'наебали'), ('е*анутости', 'ебанутости'), ('п..ц', 'пиздец'),
                       ('б*я', 'бля'), ('ах*е', 'ахуе'), ('п*здой', 'пиздой'), ('пиз*еца', 'пиздеца'),
                       ('подн*срать', 'поднасрать'), ('бля*ей', 'блядей'), ('них@@я', 'нихуя'), ('еб#ть', 'ебать'),
                       ('п*ец', 'пиздец'), ('бл*ки', 'блядки'), ('пи*данулся', 'пизданулся'), ('ж*пу', 'жопу'),
                       ('обоср@лись', 'обосрались'), ('г@нд0н', 'гондон'), ('б@рыг', 'барыг'), ('о*уели', 'охуели'),
                       ('долб**б', 'долбоёб'), ('е..ть', 'ебать'), ('ху*ней', 'хуйней'), ('с#кса', 'секса'),
                       ('х*йнуть', 'хуйнуть'), ('уеб@нов', 'уебанов'), ('еб*ло', 'ебало'), ('зае..али', 'заебали'),
                       ('нах..й', 'нахуй'), ('въ*бывать', 'въёбывать'), ('на*бывать', 'наёбывать'), ('зло@бучей', 'злоебучей'),
                       ('ох*евшие', 'охуевшие'), ('х@евы', 'хуевы'), ('пи%$ец', 'пиздец'), ('еб*наты', 'ебанаты'),
                       ('тр#халась', 'трахалась'), ('на#уй', 'нахуй'), ('@лядь', 'блядь'), ('ох**нного', 'охуенного'),
                       ('долба#б', 'долбаёб'), ('е@чая', 'ебучая'), ('прос*али', 'просрали'), ('о@уела', 'охуела'),
                       ]
        for bad, good in uncensoring:
            self.word_replaces.append((bad, good))

        fp = os.path.join(data_dir, 'speller', 'dict', 'replaces.txt')
        with open(fp) as rdr:
            pairs = [pair for pair in re.split(r'\n{2,}', rdr.read(), flags=re.MULTILINE) if pair]
            for pair in pairs:
                lines = pair.split('\n')
                if len(lines) != 2:
                    raise RuntimeError('Invalid line "{}" in "{}" file'.format(pair, fp))

                bad, good = lines

                if re.search('[a-z]', good, flags=re.I):
                    print(f'ERROR: латиница в замене {bad} ==> {good}')
                    exit(0)

                if re.match(r'^по\-\w+', bad) is not None:
                    self.repl_rx__1.append((bad, good))
                elif re.search(r'\W', bad) is None:
                    self.word_replaces.append((bad, good))
                elif re.search(r'(\w[ ]?)\-([ ]?\w)', bad):
                    bad2 = re.sub(r'(\w)\-(\w)', r'\1\-\2', bad)
                    self.repl_rx.append((bad2, good))
                else:
                    self.repl_rx.append((bad, good))

        with open(os.path.join(data_dir, 'poetry', 'dict', 'word2tags.dat'), 'r') as rdr:
            for line in rdr:
                if line:
                    fields = line.split('\t')
                    word = fields[0].replace(' - ', '-')
                    self.known_words.add(word.lower())
                    upos = fields[1]
                    if upos in ('ИНФИНИТИВ', 'ДЕЕПРИЧАСТИЕ'):
                        upos = 'ГЛАГОЛ'

                    self.word2upos[word.lower()].add(upos)

        self.word2upos["хочется"].add("ГЛАГОЛ")

        with open(os.path.join(data_dir, 'speller', 'dict', 'known_words.2.txt'), 'r') as rdr:
            for line in rdr:
                freq, word = line.strip().split('\t')
                if int(freq) >= 20 and not word.endswith('ъ') and re.search(r'цц|ьь|ъъ|чч|ыы', word) is None:
                    self.known_words.add(word)

        for fn in ['known_words_for_spellchecker.dat', 'добавка из викисловаря в known_words спеллера.txt', 'добавка из викисловаря в known_words спеллера.2.txt']:
            with open(os.path.join(data_dir, 'speller', 'dict', fn), 'r') as rdr:
                for line in rdr:
                    word = line.strip()
                    if word:
                        self.known_words.add(word.lower())

        # 18.11.2024 слова из корпуса RUCOLA2 (исправленные тексты) в качестве источника нормальных слов
        fpx = glob.glob(os.path.join(data_dir, 'speller', 'rucola2') + '/**/test.json', recursive=True)
        fpx.sort(key=os.path.getmtime, reverse=True)
        # первый файл - самый свежий
        fp = fpx[0]
        with open(fp) as f:
            for sample in json.load(f):
                if sample['fixed_text']:
                    self.known_words.update(tokenize_slowly(sample['fixed_text']))

        for bad_word, good_word in self.word_replaces:
            if ' ' not in good_word and good_word not in self.known_words:
                self.known_words.add(good_word)

        with open(os.path.join(output_dir, 'spellcheck.pkl'), 'wb') as f:
            pickle.dump(self.known_words, f)
            pickle.dump(self.word2upos, f)
            pickle.dump(self.repl_rx, f)
            pickle.dump(self.repl_rx__1, f)
            pickle.dump(self.word_replaces, f)
            #pickle.dump(self.acceptable_edits, f)

        self.post_load()

    def load(self, data_dir):
        with open(os.path.join(data_dir, 'spellcheck.pkl'), 'rb') as f:
            self.known_words = pickle.load(f)
            self.word2upos = pickle.load(f)
            self.repl_rx = pickle.load(f)
            self.repl_rx__1 = pickle.load(f)
            self.word_replaces = pickle.load(f)
            #self.acceptable_edits = pickle.load(f)

        self.post_load()

    def post_load(self):
        self.repl_trie = TrieNode()
        for bad, good in self.word_replaces:
            self.repl_trie.insert(bad, good)

        if self.allow_norwig_speller:
            self.norwig_spell = SpellChecker(distance=1)
            self.norwig_spell.word_frequency.load_words(self.known_words)
        else:
            self.norwig_spell = None

    emoji_pattern = re.compile("^(©|" + EMOJI_CHARACTER + ")", flags=re.UNICODE)

    def is_known_word(self, word: str, strict_yofication: bool=False) -> bool:
        lword = word.lower()
        if lword in self.known_words or word in string.punctuation or word in "«»—–…“”":
            return True

        if not strict_yofication and 'ё' in lword and lword.replace('ё', 'е') in self.known_words:
            return True

        # числа и 70%
        if re.match(r'^\d+%?$', word) is not None:
            return True

        # римские числа
        # VII в. н.э.
        # ^^^
        if re.match(r'^[MXCVI]+$', word) is not None:
            return True

        if PoeticSpellchecker.emoji_pattern.match(word) is not None:
            return True

        return False

    def is_verb(self, word: str) -> bool:
        lword = word.lower()
        if 'ГЛАГОЛ' in self.word2upos.get(lword, ''):
            return True

        if 'ё' in lword and 'ГЛАГОЛ' in self.word2upos.get(lword.replace('ё', 'е'), ''):
            return True

        return False

    def is_verb_only(self, word: str) -> bool:
        # мой ==> False
        # купи ==> True
        lword = word.lower()
        uposes = self.word2upos.get(lword, '')
        return 'ГЛАГОЛ' in uposes and len(uposes) == 1

    def tokenize(self, text: str):
        yield from tokenize_slowly(text)

    def search_oov(self, text: str):
        for token in self.tokenize(text):
            if not self.is_known_word(token):
                yield token

    def fix_rparens2(self, m):
        part1 = m.group(1)
        part2 = m.group(2)
        part3 = m.group(3)  # самый правый разделитель

        word12 = part1+part2
        if self.is_known_word(word12):
            return word12 + part3

        if self.is_known_word(part1) and self.is_known_word(part2):
            return part1 + ' ' + part2 + part3

        return m.group(0)

    def fix_rparens3(self, m):
        part1 = m.group(1)
        part2 = m.group(2)
        part3 = m.group(3)
        part4 = m.group(4)  # самый правый разделитель
        word123 = part1+part2+part3
        if self.is_known_word(word123):
            return word123 + part4

        if self.is_known_word(part1) and self.is_known_word(part2) and self.is_known_word(part3):
            return part1 + ' ' + part2 + ' ' + part3 + part4

        return m.group(0)

    def fix(self, text):
        fixups = []
        text2 = text

        cyr_set = '[АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя]'
        lat2cyr = {'3': 'З', 'K': 'К', 'O': 'О', 'C': 'С', 'A': 'А', 'B': 'В', 'o': 'о', 'a': 'а', 'c': 'с', 'k': 'к', 'y': 'у', '6': 'б'}

        m1 = re.search(r'\b([KOCABoacky])[,!]?\s'+cyr_set, text2)
        if m1:
            for g1, g2 in re.findall(r'\b([KOCABoacky])([,!]?\s'+cyr_set+')', text2):
                text2 = re.sub(rf'\b({g1})({g2})', lambda x: lat2cyr[x.group(1)]+x.group(2), text2)
                fixups.append((g1, lat2cyr[g1]))

        m2 = re.search(cyr_set + r'[,!?.:]?\s([oacky])\b', text2)
        if m2:
            for g1, g2 in re.findall('('+cyr_set + r'[,!?.:]?\s)([oacky])\b', text2):
                text2 = re.sub(rf'({g1}[,!?.:]?\s)({g2})\b', lambda x: x.group(1)+lat2cyr[x.group(2)], text2)
                fixups.append((g2, lat2cyr[g2]))

        # Alien char surrounded by cyrillic chars
        # те6я  ==> тебя
        m2 = re.search(cyr_set + r'([oacky6])' + cyr_set, text2)
        if m2:
            for g1, g2, g3 in re.findall('('+cyr_set + r')([oacky6])(' + cyr_set + ')', text2):
                text2 = re.sub(rf'({g1})({g2})({g3})', lambda x: x.group(1)+lat2cyr[x.group(2)]+x.group(3), text2)
                fixups.append((g2, lat2cyr[g2]))


        # for bad, good in self.repl_rx_1:
        #     m = re.search(bad, text2, flags=re.I)  # | re.MULTILINE
        #     if m is not None:
        #         token1 = m.group(1)  # почему
        #         token2 = m.group(2)  # то
        #
        #         good2 = token1 + '-' + token2
        #         text3 = re.sub(bad, good2, text2, flags=re.I)
        #         assert(text3 != text2)
        #         text2 = text3
        #
        #         fixups.append((m.group(0), good2))

        for bad, good in self.repl_rx:
            m = re.search(r'\b'+bad+r'\b', text2, flags=re.I | re.MULTILINE)
            if m is not None:
                old_str = m.group(0)
                if old_str[0].upper() == old_str[0]:
                    text2 = re.sub(r'\b'+Aa(bad)+r'\b', Aa(good), text2, flags=re.I)
                    new_str = re.sub(r'\b'+Aa(bad)+r'\b', Aa(good), old_str, flags=re.I)
                else:
                    text2 = re.sub(r'\b'+bad+r'\b', good, text2, flags=re.I)
                    new_str = re.sub(r'\b' + bad + r'\b', good, old_str, flags=re.I)

                fixups.append((old_str, new_str))

        for bad, good in [(', лишь,', ' лишь '), (', уже,', ' уже '), (', почему-то,', ' почему-то ')]:
            m = re.search(bad, text2, flags=re.I)
            if m is not None:
                text2 = re.sub(bad, good, text2)
                text2 = re.sub(r'[ ]{2,}', ' ', text2)
                fixups.append((m.group(0), good))

        # По мне, чудн’о названье это,
        #             ^
        if re.search(r'(\w)’(\w)', text2):
            m = re.search(r'\b(\w+’\w+)\b', text2)
            if m:
                token = m.group(1)
                token2 = token.replace('’', '')
                if self.is_known_word(token2):
                    fixups.append((token, token2))
                    text2 = re.sub(r'\b' + token + r'\b', token2, text2)

        # Там поля стоят во-ржи
        #                ^^^^^^
        if re.search(r'\bво\-\w+', text2, flags=re.I):
            m = re.search(r'(во)\-(\w+)', text2, flags=re.I)
            token12 = m.group(0)
            token1 = m.group(1)
            token2 = m.group(2)
            if not self.is_known_word(token12) and self.is_known_word(token2) and not self.is_known_word((token1+token2).lower()):
                fixups.append((token12, token1 + ' ' + token2))
                text2 = re.sub(r'\b' + token1 + '\\-' + token2 + r'\b', token1 + ' ' + token2, text2)

        # Но Любовью бе(з)конечной
        # О чём сказать хотел(бы)вам
        text2 = re.sub(r'\b(\w+)\((\w+)\)(\w+)(\W|$)', lambda m: self.fix_rparens3(m), text2)

        # Когда есть свет, к тому(ж) тепло
        text2 = re.sub(r'\b(\w+)\((\w+)\)(\W|$)', lambda m: self.fix_rparens2(m), text2)

        # Ты дождевик одень ка.
        #             ^^^^^^^^
        # Другой добычи поищу - ка!
        #               ^^^^^^^^^^
        if re.search(r'\sка\b', text2) is not None:
            for m in re.finditer(r'\b(\w+)\sка\b', text2):
                word1 = m.group(1)
                if self.is_verb(word1) or word1.lower() in ['ну', 'на']:
                    text2 = re.sub(r'\b({})\sка\b'.format(word1), '\\1-ка', text2)
                    fixups.append((m.group(0), f'{word1}-ка'))

            for m in re.finditer(r'\b(\w+)\s\-\sка\b', text2):
                word1 = m.group(1)
                if self.is_verb(word1):
                    text2 = re.sub(r'\b({})\s\-\sка\b'.format(word1), '\\1-ка', text2)
                    fixups.append((m.group(0), f'{word1}-ка'))

        # за скучаешь ==> заскучаешь
        for m in re.finditer(r'\b(за)\s(\w+)\b', text2):
            prepos = m.group(1)
            word2 = m.group(2)
            if self.is_verb_only(word2):
                verb12 = prepos+word2
                if self.is_known_word(verb12) and self.is_verb(verb12):
                    text2 = re.sub(r'\b({})\s({})\b'.format(prepos, word2), verb12, text2)
                    fixups.append((m.group(0), verb12))


        # Знаешь-ли, такая штука - жизнь
        # ^^^^^^^^^
        if re.search(r'\-л[иь]\b', text2) is not None:
            for m in re.finditer(r'\b(\w+)\-(л[иь])\b', text2):
                word1 = m.group(1)
                word2 = m.group(2)
                text2 = re.sub(r'\b({})\-(л[иь])\b'.format(word1), '\\1 \\2', text2)
                fixups.append((m.group(0), f'{word1} {word2}'))

        # Мы-же ни к кому не лезли.
        # ^^^^^
        # Надо-ж выдумать такое - во дурак!
        # ^^^^^^
        if re.search(r'\-(же|ж)\b', text2) is not None:
            for m in re.finditer(r'\b(\w+)\-(же|ж)\b', text2):
                word1 = m.group(1)
                if word1.lower() != 'да':  # да-же
                    word2 = m.group(2)
                    text2 = re.sub(r'\b({})\-(же|ж)\b'.format(word1), '\\1 \\2', text2)
                    fixups.append((m.group(0), f'{word1} {word2}'))

        # Мы-бы тоже пришли.
        # Куда - б не пришёл, везде номер первый.
        # Вот полетать где - бы.
        # Он со мною везде, где-б я не был.
        if re.search(r'\s*\-\s*(бы|б)\b', text2) is not None:
            for m in re.finditer(r'\b(\w+)\s*\-\s*(бы|б)\b', text2):
                word1 = m.group(1)
                word2 = m.group(2)
                text2 = re.sub(r'\b({})\s*\-\s*(бы|б)\b'.format(word1), '\\1 \\2', text2)
                fixups.append((m.group(0), f'{word1} {word2}'))

        # Я-б поучаствовал
        # ^^^
        if re.search(r'\-б\b', text2) is not None:
            for m in re.finditer(r'\b(\w+)\-б\b', text2):
                word1 = m.group(1)
                text2 = re.sub(r'\b({})\-б\b'.format(word1), '\\1 б', text2)
                fixups.append((m.group(0), f'{word1} б'))

        # Что такое блогер-это смелость
        #                 ^^^^
        if re.search(r'\-это\b', text2) is not None:
            for m in re.finditer(r'\b(\w+)\-это\b', text2, flags=re.I):
                word1 = m.group(1)
                text2 = re.sub(r'\b({})\-это\b'.format(word1), '\\1 - это', text2)
                fixups.append((m.group(0), f'{word1} - это'))

        # Кому - то повезло
        # ^^^^^^^^^
        if re.search(r' \-\s?то\b', text2) is not None:
            for m in re.finditer(r'(\b|^)(\w+) \-\s?(то)(\b|$)', text2):
                token1 = m.group(2)
                token2 = m.group(3)
                word12 = token1 + '-' + token2
                if self.is_known_word(word12):
                    text2 = re.sub(r'\b({}) \- ({})\b'.format(token1, token2), '\\1-\\2', text2)
                    fixups.append((m.group(0), word12))

        # С деревьев ветки по-срывал!
        #                  ^^^^^^^^^
        # Ты поёшь немного по - французски.
        #                  ^^^^^^^^^^^^^^^
        if re.search(r'\bпо\s?\-\s?\w', text2, flags=re.I) is not None:
            for m in re.finditer(r'\b(по)\s?\-\s?(\w+)\b', text2, flags=re.I):
                token1 = m.group(1)  # по
                token2 = m.group(2)  # срывал
                word12 = token1 + token2

                if self.is_verb(word12):
                    text2 = re.sub(r'\b({})\s?-\s?({})\b'.format(token1, token2), '\\1\\2', text2)
                    fixups.append((m.group(0), word12))

            for bad, good in self.repl_rx__1:
                m = re.search(bad, text2, flags=re.I)  #  | re.MULTILINE
                if m is not None:
                    text2 = re.sub(r'\b'+bad+r'\b', good, text2)
                    text2 = re.sub(r'\b'+Aa(bad)+r'\b', Aa(good), text2)
                    fixups.append((m.group(0), good))

            # Ты поёшь немного по - французски.
            #                  ^^^^^^^^^^^^^^^
            for m in re.finditer(r'\b(по) \- (\w+)\b', text2, flags=re.I):
                token1 = m.group(1)  # по
                token2 = m.group(2)  # французски
                word12 = token1 + '-' + token2

                if self.is_known_word(word12):
                    text2 = re.sub(r'\b({}) - ({})\b'.format(token1, token2), '\\1-\\2', text2)
                    fixups.append((m.group(0), word12))

        # под-держать ==> поддержать
        if re.search(r'\bпод\s?\-\s?\w', text2, flags=re.I) is not None:
            for m in re.finditer(r'\b(под)\s?\-\s?(\w+)\b', text2, flags=re.I):
                token1 = m.group(1)  # под
                token2 = m.group(2)  # держать
                word12 = token1 + token2

                if self.is_verb(word12):
                    text2 = re.sub(r'\b({})\s?-\s?({})\b'.format(token1, token2), '\\1\\2', text2)
                    fixups.append((m.group(0), word12))

        # из-под-палки
        if re.match(r'\bиз\s?\-\s?под\s?\-\s?\w+\b', text2, flags=re.I) is not None:
            for m in re.finditer(r'\b(из)\s?\-\s?(под)\s?\-\s?(\w+)\b', text2, flags=re.I):
                token1 = m.group(1) # из
                token2 = m.group(2) # под
                token3 = m.group(3) # палки

                if self.is_known_word(token3):
                    text2 = re.sub(r'\b({})\s?\-\s?({})\s?\-\s?({})\b'.format(token1, token2, token3), '\\1-\\2 \\3', text2)
                    fixups.append((m.group(0), token1 + '-' + token2 + ' ' + word12))

        for token in self.tokenize(text2):
            if re.match(r'^</?\w+>$', token):
                # теги типа <song> и <verse> не обрабатываем
                continue

            if re.match(r'^\d+$', token):
                # Числа игнорируем
                continue

            ltoken = token.lower()

            token0 = None
            token2 = None

            repl = self.repl_trie.search(ltoken)
            if repl is not None:
                token0 = repl
                token2 = token0
                if token[0].lower() != token[0]:
                    token2 = token2[0].upper() + token2[1:]

                fixups.append((token, token2))
                if token.startswith('*'):
                    text2 = re.sub(r'(?<=\W)' + token.replace('*', '\\*') + r'\b', token2, text2)
                else:
                    text2 = re.sub(r'\b' + token.replace('*', '\\*') + r'\b', token2, text2)
                continue

            if ltoken not in self.known_words:
                # п0д ==> под
                m = re.match(r'^\w+0\w+|\w+0|0\w+$', ltoken)
                if m:
                    token2 = ltoken.replace('0', 'о')
                    if token[0].lower() != token[0]:
                        token2 = token2[0].upper() + token2[1:]
                    fixups.append((token, token2))
                    text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                    continue

                # лa’вровый
                # полон′или
                m = re.match(r'^(\w+)[’′](\w+)$', ltoken)
                if m:
                    head = m.group(1)
                    tail = m.group(2)
                    token2 = head + tail
                    if self.is_known_word(token2):
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search('ъ', token, flags=re.I):
                    # вплотъ ==> вплоть
                    token0 = re.sub(r'^(\w*)ъ(\w*)$', '\\1ь\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search('\wйу', token, flags=re.I):
                    # выпускайут ==> выпускают
                    token0 = re.sub(r'^(\w+)йу(\w*)$', '\\1ю\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search('ш', token, flags=re.I):
                    # тёша ==> тёща
                    token0 = re.sub(r'^(\w*)ш(\w*)$', '\\1щ\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.match('^\w+"\w+$', token):
                    # под"езда ==> подъезда
                    token0 = re.sub(r'^(\w+)"(\w+)$', '\\1ъ\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search('щ', token, flags=re.I):
                    # щоколад ==> шоколад
                    token0 = re.sub(r'^(\w*)щ(\w*)$', '\\1ш\\2', token, flags=re.I)
                    if self.is_known_word(token0, strict_yofication=True):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search('^бези', token, flags=re.I):
                    # безискусных ==> безыскусный
                    token0 = re.sub(r'^(без)и(\w*)$', '\\1ы\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search(r'^\w+ться$', token, flags=re.I):
                    # льються ==> льются
                    token0 = re.sub(r'^(\w+)ться$', '\\1тся', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search(r'^\w+тся$', token, flags=re.I):
                    # заниматся ==> заниматься
                    token0 = re.sub(r'^(\w+)тся$', '\\1ться', token, flags=re.I)
                    if self.is_known_word(token0) and self.is_verb(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                # хочецца
                if re.search(r'^\w+цца$', token, flags=re.I):
                    # хочецца ==> хочется
                    token0 = re.sub(r'^(\w+)цца$', '\\1тся', token, flags=re.I)
                    token00 = re.sub(r'^(\w+)цца$', '\\1ться', token, flags=re.I)
                    if self.is_known_word(token0) and self.is_verb(token0) and not self.is_known_word(token00):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search(r'^\w+тса$', token, flags=re.I):
                    # улыбаетса ==> улыбается
                    # улыбаютса ==> улыбаются
                    token0 = re.sub(r'^(\w+)тса$', '\\1тся', token, flags=re.I)
                    token00 = re.sub(r'^(\w+)тса$', '\\1ться', token, flags=re.I)
                    if self.is_known_word(token0) and self.is_verb(token0) and not self.is_known_word(token00):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search(r'^\w+а(ю|е)ца$', token, flags=re.I):
                    # раздаюца ==> раздаются
                    # случаеца
                    token0 = re.sub(r'^(\w+а(ю|е))ца$', '\\1тся', token, flags=re.I)
                    token00 = re.sub(r'^(\w+а(ю|е))ца$', '\\1ться', token, flags=re.I)
                    if self.is_known_word(token0) and self.is_verb(token0) and not self.is_known_word(token00):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search(r'^здел\w+$', token, flags=re.I):
                    # зделать ==> сделать
                    token0 = re.sub(r'^здел(\w+)$', 'сдел\\1', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]

                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.search(r'^\w+щь$', token, flags=re.I):
                    # увидищь ==> увидишь
                    token0_1 = re.sub(r'^(\w+)щь$', '\\1шь', token, flags=re.I)

                    # пожарищь ==> пожарищ
                    # плащь ==> плащ
                    token0_2 = re.sub(r'^(\w+)щь$', '\\1щ', token, flags=re.I)

                    if self.is_known_word(token0_1) and not self.is_known_word(token0_2):
                        # увидищь ==> увидишь
                        token0 = token0_1
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue
                    elif self.is_known_word(token0_2) and not self.is_known_word(token0_1):
                        # пожарищь ==> пожарищ
                        token0 = token0_2
                        token2 = token0
                        if self.is_known_word(token0):
                            token2 = token0
                            if token[0].lower() != token[0]:
                                token2 = token2[0].upper() + token2[1:]
                            fixups.append((token, token2))
                            text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                            continue

                if re.search(r'^\w*[бвгджзклмнпрстфхцчшщ]ь[аеёиоуыэюя]\w+$', token, flags=re.I):
                    # изьянов ==> изъянов
                    token0 = re.sub(r'^(\w*[бвгджзклмнпрстфхцчшщ])ь([аеёиоуыэюя]\w+)$', '\\1ъ\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                        fixups.append((token, token2))
                        text2 = re.sub(r'\b' + token + r'\b', token2, text2)
                        continue

                if re.match(r'^без[кпстфхц]\w+', token, flags=re.I):
                    # безконечный ==> бесконечный
                    # безценна ==> бесценна
                    token0 = 'бес' + ltoken[3:]
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.match(r'^бес[бвгджзлмнр]\w+', token, flags=re.I):
                    # безпардонный ==> беспардонный
                    token0 = 'без' + ltoken[3:]
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'([бвгджзклмнпрстфхцчшщ])\1{2,}', token, flags=re.I):
                    # ввверх ==> вверх
                    # испуганнной ==> испуганной

                    # НО: "Ммм" оставляем такие цепочки без изменения
                    if len(set(token.lower())) != 1:
                        if not self.is_known_word(token):
                            # ввверх ==> вверх
                            token0 = re.sub(r'([бвгджзклмнпрстфхцчшщ])(\1){2,}', r'\1\2', token, flags=re.I)
                            if self.is_known_word(token0):
                                token2 = token0
                                if token[0].lower() != token[0]:
                                    token2 = token2[0].upper() + token2[1:]
                            else:
                                # очччень ==> очень
                                token0 = re.sub(r'([бвгджзклмнпрстфхцчшщ])(\1){2,}', r'\2', token, flags=re.I)
                                if self.is_known_word(token0):
                                    token2 = token0
                                    if token[0].lower() != token[0]:
                                        token2 = token2[0].upper() + token2[1:]

                elif re.search(r'([ыщьъй])\1', token, flags=re.I):
                    # Удивителььный ==> Удивительный
                    token0 = re.sub(r'([ыщьъй])\1{1,}', r'\1', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'[жшщ]ы', token, flags=re.I):
                    # обычнейшый ==> обычнейший
                    token0 = re.sub(r'([жшщ])ы', r'\1и', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+[аеёиоуыя]шся$', token, flags=re.I):
                    # боишся ==> боишься
                    token0 = re.sub(r'^(\w+[аеёиоуыя])шся$', '\\1шься', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w{2,}[аеёио]ш$', token, flags=re.I):
                    # сможеш ==> сможешь
                    token0 = re.sub(r'^(\w+[аеёио])ш$', '\\1шь', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w{2,}[аеёиоуыюя]ж$', token, flags=re.I):
                    # уничтож ==> уничтожь
                    token0 = re.sub(r'^(\w+[аеёиоуюыя])ж$', '\\1жь', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]

                elif re.search(r'^\w{2,}[аеёиоуюя]ч$', token, flags=re.I):
                    # пресеч ==> пресечь
                    token0 = token + 'ь'
                    if self.is_known_word(token0):
                        token2 = token0

                elif re.search(r'^\w{2,}[аеёиоуыюя][шч]ь$', token, flags=re.I):
                    # гадёнышь ==> гадёныш
                    # скрипачь ==> скрипач
                    token0 = token[:-1]
                    if self.is_known_word(token0):
                        token2 = token0

                elif re.search(r'^\w{2,}чём$', token, flags=re.I):
                    # лучём ==> лучом
                    token0 = re.sub(r'^(\w{2,})чём$', '\\1чом', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w*[бвгджзклмнпрстфхцчшщ]ъ[аеёиоуыэюя]\w*$', token, flags=re.I):
                    # пъедестала ==> пьедестала
                    token0 = re.sub(r'^(\w*[бвгджзклмнпрстфхцчшщ])ъ([аеёиоуыэюя]\w*)$', '\\1ь\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w*чё\w*$', token, flags=re.I):
                    # девчёночка ==> девчоночка
                    token0 = re.sub(r'^(\w*)чё(\w*)$', '\\1чо\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+[бвгджзклмнпрстфхцчшщ]ъ$', token, flags=re.I):
                    if token.lower() not in ('азъ',):
                        # пылъ ==> пыль
                        token0 = token[:-1] + 'ь'
                        if self.is_known_word(token0):
                            token2 = token0
                            if token[0].lower() != token[0]:
                                token2 = token2[0].upper() + token2[1:]
                        else:
                            # крикъ ==> крик
                            token0 = token[:-1]
                            if self.is_known_word(token0):
                                token2 = token0
                                if token[0].lower() != token[0]:
                                    token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^обь[аеёиоуыэюя]\w+$', token, flags=re.I):
                    # обьяснять ==> объяснять
                    token0 = re.sub(r'^обь([аеёиоуыэюя]\w+)$', 'объ\\1', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search('[3a-zëáóúόéýќўú]', token, flags=re.I) is not None and re.search('[абвгдеёжзийклмнопрстуфхцчшщъыьэюя]', token, flags=re.I) is not None:
                    # В слове смешана латиница и кириллица.
                    token0 = restore_cyrillic(token)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^изч[аеёиоуыэюя]\w+$', token, flags=re.I):
                    # изчезать ==> исчезать
                    token0 = re.sub(r'^из(ч[аеёиоуыэюя]\w+)$', 'ис\\1', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^здав\w+$', token, flags=re.I):
                    # здаваться ==> сдаваться
                    token0 = re.sub(r'^з(дав\w+)$', 'с\\1', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w*зп\w+$', token, flags=re.I):
                    # изподлобья ==> исподлобья
                    token0 = re.sub(r'^(\w*)зп(\w+)$', '\\1сп\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+шол$', token, flags=re.I):
                    # прошол ==> прошёл
                    token0 = re.sub(r'^(\w+)шол$', '\\1шёл', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+щём$', token, flags=re.I):
                    # плющём ==> плющом
                    token0 = re.sub(r'^(\w+)щём$', '\\1щом', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+чь[кн]\w+$', token, flags=re.I):
                    # ночькой ==> ночкой
                    token0 = re.sub(r'^(\w+ч)ь([кн]\w+)$', '\\1\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'\w+ч[бвгджзклмнпрстфхц]\w*', token, flags=re.I):
                    # улетучтесь ==> улетучьтесь
                    token0 = re.sub(r'(\w+ч)([бвгджзклмнпрстфхц]\w*)', '\\1ь\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+вся$', token, flags=re.I):
                    # слався ==> славься
                    token0 = re.sub(r'^(\w+)вся$', '\\1вься', token, flags=re.I)
                    if self.is_known_word(token0) and self.is_verb(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+вте$', token, flags=re.I):
                    # представте ==> представьте
                    token0 = re.sub(r'^(\w+)вте$', '\\1вьте', token, flags=re.I)
                    if self.is_known_word(token0) and self.is_verb(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+втесь$', token, flags=re.I):
                    # представтесь ==> представьтесь
                    token0 = re.sub(r'^(\w+)втесь$', '\\1вьтесь', token, flags=re.I)
                    if self.is_known_word(token0) and self.is_verb(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'щю', token, flags=re.I):
                    # грущю ==> грущу
                    token0 = re.sub(r'^(\w*)щю(\w*)$', '\\1щу\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search('чю', token, flags=re.I):
                    # канючю ==> канючу
                    token0 = re.sub('чю', 'чу', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search('чь[бвгджзклмнпрстфх]', token, flags=re.I):
                    # мечьтах ==> мечтах
                    token0 = re.sub('чь([бвгджзклмнпрстфх])', 'ч\\1', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search('чор', token, flags=re.I):
                    # чорный ==> чёрный
                    token0 = re.sub('чор', 'чёр', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search('щя', token, flags=re.I):
                    # обращяя ==> обращая
                    token0 = re.sub('щя', 'ща', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search('щк', token, flags=re.I):
                    # зайчищки ==> зайчишки
                    token0 = re.sub('щк', 'шк', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search('чя', token, flags=re.I):
                    # мелочях ==> мелочах
                    token0 = re.sub('чя', 'ча', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search('[щч]ь[н]', token, flags=re.I):
                    # мощьный ==> мощный
                    token0 = re.sub('([щч])ь([н])', '\\1\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.match('^зб\w+$', token, flags=re.I):
                    # збудутся ==> сбудутся
                    token0 = 'с'+token[1:]
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+жь$', token, flags=re.I):
                    # грабёжь ==> грабёж
                    token0 = re.sub(r'^(\w+ж)ь$', '\\1', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^\w+чен\w+$', token, flags=re.I):
                    # рученками ==> ручонками
                    token0 = re.sub(r'^(\w+)че(н\w+)$', '\\1чо\\2', token, flags=re.I)
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^(воз|вз|из|низ|раз|без|чрез|через)([кптхчцшщфс]\w+)$', token, flags=re.I):
                    # безсмертие ==> бессмертие
                    m = re.match(r'^(воз|вз|из|низ|раз|без|чрез|через)([кптхчцшщфс]\w+)$', token, flags=re.I)
                    prefix = m.group(1).replace('з', 'с')
                    token0 = prefix + m.group(2)
                    #print('DEBUG@2494 token={} token0={}'.format(token, token0))
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif re.search(r'^(вос|вс|ис|нис|рас|бес|чрес|черес)([бвгджз]\w+)$', token, flags=re.I):
                    # всдыхая ==> вздыхая
                    m = re.match(r'^(вос|вс|ис|нис|рас|бес|чрес|черес)([бвгджз]\w+)$', token, flags=re.I)
                    prefix = m.group(1).replace('с', 'з')
                    token0 = prefix + m.group(2)
                    #print('DEBUG@2508 token={} token0={}'.format(token, token0))
                    if self.is_known_word(token0):
                        token2 = token0
                        if token[0].lower() != token[0]:
                            token2 = token2[0].upper() + token2[1:]
                elif self.norwig_spell is not None and len(token) >= 7 and re.match(r'^\w+$', token):
                    # Пробуем заменить длинное слово по словарю
                    token3 = self.norwig_spell.correction(token.lower())
                    if token3:
                        if token[0].lower() != token[0]:
                            token3 = token3[0].upper() + token3[1:]
                        if token3 != token:
                            token2 = token3

                if token2:
                    fixups.append((token, token2))
                    text2 = re.sub(r'\b' + token + r'\b', token2, text2)

            if False:
                # Подлежащее отделено от сказуемого запятой
                # А я, хочу встречать рассветы.
                for text3, left, sbj_str in re.findall(r'[.?!^]\n((.*)\b(я|ты|мы|вы), .+[.?!])', text2, flags=re.I):
                    bad_str = text3
                    new_str = text3.replace(sbj_str + ',', sbj_str)
                    parsing = self.parser.parse_text(text3)[0]

                    sbj = None
                    for t in parsing:
                        if t.form == sbj_str:
                            sbj = t
                            break

                    # слева от подлежащего есть глагол?
                    if sbj:
                        bad_case = False
                        for t in parsing:
                            if t.upos == 'VERB' and t.get_attr('VerbForm') in ['Inf', 'Fin'] and int(t.id) < int(sbj.id):
                                bad_case = True
                                break
                            elif t.form == sbj_str:
                                break

                        if not bad_case:
                            # Справа от подлежащего есть глагольное сказуемое?
                            for t in parsing:
                                if t.upos == 'VERB' and t.get_attr('VerbForm') == 'Fin' and t.deprel == 'root' and sbj.head == t.id:
                                    # Можем удалить запятую после подлежащего
                                    fixups.append((bad_str, new_str))
                                    text2 = re.sub(bad_str, new_str, text2)
                                    break

        return text2, fixups


if __name__ == '__main__':
    from generative_poetry.udpipe_parser import UdpipeParser

    proj_dir = os.path.expanduser('~/polygon/text_generator')
    tmp_dir = os.path.join(proj_dir, 'tmp')
    models_dir = os.path.join(proj_dir, 'models')

    parser = UdpipeParser()
    parser.load(models_dir)

    schecker = PoeticSpellchecker(parser)
    schecker.compile(os.path.join(proj_dir, 'data'), os.path.join(proj_dir, 'data/speller'))

    # A small check of functionality
    new_text, fixups = schecker.fix('за скучаешь')
    assert(new_text=='заскучаешь')
    print(new_text)

    r = schecker.is_known_word('ещё')
    assert(r is True)

    print('All done :)')
