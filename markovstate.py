import time

import tokenise
import markov
import fileinput


class MarkovStateError(Exception):
    def __init__(self, value):
        self.value = value


class MarkovState:
    """Class to keep track of a markov generator in progress.
    """
    COLORS = ["\033[0;31m", "\033[0;32m", "\033[0;34m"]
    NONE = ""
    RESET = "\033[0m"

    def __init__(self):
        self.markov = None
        self.generator = None
        self.colors = {}
        self.last_path = None

    def generate(self, chunks, seed=None, prob=0, offset=0, cln=None,
                 startf=lambda t: True, endchunkf=lambda t: True,
                 kill=0, prefix=()):
        """Generate some output, starting anew. Then save the state of the
           generator so it can be resumed later.

           :param chunks: The number of chunks to generate.
           :param seed: The random seed. If not given, use system time.
           :param prob: The probability of random token substitution.
           :param offset: The number of tokens to discard from the start.
           :param cln: The n value to use after the end of a clause.
           :param startf: Only start outputting after a token for thich this is
                          True is produced.
           :param endchunkf: End a chunk when a token for which this is True
                             is produced.
           :param kill: Drop this many tokens from the end of the output,
                        after finishing.
           :param prefix: Prefix to seed the Markov chain with.
           """

        if self.markov is None:
            raise MarkovStateError("No markov chain loaded!")

        if seed is None:
            seed = int(time.time())
            print("Warning: using seed {}".format(seed))

        if len(prefix) > self.markov.n:
            print("Warning: truncating prefix")
            prefix = prefix[self.markov.n - 1:]

        self.markov.reset(seed, prob, prefix, cln)
        
        for i in range(offset):
            next(self.markov)
        while not startf(next(self.markov)):
            pass

        def gen(n):
            out = []
            while n > 0:
                tok = next(self.markov)
                out.append("%s%s" % (self.color(self.sources[tok]), tok))
                if endchunkf(tok):
                    n -= 1
            return(' '.join(out if not kill else out[:-kill]))

        self.generator = gen
        return self.generator(chunks)

    def more(self, chunks=1):
        """Generate more chunks of output, using the established generator.
        """

        if self.generator is None:
            raise MarkovStateError("No generator to resume!")

        return self.generator(chunks)

    def train(self, n, paths, noparagraphs=False):
        """Train a new markov chain, overwriting the existing one.
        """
        def charinput(path):
            with fileinput.input(path) as fi:
                for line in fi:
                    for char in line:
                        yield char

        self.markov = markov.Markov(n)
        print(paths)
        for path in paths:
            training_data = tokenise.Tokeniser(stream=charinput(path),
                                               noparagraphs=noparagraphs)

            self.markov.train(path, training_data)
        self.sources = {k: sorted(list(v)) for k, v in self.markov.sources.items()}
        self.generator = None

    def color(self, paths):
        # Don't color it if it's not unique
        if len(paths) > 1 and self.last_path in paths:
            return self.NONE

        path = paths[0]
        self.last_path = path
        if path in self.colors:
            return self.colors[path]
        else:
            self.colors[path] = self.COLORS.pop()
            return self.colors[path]

    def load(self, filename):
        """Load a markov chain from a file.
        """

        self.generator = None
        self.markov = markov.Markov()
        self.markov.load(filename)

    def dump(self, filename):
        """Dump a markov chain to a file.
        """

        if self.markov is None:
            raise MarkovStateError("No markov chain loaded!")

        self.markov.dump(filename)
