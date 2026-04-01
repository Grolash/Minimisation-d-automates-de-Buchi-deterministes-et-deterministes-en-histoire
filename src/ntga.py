class NTGA:
    class Transition:
        def __init__(self, source, symbol: str, target, acceptance_sets: set[int] = None):
            self.source = source # TGA.State
            self.symbol = symbol
            self.target = target # TGA.State
            # Which acceptance sets this transition belongs to (e.g. {0, 2})
            self.acceptance_sets: frozenset[int] = acceptance_sets or frozenset() # Acc(q_1', l, q_2')

        def __repr__(self):
            return (f'{self.source.id} --{self.symbol}--> {self.target.id}: '
                    f'{self.acceptance_sets if self.acceptance_sets else "no acceptance sets"}')

    class State:
        def __init__(self, id: str):
            self.id = id
            self.transitions : dict[str, list[NTGA.Transition]] = {}

        def add_transition(self, symbol: str, target, acceptance_sets: set[int] = None):
            transition = NTGA.Transition(self, symbol, target, acceptance_sets)
            self.transitions[symbol].append(transition)

        def successors(self):
            return list(set(transition.target for transitionlist in self.transitions.values() for transition in transitionlist))

        def __str__(self):
            return self.id

    def __init__(self, num_acceptance_sets: int = 1):
        self.states : list[NTGA.State] = []
        self.alphabet : set[str] = set()
        self.num_acceptance_sets : int = num_acceptance_sets

    def add_state(self, state: State):
        self.states.append(state)

    def size(self):
        return len(self.states)

    def scc(self):
        successors = {s : s.successors() for s in self.states}

        # Tarjan's strongly connected components algorithm
        index_counter = 0
        stack = []
        index = {}
        lowlink = {}
        on_stack = {}
        sccs = set()

        def strong_connect(v):
            nonlocal index_counter
            index[v] = lowlink[v] = index_counter
            index_counter += 1
            stack.append(v)
            on_stack[v] = True

            nonlocal successors
            for w in successors[v]:
                if w not in index:
                    strong_connect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in stack:
                    lowlink[v] = min(lowlink[v], index[w])
            if lowlink[v] == index[v]:
                scc = set()
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    scc.add(w)
                    if w == v:
                        break
                sccs.add(frozenset(scc))

        for v in self.states:
            if v not in index:
                strong_connect(v)

        return sccs

    def non_trivial_sccs(self):
        def is_non_trivial(scc):
            return len(scc) > 1 or (len(scc) == 1 and next(iter(scc)).successors() == [next(iter(scc))])

        return set(filter(is_non_trivial, self.scc()))

    def __str__(self):
        return str(self.states)

    def __repr__(self):
        for state in self.states:
            print(f'{state.id}')
            for transitionlist in state.transitions.values():
                for transition in transitionlist:
                    acceptance_info = f" (acceptance sets: {transition.acceptance_sets})" if transition.acceptance_sets else ""
                    print(f'  --{transition.symbol}--> {transition.target.id}{acceptance_info}')


if __name__ == "__main__":
    pass