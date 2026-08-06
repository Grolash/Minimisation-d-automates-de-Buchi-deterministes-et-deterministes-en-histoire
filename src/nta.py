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

    def add_state(self, state: State):
        self.states.append(state)

    def size(self):
        return len(self.states)

    def completed(self):
        for state in self.states:
            for symbol in self.alphabet:
                transitions = state.transitions.get(symbol, [])
                if len(transitions) == 0:
                    return False
        return True

    def complete(self):
        if not self.completed():
            dump_state = NTA.State('dump')
            self.add_state(dump_state)
            for state in self.states:
                for symbol in self.alphabet:
                    transitions = state.transitions.get(symbol, [])
                    if len(transitions) == 0:
                        state.add_transition(symbol, dump_state)

    def get_transitions(self):
        transitions = []
        for state in self.states:
            for transitionlist in state.transitions.values():
                for transition in transitionlist:
                    transitions.append(transition)
        return transitions


    def __str__(self):
        return str(self.states)

    def __repr__(self):
        for state in self.states:
            print(f'{state.id}')
            for transitionlist in state.transitions.values():
                for transition in transitionlist:
                    acceptance_info = " (accepting)" if transition.is_accepting else " (non-accepting)"
                    print(f'  --{transition.symbol}--> {transition.target.id}{acceptance_info}')

    def to_na(self):
        from na import NA

        na = NA()
        na.alphabet = self.alphabet.copy()

        transition_to_state = {}
        for transition in self.get_transitions():
            state = NA.State(
                f"{transition.source.id} -{transition.symbol}-> {transition.target.id}"
            )
            state.is_accepting = transition.is_accepting
            transition_to_state[transition] = state
            na.add_state(state)

        initial = NA.State("init")
        na.add_state(initial)
        if len(self.states) == 0:
            return na

        nta_initial = self.states[0]
        # Initial state's outgoing transitions
        for symbol, transitions in nta_initial.transitions.items():
            for transition in transitions:
                initial.add_transition(symbol, transition_to_state[transition])

        for transition in self.get_transitions():
            current = transition_to_state[transition]
            for symbol, next_transitions in transition.target.transitions.items():
                for next_transition in next_transitions:
                    current.add_transition(
                        symbol,
                        transition_to_state[next_transition]
                    )

        return na




if __name__ == "__main__":
    GFG_nta = NTA()
    GFG_nta.alphabet = {'a', 'b', 'x'}
    i = NTA.State('i')
    a = NTA.State('a')
    a_prime = NTA.State('a_prime')
    a_seconde = NTA.State('a_seconde')
    b = NTA.State('b')
    b_prime = NTA.State('b_prime')
    b_seconde = NTA.State('b_seconde')
    i.add_transition('x', a)
    a.add_transition('b', i)
    a.add_transition('a', a_prime)
    a_prime.add_transition('x', a_seconde)
    a_seconde.add_transition('b', b_prime)
    a_seconde.add_transition('a', i, True)
    i.add_transition('x', b)
    b.add_transition('a', i)
    b.add_transition('b', b_prime)
    b_prime.add_transition('x', b_seconde)
    b_seconde.add_transition('a', a_prime)
    b_seconde.add_transition('b', i, True)
    GFG_nta.add_state(i)
    GFG_nta.add_state(a)
    GFG_nta.add_state(a_prime)
    GFG_nta.add_state(a_seconde)
    GFG_nta.add_state(b)
    GFG_nta.add_state(b_prime)
    GFG_nta.add_state(b_seconde)
    GFG_nta.complete()
    GFG_na = GFG_nta.to_na()
    GFG_na.__repr__()
    print(f"GFG NTA has {GFG_nta.size()} states and {len(GFG_nta.get_transitions())} transitions.")
    print(f"GFG NA has {GFG_na.size()} states and {len(GFG_na.get_transitions())} transitions.")