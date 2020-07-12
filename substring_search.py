import os
import argparse
from suffix_tree import *
from highlighter import printHighlight

def getMatch(startNode, result_accumulator):
    def traverse(currNode):
        if currNode.isLeaf():
            suffixOrigin = currNode.suffixOrigin
            while suffixOrigin is not None: # multiple words can have the same suffix, so need to loop through all
                wordID = suffixOrigin.wordID
                suffixIndex = suffixOrigin.suffixIndex
                if wordID not in result_accumulator or suffixIndex < result_accumulator[wordID]:
                    result_accumulator[wordID] = suffixIndex
                suffixOrigin = suffixOrigin.next
        else:
            for childNode in currNode.getChildren():
                traverse(childNode) # assignment to result is unnecessary     
    traverse(startNode)
    return result_accumulator

def matchSubstring(wordList, gst, query):
    """
    Phase 1: traverse to node corresponding to the query
    Phase 2: search all leaves from that node recursively to get match
    """
    if query == "" or query == gst.termChar:
        return []
        
    ### Phase 1 ###
    currNode = gst.root #gstRoot.getChild(query[0])
    pWordList = gst.wordList # preprocessed word list by GST
    i = 0
    while i < len(query):
        c = query[i]
        if currNode.hasChild(c):
            currNode = currNode.getChild(c)
            edgeSize = currNode.getEdgeSize()
            wordID = currNode.suffixOrigin.wordID
            istart = currNode.istart

            cmplen = min(len(query) - i, edgeSize) # comparison length
            for k in range(cmplen):
                if query[i+k] != pWordList[wordID][istart+k]:
                    return []
            i += cmplen
        else:
            return [] # no match

    ### Phase 2 ###
    result_dict = {}
    getMatch(currNode, result_dict)

    result = list(result_dict.items())

    mapfst = lambda f: lambda x:(f(x[0]), x[1])
    id2word = lambda i:wordList[i]

    # convert wordID to word from wordList, while retaining the suffixIndex
    return list(map(mapfst(id2word), result))

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
                gstac = matchSubstring(wordList, gst, substring)
                if len(naive) != len(gstac):
                    print("Wrong:", substring)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Preprocess word list to a generalized suffix tree for efficient substring querying.')
    parser.add_argument("path", type=str, help="Path to the file containing line separated word list.")
    parser.add_argument("-cs", "--case-sensitive", action='store_true', help="Enable case sensitive searching.")
    parser.add_argument("-pp", "--print-progress", action='store_true', help="Print generalized suffix tree parsing process.")
    parser.add_argument("-al", "--alphabet-lookup", action='store_true', help="Compute alphabet lookup table, and auto select terminating char that is 1 higher than the max alphabet used in the word list.")
    parser.add_argument("-max", "--max-alphabet", type=int, default=None, help="Max value of char, dafault to 255. Overriden when alphabet lookup is enabled.")
    parser.add_argument("-s", "--sort", action='store_true', help="Sort query results alphabetically.")
    
    opt = parser.parse_args()
    
    wordList = open(opt.path, "rb").readlines()
    wordList = list(map(lambda x:x.decode("utf-8").rstrip(), wordList))
    
    # default values
    lookup_table = None
    termChar = chr(256) # it is sufficient to be a char not used anywhere in the input word list
    
    if opt.alphabet_lookup:
        lookup_table, termChar = getAlphabetTable(wordList) # override termChar
        print(f"Terminating char value: {ord(termChar)}")
    elif opt.max_alphabet:
        opt.max_alphabet += 1 # +1 to include term char
        termChar = chr(opt.max_alphabet)
    
    print("Initializing Generalized Suffix Tree")
    gst = GeneralizedSuffixTree(wordList, termChar=termChar, alphabetMax=opt.max_alphabet, alphabetLookup=lookup_table, case_sensitive=opt.case_sensitive,print_progress=opt.print_progress)
    
    #test(wordList, gst)
    #exit()
    
    # to check if alphabet in query is also in wordList; or within the specified max alphabet
    verify_alphabet = lambda query: all(map(lambda x:ord(x) in lookup_table, query))
    verify_max = lambda query: all(map(lambda x:ord(x) <= opt.max_alphabet, query))
    
    while True:
        query = input("Enter search query: ")
        if not opt.case_sensitive:
            query = query.lower()
        os.system('cls')
        print("Query:", query)
        
        verifier = verify_alphabet if opt.alphabet_lookup else verify_max
        
        if verifier(query): # only search if all char in query are in the alphabet table or within the limit of specified max_alphabet
            match = matchSubstring(wordList, gst, query)
        else:
            match = [] # contains char not found in wordList alphabet or within the limit, so immediately returns no result
            
        if opt.sort:
            match.sort()
        
        for word,start in match:
            end = start + len(query)
            printHighlight(word, start, end)
        print("\nTotal", len(match))
        