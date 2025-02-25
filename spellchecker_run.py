from spellcheck import PoeticSpellchecker
from udpipe_parser import UdpipeParser



if __name__ == '__main__':
    parser = UdpipeParser()
    parser.load('./models')

    schecker = PoeticSpellchecker(parser)
    schecker.load('./data')

    new_text, fixups = schecker.fix("Вмести в себя все от кровенья мира")
    print(new_text)
