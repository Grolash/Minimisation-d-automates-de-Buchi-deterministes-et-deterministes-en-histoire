class Automaton:
    class State:
        def __init__(self, id: str):
            self.id : str = id
            self.transitions : dict[str, Automaton.State] = {}
            self.is_accepting : bool = False

        def add_transition(self, symbol: str, target):
            self.transitions[symbol] = target

        def __str__(self):
            return self.id

    def __init__(self):
        self.states : list[Automaton.State] = []
        self.alphabet : set[str] = set()

    def add_state(self, state: State):
        self.states.append(state)

    def size(self):
        return len(self.states)

    def __str__(self):
        return str(self.states)

    def __repr__(self):
        for state in self.states:
            print(f'{state.id} ({"accepting" if state.is_accepting else "non-accepting"})')
            for symbol, target in state.transitions.items():
                print(f'  --{symbol}--> {target.id}')


if __name__ == "__main__":
    reference_automaton = Automaton()
    q0 = Automaton.State('q0')
    q1 = Automaton.State('q1')
    q2 = Automaton.State('q2')
    q3 = Automaton.State('q3')
    q0.is_accepting = True
    q1.is_accepting = True
    q0.add_transition('a', q1)
    q0.add_transition('b', q2)
    q1.add_transition('a', q3)
    q1.add_transition('b', q0)
    q2.add_transition('a', q1)
    q2.add_transition('b', q2)
    q3.add_transition('a', q3)
    q3.add_transition('b', q0)
    reference_automaton.add_state(q0)
    reference_automaton.add_state(q1)
    reference_automaton.add_state(q2)
    reference_automaton.add_state(q3)
    reference_automaton.alphabet = {'a', 'b'}
    print(reference_automaton.__repr__())