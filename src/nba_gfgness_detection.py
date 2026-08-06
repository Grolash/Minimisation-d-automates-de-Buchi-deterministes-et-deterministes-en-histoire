from ortools.sat.python import cp_model

from src.na import NA

class Game:
    def __init__(self, na: NA):
        self.na = na
        self.model = cp_model.CpModel()

        self.position_variables = {}
        self.edge_variables = {}
        self.path_variables = {}
        for p in self.na.states:
            for q1 in self.na.states:
                for q2 in self.na.states:
                    for a in self.na.alphabet:
                        self.position_variables[(p, q1, q2, a, "Adam")] = self.model.new_bool_var(
                            '')
                        self.position_variables[(p, q1, q2, a, "Eve")] = self.model.new_bool_var(
                            '')
                        p_primes: list[NA.State] = p.transitions.get(a, [])
                        for p_prime in p_primes:
                            self.edge_variables[(p, q1, q2, a, "Eve", p_prime)] = self.model.new_bool_var(
                                ''
                                )
                    for q1_prime in self.na.states:
                        for q2_prime in self.na.states:
                            for p_prime in self.na.states:
                                for a in self.na.alphabet:
                                    for b in self.na.alphabet:
                                        for player in ["Adam", "Eve"]:
                                            self.path_variables[
                                                (p, q1, q2, a, p_prime, q1_prime, q2_prime, b, player, 0)] = self.model.new_bool_var(
                                                '')
                                            self.path_variables[
                                                (p, q1, q2, a, p_prime, q1_prime, q2_prime, b, player, 1)] = self.model.new_bool_var(
                                                '')
                                            self.path_variables[
                                                (p, q1, q2, a, p_prime, q1_prime, q2_prime, b, player, 2)] = self.model.new_bool_var(
                                                '')

        self.solver = cp_model.CpSolver()
        self.status = None

    def eve_strategy(self):
        for p in self.na.states:
            for a in self.na.alphabet:
                for q1 in self.na.states:
                    for q2 in self.na.states:
                        p_primes: list[NA.State] = p.transitions.get(a, [])
                        strategy_variables = [self.edge_variables[(p, q1, q2, a, "Eve", p_prime)] for p_prime in p_primes]
                        self.model.add_exactly_one(strategy_variables).only_enforce_if(self.position_variables[(p, q1, q2, a, "Eve")])

    """
    Eve chooses the transition given by her strategy for symbol a at position p; transition.target is p' in formula
    => p' = strategy(p, q1, q2, a); i.e., strategy(p, q1, q2, a, p') = True
    => (p', q1, q2, a, Adam) is true if (p, q1, q2, a, Eve) is true and strategy(p, q1, q2, a) = p'
    """
    def eve_adam_sequence(self):
        for p in self.na.states:
            for q1 in self.na.states:
                for q2 in self.na.states:
                    for a in self.na.alphabet:
                        p_primes = p.transitions.get(a, [])
                        for p_prime in p_primes:
                            self.model.add(self.position_variables[(p_prime, q1, q2, a, "Adam")] == True).only_enforce_if(
                                self.edge_variables[(p, q1, q2, a, "Eve", p_prime)]
                            )


    """
    Adam 'chooses' a starting letter a and the Eve tuple (q0, q0, q0, a, Eve) is true for a;

    Adam 'chooses' a q1' and a q2' such that they are reachable from, respectively, q1 and q2 by letter a,
    and (p, q1, q2, a, Adam) is true.
    Adam also 'chooses' a letter b.
    => for all p, q1, q2 in Q, and a in Alphabet,
    for all q1', q2' reachable from q1 and q2 respectively by letter a,
    for all b in Alphabet,
    all (p, q1', q2', b, Eve) tuples are true.
    If the (p, q1, q2, a, Adam) tuple is false, then (p, q1', q2', b, Eve) is false.
    """
    def adam_eve_sequence(self):
        start_state = self.na.states[0]
        for a in self.na.alphabet:
            self.model.add(self.position_variables[(start_state, start_state, start_state, a, "Eve")] == True)

        for p in self.na.states:
            for a in self.na.alphabet:
                for q1 in self.na.states:
                    q1_primes = q1.transitions.get(a, [])
                    for q1_prime in q1_primes:
                        for q2 in self.na.states:
                            q2_primes = q2.transitions.get(a, [])
                            for q2_prime in q2_primes:
                                for b in self.na.alphabet:
                                    position_variable = self.position_variables[
                                        (p, q1_prime, q2_prime, b, "Eve")]

                                    self.model.add(position_variable == True).only_enforce_if(self.position_variables[(p, q1, q2, a, "Adam")])

    """
    computing paths
    """
    def pathing(self):
        for p in self.na.states:
            for q1 in self.na.states:
                for q2 in self.na.states:
                    for a in self.na.alphabet:
                        self.model.add(self.path_variables[(p, q1, q2, a, p, q1, q2, a, "Eve", 0)] == True).only_enforce_if(
                            self.position_variables[(p, q1, q2, a, "Eve")])

        for a in self.na.alphabet:
            for q1 in self.na.states:
                for q1_prime in self.na.states:
                    for q2 in self.na.states:
                        for q2_prime in self.na.states:
                            for p in self.na.states:
                                for p_prime in self.na.states:
                                    for p_seconde in p_prime.transitions.get(a, []):
                                        for c in self.na.alphabet:
                                            for n in range(3):
                                                literals = [
                                                    self.path_variables[(p, q1, q2, c, p_prime, q1_prime, q2_prime, a, "Eve", n)],
                                                    self.edge_variables[(p_prime, q1_prime, q2_prime, a, "Eve",
                                                                         p_seconde)],
                                                ]
                                                if p_seconde.is_accepting:
                                                    self.model.add(self.path_variables[
                                                                       (p, q1, q2, c, p_seconde, q1_prime, q2_prime, a, "Adam",
                                                                        2)] == True).only_enforce_if(
                                                        literals
                                                    )
                                                else:
                                                    self.model.add(self.path_variables[
                                                                       (p, q1, q2, c, p_seconde, q1_prime, q2_prime, a, "Adam",
                                                                        n)] == True).only_enforce_if(
                                                        literals
                                                    )


        for a in self.na.alphabet:
            for b in self.na.alphabet:
                for q1 in self.na.states:
                    for q1_prime in self.na.states:
                        for q2 in self.na.states:
                            for q2_prime in self.na.states:
                                for p in self.na.states:
                                    for p_prime in self.na.states:
                                        for q1_seconde in q1_prime.transitions.get(a, []):
                                            for q2_seconde in q2_prime.transitions.get(a, []):
                                                for c in self.na.alphabet:
                                                    for n in range(2):
                                                        literals = [self.path_variables[
                                                                    (p, q1, q2, c, p_prime, q1_prime, q2_prime, a, "Adam", n)],
                                                                    self.position_variables[(p_prime, q1_prime, q2_prime, a, "Adam")],
                                                                    self.position_variables[(p_prime, q1_seconde, q2_seconde, b, "Eve")]
                                                                    ]

                                                        if q1_seconde.is_accepting or q2_seconde.is_accepting:
                                                            self.model.add(self.path_variables[
                                                                               (p, q1, q2, c, p_prime, q1_seconde,
                                                                                q2_seconde, b, "Eve",
                                                                                1)] == True).only_enforce_if(
                                                                literals,

                                                            )
                                                        else:
                                                            self.model.add(self.path_variables[
                                                                               (p, q1, q2, c, p_prime, q1_seconde,
                                                                                q2_seconde, b, "Eve",
                                                                                n)] == True).only_enforce_if(
                                                                literals
                                                            )

                                                    self.model.add(self.path_variables[
                                                                       (p, q1, q2, c, p_prime, q1_seconde,
                                                                        q2_seconde, b, "Eve",
                                                                        2)] == True).only_enforce_if(
                                                        self.path_variables[
                                                            (p, q1, q2, c, p_prime, q1_prime, q2_prime, a, "Adam", 2)],
                                                        self.position_variables[
                                                            (p_prime, q1_prime, q2_prime, a, "Adam")],
                                                        self.position_variables[
                                                            (p_prime, q1_seconde, q2_seconde, b, "Eve")]
                                                    )


    def cycle_closing(self):
        for a in self.na.alphabet:
            for q1 in self.na.states:
                for q2 in self.na.states:
                    for p in self.na.states:
                        self.model.add(self.path_variables[
                           (p, q1, q2, a, p, q1, q2, a, "Eve", 1)] == False)



    def solve(self):
        self.eve_strategy()
        self.eve_adam_sequence()
        self.adam_eve_sequence()
        self.pathing()
        self.cycle_closing()
        self.status = self.solver.Solve(self.model)
        return self.status == cp_model.OPTIMAL

    def get_solution(self):
        if self.status == cp_model.OPTIMAL:
            print("Solution found:")
            for p in self.na.states:
                for q1 in self.na.states:
                    for q2 in self.na.states:
                        for a in self.na.alphabet:
                            if self.solver.Value(self.position_variables[(p, q1, q2, a, "Eve")]) == 1:
                                print(f'Eve is at position ({p.id}, {q1.id}, {q2.id}), for symbol {a}')
                            if self.solver.Value(self.position_variables[(p, q1, q2, a, "Adam")]) == 1:
                                print(f'Adam is at position ({p.id}, {q1.id}, {q2.id}), for symbol {a}')
                            for p_prime in p.transitions.get(a, []):
                                if self.solver.Value(
                                    self.edge_variables[(p, q1, q2, a, "Eve", p_prime)]) == 1:
                                    print(f'At position ({p.id}, {q1.id}, {q2.id}), for symbol {a}, Eve chooses {p_prime.id}')

                            for q1_prime in q1.transitions.get(a, []):
                                for q2_prime in q2.transitions.get(a, []):
                                    for b in self.na.alphabet:
                                        if self.solver.Value(
                                                self.position_variables[(p, q1, q2, a, "Adam")]) == 1 and self.solver.Value(self.position_variables[(p, q1_prime, q2_prime, b, "Eve")]) == 1:
                                            print(f'At position ({p.id}, {q1.id}, {q2.id}), for symbol {a}, Adam chooses {q1_prime.id} and {q2_prime.id} and {b}')
        else:
            print("No solution found")






if __name__ == "__main__":
    fake_na = NA()  # actually deterministic but deterministic means HD
    print("Fake NA")
    q0 = NA.State('q0')
    fake_na.add_state(NA.State('q0'))
    q0.is_accepting = True
    q1 = NA.State('q1')
    q1.is_accepting = True
    q2 = NA.State('q2')
    q3 = NA.State('q3')

    fake_na.alphabet = {'a', 'b'}

    q0.add_transition('a', q1)
    q0.add_transition('b', q2)
    q1.add_transition('a', q3)
    q1.add_transition('b', q0)
    q2.add_transition('a', q1)
    q2.add_transition('b', q2)
    q3.add_transition('a', q3)
    q3.add_transition('b', q0)
    fake_na.add_state(q0)
    fake_na.add_state(q1)
    fake_na.add_state(q2)
    fake_na.add_state(q3)
    fake_na.complete()
    game = Game(fake_na)
    game.solve()
    game.get_solution()

    print("----------------------------------------------------------------------------------------------------")

    non_hd_na = NA()
    print("Non-HD NA")
    p = NA.State('p')
    q = NA.State('q')
    q.is_accepting = True
    dump = NA.State('dump')
    non_hd_na.alphabet = {'a', 'b'}

    p.add_transition('a', p)
    p.add_transition('b', p)
    p.add_transition('a', q)
    p.add_transition('b', q)
    q.add_transition('a', q)
    q.add_transition('b', dump)
    dump.add_transition('a', dump)
    dump.add_transition('b', dump)
    non_hd_na.add_state(p)
    non_hd_na.add_state(q)
    non_hd_na.add_state(dump)
    non_hd_na.complete()
    game = Game(non_hd_na)
    game.solve()
    game.get_solution()
