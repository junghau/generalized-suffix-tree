from highlighter import printHighlight
from collections import defaultdict
from tqdm import tqdm
import functools

def compose(*functions):
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions, lambda x: x)

mapl = lambda f,x: list(map(f,x))

class SuffixTreeNode:

    class SuffixOrigin: # NOTE: GST extension
        def __init__(self, wordID, suffixIndex, nextSuffixOrigin=None):
            """
            @param wordID: the word index from a wordlist
            @param istart: start index of the suffix in the word
            """
            self.wordID = wordID
            self.suffixIndex = suffixIndex
            self.next = nextSuffixOrigin # implemented as linked list

    # used so that list[x] becomes list[lookup_table[x]]
    class LookupList:
        def __init__(self, lookup_table):
            self.list = [None] * len(lookup_table)
            self.lookup_table = lookup_table
        def __len__(self):
            return len(self.list)
        def __getitem__(self, key):
            return self.list[self.lookup_table[key]]
        def __setitem__(self, key, new_val):
            self.list[self.lookup_table[key]] = new_val


    def __init__(self, wordID=None, istart=None, iend=None, isLeaf=False, suffixIndex=None, alphabetMax=255, alphabetLookup=None):
        self.istart = istart
        self.iend = iend    # None for leaf since we know the value is the last index of the input txt in the end
        self.link = None    # only internal node (non-root and non-leaf) has link, # optional: root node link yo itself
        self.children = None #{} # each child/branch starts with different char
        self.suffixOrigin = SuffixTreeNode.SuffixOrigin(wordID, suffixIndex) # NOTE: GST extension # head of linked list
        self.alphabetMax = alphabetMax # Max value of alphabet in string. If None, then use defaultdict which is useful for sparse alphabet
        self.alphabetLookup = alphabetLookup # lookup table in the form {ord(char):index}, where 0 <= index < alphabet_size

        # the istart and iend correspond to the first wordID in suffixOrigin,
        # so the first should be maintained in head, and append the rest to the tail
        self._lastSuffixOrigin = self.suffixOrigin # NOTE: GST extension # tail of linked list

        self._childlist = [] # stores usable index in children for faster iteration

        # Only applicable to leaf node,
        # Which means that suffix is settled,
        #   and will always remain as leaf node
        # self.suffixIndex = suffixIndex

        # Only allocate memory to store children if not leaf, because A LEAF IS ALWAYS A LEAF
        if not isLeaf:
            if alphabetLookup:
                self.children = SuffixTreeNode.LookupList(alphabetLookup) # takes up slightly less memory compared to defaultdict
            elif self.alphabetMax is None:
                self.children = defaultdict(lambda:None)
            else:
                self.children = [None] * (self.alphabetMax + 1) # most efficient but depends on the sparseness of alphabet, +1 to access at alphabetMax index

    def isRoot(self):
        return (self.istart is None) and (self.iend is None)
    def isLeaf(self):
        return self.children is None
    def hasLink(self):
        return self.link is not None
    def hasChild(self, char):
        return self.getChild(char) is not None
    def getEdgeSize(self):
        return self.iend - self.istart + 1

    # to record the wordID and suffixIndex of the word that the current suffix belongs to in the leaf
    def addSuffixOrigin(self, wordID, suffixIndex): # NOTE: GST extension
        if not self.isLeaf():
            return
        newSuffixOrigin = SuffixTreeNode.SuffixOrigin(wordID, suffixIndex)
        self._lastSuffixOrigin.next = newSuffixOrigin
        self._lastSuffixOrigin = newSuffixOrigin

    ## child management functions

    # access child by char
    def getChild(self, char):
        if self.isLeaf():
            return None
        else:
            return self.children[ord(char)]

    def setChild(self, char, newChild):
        if not self.isLeaf():
            if self.children[ord(char)] is None:
                self._childlist.append(ord(char)) # based on the idea that child will only get added, never deleted
            self.children[ord(char)] = newChild

    def getChildren(self):
        return map(lambda x:self.children[x], self._childlist)
        # return filter(lambda x:x is not None, self.children)

    """
    # enable the use of square brackets to access and modify its child
    def __getitem__(self, char):
        return self.getChild(char)
    def __setitem__(self, char, newChild):
        self.setChild(char, newChild)
    """

class GeneralizedSuffixTree:

    def __init__(self, wordList, termChar="$", alphabetMax=None, alphabetLookup=None, case_sensitive=False, print_progress=False):
        self.print_progress = print_progress
        self.alphabetMax = alphabetMax
        self.alphabetLookup = alphabetLookup

        appendTermChar = lambda s:s+termChar if s[-1] != termChar else s
        convertCase = (lambda s:s) if case_sensitive else (lambda s:s.lower())
        self.preprocess = lambda s: convertCase(appendTermChar(s))

        self.wordList = mapl(self.preprocess, wordList)
        self.termChar = termChar
        self.root = SuffixTreeNode(alphabetMax=self.alphabetMax, alphabetLookup=alphabetLookup)
        self.root.link = self.root # root link to itself
        for word_index in tqdm(range(len(self.wordList))):
            self._add(word_index)
            # print(self.wordList[word_index])

    def _getMatch(self, startNode, result_accumulator):
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

    def match(self, pattern, ret_match_index=False):
        """
        Match the substring pattern with all words in the Generalized Suffix Tree
        @param pattern: substring pattern to match the words in the tree
        @param ret_match_index: Whether the output should include the starting index
                of each word that matches the pattern
        @return: list of words that contains the pattern substring in the tree:
                either [word,...], or [(word, match_index),...]

        Phase 1: traverse to node corresponding to the pattern
        Phase 2: search all leaves from that node recursively to get match
        """
        if pattern == "" or pattern == self.termChar:
            return []

        ### Phase 1 ###
        currNode = self.root
        pWordList = self.wordList # preprocessed word list by GST
        i = 0
        while i < len(pattern):
            c = pattern[i]
            if currNode.hasChild(c):
                currNode = currNode.getChild(c)
                edgeSize = currNode.getEdgeSize()
                wordID = currNode.suffixOrigin.wordID
                istart = currNode.istart

                cmplen = min(len(pattern) - i, edgeSize) # comparison length
                for k in range(cmplen):
                    if pattern[i+k] != pWordList[wordID][istart+k]:
                        return []
                i += cmplen
            else:
                return [] # no match

        ### Phase 2 ###
        result_dict = {}
        self._getMatch(currNode, result_dict)

        out_format = lambda x:x if ret_match_index else lambda x:x[0]
        mapfst = lambda f: lambda x:(f(x[0]), x[1])
        id2word = lambda i:self.wordList[i][:-1] # ignore the term char

        postprocess = compose(out_format, mapfst(id2word))

        # convert wordID to word from wordList, while retaining the suffixIndex
        return mapl(postprocess, result_dict.items())

    def createLeaf(self, wordID, sourceNode, istart, suffixIndex, firstChar):
        """
        Create a leaf braching from sourceNode, with end index set to the last index of the string because
        A LEAF IS ALWAYS A LEAF

        @param istart: starting index of the substring on this node
        @param suffixIndex: the suffix index represented by this leaf
        """
        lastIndex = len(self.wordList[wordID]) - 1
        leaf = SuffixTreeNode(wordID, istart, lastIndex, True, suffixIndex,
                                alphabetMax=self.alphabetMax, alphabetLookup=self.alphabetLookup)
        sourceNode.setChild(firstChar, leaf)
        return leaf

    def splitEdge(self, currNode, parentNode, conflictIndex, goodCount, suffixIndex, wordID):
        """
        A new internal node will be created between current node and its parent node

        @param conflictIndex: the index of the last char in current suffix extension [j..i], which is i
        @param goodCount: number of char before conflict happens in the current edge of node, which is i-j
        @param suffixIndex: suffix index of the new leaf to be created
        @return: newly constructed internalNode, new leaf ignored as it can care for itself,
                such that all future RULE 1 are implicitly handled
        """
        currWord = self.wordList[wordID]
        existingWord = self.wordList[currNode.suffixOrigin.wordID]

        # create the 2 new nodes
        internalNode = SuffixTreeNode(currNode.suffixOrigin.wordID, currNode.istart, currNode.istart + goodCount - 1,
                                        alphabetMax=self.alphabetMax, alphabetLookup=self.alphabetLookup)
        newLeaf = self.createLeaf(wordID, internalNode, conflictIndex, suffixIndex, currWord[conflictIndex])

        # link the created internal node
        parentNode.setChild(existingWord[currNode.istart], internalNode)

        # make changes to currNode and link to internal node
        currNode.istart += goodCount
        internalNode.setChild(existingWord[currNode.istart], currNode)

        return internalNode

    def walkDown(self, startNode, iend, skipCount, wordID):
        """
        Walk down from startNode and skip skipCount number of chars until the EDGE that can fit the requirement is reached.
        if skipCount > 0, then the current node will traverse to its child,
        and parentNode will definitely be updated into non-None value.
        So if skipCount is 0, then there is no need to traverse to its child.

        NOTE: skipCount excludes the char introduced in the current phase.
        @return currNode: current node after skip
        @return parentNode: not none if traversal to child has happened
        @return remainingSkip: remaining skip available after reaching the destination edge
        """
        currWord = self.wordList[wordID]

        istart = iend - skipCount
        remainingSkip = skipCount
        currNode = startNode
        parentNode = None

        # skip if necassary
        while remainingSkip > 0:

            # get child
            childNode = currNode.getChild(currWord[istart])

            childLength = childNode.getEdgeSize() # edge length

            # traverse down
            parentNode = currNode
            currNode = childNode

            if remainingSkip < childLength:
                break

            istart += childLength
            remainingSkip -= childLength

        return currNode, parentNode, remainingSkip

    def add(self, word):
        """
        !NOTE: Not working when using alphabet lookup table or with max alphabet list
        """
        word = self.preprocess(word)
        self.wordList.append(word)
        wordID = len(self.wordList) - 1
        self._add(wordID)

    def _add(self, wordID):
        """
        Append a new word using its index to the Generalized Suffix Tree with Ukkonen's Algorithm
        """
        #txt = self.wordList[wordID]
        currWord = self.wordList[wordID]
        n = len(currWord)

        # initialize extension istart value
        istart = 0

        # newly created internal node, which obviously has no outgoing link,
        # and is awaiting to be linked up in the following extension of its creation
        nodeToLink = None

        currNode = self.root
        skipCount = 0

        nextSkipCount = 0

        # phase iend
        for iend in range(n):

            # extension istart
            while istart <= iend:
                if self.print_progress:
                    printHighlight(self.wordList[wordID], istart, iend+1)

                suffixIndex = istart # for readability

                if currNode.isRoot():
                    skipCount = iend - istart

                currNode, parentNode, remainingSkip \
                    = self.walkDown(currNode, iend, skipCount, wordID)

                ## WE HAVE REACHED THE DESIRED EDGE FROM THIS POINT ONWARDS ##

                # the index of char we want to see if matches with the one on the edge
                queryIndex = iend

                newInternalNode = None

                termCharReached = iend == n-1

                if remainingSkip == 0:
                    targetFirstChar = currWord[queryIndex]
                    if not currNode.hasChild(targetFirstChar):
                        self.createLeaf(wordID, currNode, queryIndex, suffixIndex, targetFirstChar)
                        nextSkipCount = 0 # not walked up one edge, so nothing to skip
                    elif termCharReached: # NOTE: GST extension
                        # Identical suffixes of different words encountered, add the new wordID to the leaf
                        # CASE 1: terminating node at child
                        termNode = currNode.getChild(targetFirstChar) # targetFirstChar is terminating char
                        termNode.addSuffixOrigin(wordID, suffixIndex)
                        nextSkipCount = 0
                    else:
                        nextSkipCount = 1 # RULE 3
                else:
                    # actual index of char on the edge
                    edgeIndex = currNode.istart + remainingSkip
                    existingWord = self.wordList[currNode.suffixOrigin.wordID]

                    # split edge if char at query index mismatch with the one present in the edge
                    if currWord[queryIndex] != existingWord[edgeIndex]:
                        newInternalNode = self.splitEdge(currNode, parentNode, queryIndex, remainingSkip, suffixIndex, wordID)
                        nextSkipCount = newInternalNode.getEdgeSize() # newInternalNode.iend - newInternalNode.istart + 1
                    elif termCharReached: # NOTE: GST extension
                        # Identical suffixes of different words encountered, add the new wordID to the leaf
                        # CASE 2: current node is terminating node
                        termNode = currNode # terminating node contains terminating char
                        termNode.addSuffixOrigin(wordID, suffixIndex)
                        nextSkipCount = termNode.getEdgeSize() - 1 # -1 to exlude the terminating char, as if split with term char happened
                    else:
                        nextSkipCount = remainingSkip + 1 # RULE 3

                    #   If nothing is done due to RULE 3, then go back to its parent
                    ##
                    # HOWEVER if branching (splitting) has happened, then the new internal node
                    #   has no outgoing link, so might as well walking up ONE edge, which is its parent node
                    #   that definitely has a link since it must have linked up in the following extension
                    #   after it has been created
                    currNode = parentNode # this allows us to guarantee linkableNode has link

                if nodeToLink:
                    nodeToLink.link = newInternalNode if newInternalNode else currNode
                nodeToLink = newInternalNode # update nodeToLink

                skipCount = nextSkipCount

                # is RULE2
                if skipCount == 0 or newInternalNode or termCharReached: # NOTE: GST extension
                    currNode = currNode.link # go across link
                    istart += 1 # increment extension
                else: # is RULE 3
                    break


def getAlphabetTable(wordList):
    """
    Get the alphabet used in txt to speed up suffix tree traversal
    """
    alphaUsed = {ord(c) for txt in wordList for c in txt}
    termChar = max(alphaUsed) + 1
    alphaUsed.add(termChar)
    termChar = chr(termChar)
    table = dict(zip(sorted(alphaUsed), range(len(alphaUsed))))
    #print("Alphabet size:", len(alphaUsed), table)
    return table, termChar
