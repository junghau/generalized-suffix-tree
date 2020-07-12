import os
import argparse
from suffix_tree import *
from highlighter import printHighlight

def test(wordList, gst):
    import random
    print("Testing...")
    randomized = list(wordList)
    random.shuffle(randomized)
    for word in tqdm(randomized):
        n = len(word)
        for start in range(n):
            for end in range(start,n):
                substring = word[start:end+1]
                naive = [x for x in wordList if substring in x]
                gstac = gst.match(substring)
                if len(naive) != len(gstac):
                    print("Wrong:", substring)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Preprocess word list to a generalized suffix tree for efficient substring querying.')
    parser.add_argument("path", type=str, help="Path to the file containing line separated word list.")
    parser.add_argument("-cs", "--case-sensitive", action='store_true', help="Enable case sensitive searching.")
    parser.add_argument("-pp", "--print-progress", action='store_true', help="Print generalized suffix tree parsing process.")
    parser.add_argument("-pre", "--preprocess", action='store_true', help="Scan through the input to get the alphabet and to auto select a terminating char that is 1 higher than the max alphabet used in the word list.")
    parser.add_argument("-al", "--alphabet-lookup", action='store_true', help="Preprocess the input and use alphabet lookup table.")
    parser.add_argument("-max", "--max-alphabet", type=int, default=None, help="Max value of char, dafault to 255. Overriden when preprocessing or alphabet lookup is enabled.")
    parser.add_argument("-s", "--sort", action='store_true', help="Sort query results alphabetically.")

    opt = parser.parse_args()

    wordList = open(opt.path, "rb").readlines()
    wordList = list(map(lambda x:x.decode("utf-8").rstrip(), wordList))

    # default values
    lookup_table = None
    termChar = chr(256) # it is sufficient to be a char not used anywhere in the input word list

    if opt.preprocess or opt.alphabet_lookup:
        lookup_table, termChar = getAlphabetTable(wordList) # override termChar
        if not opt.alphabet_lookup:
            lookup_table = None # disable lookup table if not specified by user
        print(f"Terminating char value: {ord(termChar)}")
    elif opt.max_alphabet:
        opt.max_alphabet += 1 # +1 to include term char
        termChar = chr(opt.max_alphabet)

    print("Initializing Generalized Suffix Tree")
    gst = GeneralizedSuffixTree(wordList, termChar=termChar, alphabetMax=opt.max_alphabet, alphabetLookup=lookup_table, case_sensitive=opt.case_sensitive,print_progress=opt.print_progress)

    # test(wordList, gst)
    # exit()

    # to check if alphabet in query is also in wordList; or within the specified max alphabet
    check_alphabet = lambda query: all(map(lambda x:ord(x) in lookup_table,     query))
    check_max      = lambda query: all(map(lambda x:ord(x) <= opt.max_alphabet, query))

    while True:
        query = input("Enter search query: ")
        if not opt.case_sensitive:
            query = query.lower()
        os.system('cls')
        print("Query:", query)

        if opt.alphabet_lookup and not check_alphabet(query) or opt.max_alphabet and not check_max(query):
            match = []
        else:
            match = gst.match(query, ret_match_index=True) # defaultdict mode

        if opt.sort:
            match.sort()

        for word,start in match:
            end = start + len(query)
            printHighlight(word, start, end)
        print("\nTotal", len(match))
