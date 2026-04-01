from itertools import combinations

from ortools.sat.python import cp_model

from src.ntga import NTGA


def powerset(s):
    return frozenset(frozenset(comb) for r in range(len(s) + 1) for comb in combinations(s, r))

class Game:
    def __init__(self, reference_ntga : NTGA, maxtokens):
        self.reference_ntga = reference_ntga
        self.maxtokens = maxtokens
        self.model = cp_model.CpModel()
        self.f_r = frozenset(range(reference_ntga.num_acceptance_sets))
        self.fs = powerset(self.f_r)

        self.position_variables = {}
        self.strategy_variables = {}
        self.rank_variables = {}
        self.path_variables = {}
        for p in self.reference_ntga.states:
            for q1 in self.reference_ntga.states:
                for q2 in self.reference_ntga.states:
                    self.rank_variables[(p, q1, q2)] = self.model.new_int_var(0, 2, f'rank_{p.id}_{q1.id}_{q2.id}')
                    for a in self.reference_ntga.alphabet:
                        self.position_variables[(p, q1, q2, a, "Adam")] = self.model.new_bool_var(f'position_{p.id}_{q1.id}_{q2.id}_{a}_{"Adam"}')
                        self.position_variables[(p, q1, q2, a, "Eve")] = self.model.new_bool_var(f'position_{p.id}_{q1.id}_{q2.id}_{a}_{"Eve"}')
                        transitions = p.transitions.get(a, [])
                        for transition in transitions:
                            self.strategy_variables[(p, q1, q2, a, transition.target)] = self.model.new_bool_var(f'strategy_{p.id}_{q1.id}_{q2.id}_{a}_{transition.target.id}')
                    for f1 in self.fs:
                        for f2 in self.fs:
                            for f3 in self.fs:
                                self.path_variables[(p, q1, q2, f1, f2, f3)] = self.model.new_bool_var(f'path_{p.id}_{q1.id}_{q2.id}_{f1}_{f2}_{f3}')


    """
    Among all transition targets for letter a, choose one.
    """
    def strategy_choice(self):
        for p in self.reference_ntga.states:
            for q1 in self.reference_ntga.states:
                for q2 in self.reference_ntga.states:
                    for a in self.reference_ntga.alphabet:
                        transitions = p.transitions.get(a, [])
                        if len(transitions) > 0:
                            self.model.add_exactly_one(self.strategy_variables[(p, q1, q2, a, transition.target)] for transition in transitions)

    """
    Eve chooses the transition given by her strategy for symbol a at position p; transition.target is p' in formula
    => p' = strategy(p, q1, q2, a); i.e., strategy(p, q1, q2, a, p') = True
    => (p', q1, q2, a, Adam) is true if (p, q1, q2, a, Eve) is true and strategy(p, q1, q2, a) = p'
    """
    def eve_adam_sequence(self):
        for p in self.reference_ntga.states:
            for q1 in self.reference_ntga.states:
                for q2 in self.reference_ntga.states:
                    for a in self.reference_ntga.alphabet:
                        transitions = p.transitions.get(a, [])
                        for transition in transitions:
                            self.model.add(self.position_variables[(transition.target, q1, q2, a, "Adam")] == True).only_enforce_if(
                                self.position_variables[(p, q1, q2, a, "Eve")],
                                self.strategy_variables[(p, q1, q2, a, transition.target)]
                            )


    """
    Adam chooses a starting letter a and the Eve tuple (q0, q0, q0, a, Eve) is true for that a;
    => considering, for all symbols a in Alphabet, the (q0, q0, q0, a, Eve) position variables, exactly one is true.
    
    Adam chooses a q1' and a q2' such that they are reachable from, respectively, q1 and q2 by letter a, 
    and (p, q1, q2, a, Eve) is true.
    Adam also chooses a letter b.
    => for all p, q1, q2 in Q, and a in Alphabet,
    for all q1', q2' reachable from q1 and q2 respectively by letter a,
    for all b in Alphabet,
    among all (p, q1', q2', b, Eve) tuples, exactly one is true.
    If the (p, q1, q2, a, Adam) tuple is false, then (p, q1', q2', b, Eve) is false;
    i.e., the (p, q1', q2', b, Eve) chosen to be true is among the ones with (p, q1, q2, a, Adam) true.
    """
    def adam_eve_sequence(self):
        a_variables = []
        start_state = self.reference_ntga.states[0]
        for a in self.reference_ntga.alphabet:
            a_variables.append(self.position_variables[(start_state, start_state, start_state, a, "Eve")])
        self.model.add_exactly_one(a_variables) # Adam chooses a starting letter

        eve_variables = []
        for p in self.reference_ntga.states:
            for a in self.reference_ntga.alphabet:
                for q1 in self.reference_ntga.states:
                    q1_primes_transitions = p.transitions.get(a, [])
                    for q1_prime_transition in q1_primes_transitions:
                        q1_prime = q1_prime_transition.target
                        for q2 in self.reference_ntga.states:
                            q2_primes_transitions = p.transitions.get(a, [])
                            for q2_prime_transition in q2_primes_transitions:
                                q2_prime = q2_prime_transition.target
                                for b in self.reference_ntga.alphabet:
                                    position_variable = self.position_variables[(p, q1_prime, q2_prime, b, "Eve")]
                                    eve_variables.append(position_variable)
                                    self.model.add(position_variable == False).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")].Not()
                                    )
        self.model.add_exactly_one(eve_variables)

    """
    computing path acceptance set transitively
    """
    def pathing(self):
        self.model.add(self.path_variables[(self.reference_ntga.states[0], self.reference_ntga.states[0],
                                            self.reference_ntga.states[0], frozenset(), frozenset(),
                                            frozenset())] == True)

        for a in self.reference_ntga.alphabet:
            for p in self.reference_ntga.states:
                p_transitions = p.transitions.get(a, [])
                for p_transition in p_transitions:
                    p_prime = p_transition.target
                    p_transition_acceptance_sets = p_transition.acceptance_sets
                    for q1 in self.reference_ntga.states:
                        for q2 in self.reference_ntga.states:
                            for f1 in self.fs:
                                for f2 in self.fs:
                                    for f3 in self.fs:
                                        self.model.add(self.path_variables[(p_prime, q1, q2, frozenset(
                                            f1.union(p_transition_acceptance_sets)), f2, f3)] == True).only_enforce_if(
                                            self.path_variables[(p, q1, q2, f1, f2, f3)],
                                            self.position_variables[(p, q1, q2, a, "Eve")],
                                            self.position_variables[(p_prime, q1, q2, a, "Adam")]
                                        )

                for q1 in self.reference_ntga.states:
                    q1_transitions = p.transitions.get(a, [])
                    for q1_transition in q1_transitions:
                        q1_prime = q1_transition.target
                        q1_transition_acceptance_sets = q1_transition.acceptance_sets
                        for q2 in self.reference_ntga.states:
                            q2_transitions = p.transitions.get(a, [])
                            for q2_transition in q2_transitions:
                                q2_prime = q2_transition.target
                                q2_transition_acceptance_sets = q2_transition.acceptance_sets
                                for f1 in self.fs:
                                    for f2 in self.fs:
                                        for f3 in self.fs:
                                            self.model.add(self.path_variables[(p, q1_prime, q2_prime, f1,
                                                                                frozenset(f2.union(q1_transition_acceptance_sets)),
                                                                                frozenset(f3.union(q2_transition_acceptance_sets)))]
                                                           == True).only_enforce_if(
                                                self.path_variables[(p, q1, q2, f1, f2, f3)],
                                                self.position_variables[(p, q1, q2, a, "Adam")],
                                                self.position_variables[(p, q1_prime, q2_prime, a, "Eve")],
                                            )

    # TODO: close path and determine max rank of cycle: 2 if f1 = f_r, 1 if f2 = f_r or f3 = f_r, 0 otherwise




