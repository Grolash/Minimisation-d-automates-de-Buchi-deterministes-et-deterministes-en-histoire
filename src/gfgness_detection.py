from itertools import combinations

from ortools.sat.python import cp_model

from src.nga import NGA


def powerset(s):
    return frozenset(frozenset(comb) for r in range(len(s) + 1) for comb in combinations(s, r))

class Game:
    def __init__(self, reference_ntga : NGA, maxtokens):
        self.reference_ntga = reference_ntga
        self.maxtokens = maxtokens
        self.model = cp_model.CpModel()

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
                        for state in transitions:
                            self.strategy_variables[(p, q1, q2, a, state)] = self.model.new_bool_var(f'strategy_{p.id}_{q1.id}_{q2.id}_{a}_{state.id}')
                    q1_primes = p.transitions.get(a, [])
                    for q1_prime in q1_primes:
                        q2_primes = p.transitions.get(a, [])
                        for q2_prime in q2_primes:
                            p_primes = p.transitions.get(a, [])
                            for p_prime in p_primes:
                                self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)] = self.model.new_bool_var(f'path_{p.id}_{p_prime.id}_{q1.id}_{q1_prime.id}_{q2.id}_{q2_prime.id}')
        self.rank = {}
        self.solver = cp_model.CpSolver()
        self.status = None



    """
    Among all transition targets for letter a, choose one.
    """
    def strategy_choice(self):
        for p in self.reference_ntga.states:
            for q1 in self.reference_ntga.states:
                for q2 in self.reference_ntga.states:
                    for a in self.reference_ntga.alphabet:
                        states = p.transitions.get(a, [])
                        if len(states) > 0:
                            self.model.add_exactly_one(self.strategy_variables[(p, q1, q2, a, state)] for state in states)

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
                        p_primes = p.transitions.get(a, [])
                        for p_prime in p_primes:
                            self.model.add(self.position_variables[(p_prime, q1, q2, a, "Adam")] == True).only_enforce_if(
                                self.position_variables[(p, q1, q2, a, "Eve")],
                                self.strategy_variables[(p, q1, q2, a, p_prime)]
                            )
                            self.rank[p_prime, q1, q2] = max(self.rank[p, q1, q2], 2 if p_prime.is_accepting else 0)


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

        for p in self.reference_ntga.states:
            for a in self.reference_ntga.alphabet:
                for q1 in self.reference_ntga.states:
                    q1_primes = q1.transitions.get(a, [])
                    for q1_prime in q1_primes:
                        for q2 in self.reference_ntga.states:
                            q2_primes = q2.transitions.get(a, [])
                            for q2_prime in q2_primes:
                                for b in self.reference_ntga.alphabet:
                                    position_variable = self.position_variables[(p, q1_prime, q2_prime, b, "Eve")]
                                    self.model.add(position_variable == True).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")]
                                    )
                                self.rank[p, q1_prime, q2_prime] = max(self.rank[p, q1, q2], 1 if (q1.is_accepting or q2.is_accepting) else 0)

    """
    computing paths
    """
    def pathing(self):
        self.model.add(self.path_variables[(self.reference_ntga.states[0], self.reference_ntga.states[0],
                                            self.reference_ntga.states[0], self.reference_ntga.states[0],
                                            self.reference_ntga.states[0], self.reference_ntga.states[0])] == True)

        for a in self.reference_ntga.alphabet:
            for q1 in self.reference_ntga.states:
                for q1_prime in self.reference_ntga.states:
                    for q2 in self.reference_ntga.states:
                        for q2_prime in self.reference_ntga.states:
                            for p in self.reference_ntga.states:
                                for p_prime in self.reference_ntga.states:
                                    for p_seconde in self.reference_ntga.states:
                                        self.model.add(self.path_variables[(p, p_seconde, q1, q1_prime, q2, q2_prime)] == True).only_enforce_if(
                                            self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)],
                                            self.position_variables[(p_prime, q1_prime, q2_prime, a, "Eve")],
                                            self.position_variables[(p_seconde, q1_prime, q2_prime, a, "Adam")]
                                        )
                                    for q1_seconde in self.reference_ntga.states:
                                        for q2_seconde in self.reference_ntga.states:
                                            for b in self.reference_ntga.alphabet:
                                                self.model.add(self.path_variables[(p, p_prime, q1, q1_seconde, q2, q2_seconde)] == True).only_enforce_if(
                                                    self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)],
                                                    self.position_variables[(p_prime, q1_prime, q2_prime, a, "Adam")],
                                                    self.position_variables[(p_prime, q1_seconde, q2_seconde, b, "Eve")]
                                                )

    def cycle_closing(self):
        for a in self.reference_ntga.alphabet:
            for q1 in self.reference_ntga.states:
                for q1_prime in self.reference_ntga.states:
                    for q2 in self.reference_ntga.states:
                        for q2_prime in self.reference_ntga.states:
                            for p in self.reference_ntga.states:
                                for p_prime in self.reference_ntga.states:
                                    self.model.add(self.rank[p, q1_prime, q2_prime] == 2 or self.rank[p, q1_prime, q2_prime] == 0).only_enforce_if(
                                        self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)],
                                        self.position_variables[(p_prime, q1_prime, q2_prime, a, "Eve")],
                                        self.position_variables[(p, q1_prime, q2_prime, a, "Adam")]
                                    )

    def solve(self):
        self.strategy_choice()
        self.eve_adam_sequence()
        self.adam_eve_sequence()
        self.pathing()
        self.cycle_closing()
        self.status = self.solver.Solve(self.model)
        return self.status == cp_model.OPTIMAL

    def get_solution(self):
        if self.status == cp_model.OPTIMAL:
            print("Solution found:")
            for p in self.reference_ntga.states:
                for q1 in self.reference_ntga.states:
                    for q2 in self.reference_ntga.states:
                        for a in self.reference_ntga.alphabet:
                            if self.solver.Value(self.position_variables[(p, q1, q2, a, "Adam")]) == 1:
                                print(f"Position: --{a}--> {p.id} {q1.id} {q2.id} (Adam)")
                            if self.solver.Value(self.position_variables[(p, q1, q2, a, "Eve")]) == 1:
                                print(f"Position: --{a}--> {p.id} {q1.id} {q2.id} (Eve)")
            for p in self.reference_ntga.states:
                for q1 in self.reference_ntga.states:
                    for q2 in self.reference_ntga.states:
                        print(f"Rank: {p.id} {q1.id} {q2.id} = {self.solver.Value(self.rank_variables[(p, q1, q2)])}")


if __name__ == "__main__":
    pass





