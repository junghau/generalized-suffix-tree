import colorama
from colorama import init
init()
from colorama import Fore, Back, Style
# exclusive end
def printHighlight(word, hStart, hEnd, hColor=Back.YELLOW):
    # hColor can also be Back.GREEN
    enableHighlight = Fore.BLACK + hColor
    disableHighlight = Fore.RESET + Back.RESET
    print(word[:hStart] + enableHighlight + word[hStart:hEnd] + disableHighlight + word[hEnd:])