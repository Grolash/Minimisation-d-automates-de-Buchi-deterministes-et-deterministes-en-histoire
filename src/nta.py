class NTA:
    class Transition:
        def __init__(self, source, symbol: str, target, accepting: bool = False):
            self.source = source # TGA.State
            self.symbol = symbol
            self.target = target # TGA.State
            # Which acceptance sets this transition belongs to (e.g. {0, 2})
            self.is_accepting = accepting # Acc(q_1', l, q_2')

        def __repr__(self):
            return (f'{self.source.id} --{self.symbol}--> {self.target.id}: '
                    f'{"accepting" if self.is_accepting else "non-accepting"}')

    class State:
        def __init__(self, id: str):
            self.id = id
            self.transitions : dict[str, list[NTA.Transition]] = {}

        def add_transition(self, symbol: str, target, accepting: bool = False):
            transition = NTA.Transition(self, symbol, target, accepting)
            if symbol in self.transitions.keys():
                self.transitions[symbol].append(transition)
            else:
                self.transitions[symbol] = [transition]

        def successors(self):
            return list(set(transition.target for transitionlist in self.transitions.values() for transition in transitionlist))

        def __str__(self):
            return self.id

    def __init__(self, num_acceptance_sets: int = 1):
        self.states : list[NTA.State] = []
        self.alphabet : set[str] = set()
        self.num_acceptance_sets : int = num_acceptance_sets

    def add_state(self, state: State):
        self.states.append(state)

    def size(self):
        return len(self.states)

    def __str__(self):
        return str(self.states)

    def __repr__(self):
        for state in self.states:
            print(f'{state.id}')
            for transitionlist in state.transitions.values():
                for transition in transitionlist:
                    acceptance_info = " (accepting)" if transition.is_accepting else " (non-accepting)"
                    print(f'  --{transition.symbol}--> {transition.target.id}{acceptance_info}')


if __name__ == "__main__":
    pass