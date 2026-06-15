from ortools.sat.python import cp_model

from src.nta import NTA

class Game:
    def __init__(self, nta: NTA):
        self.nta = nta
        self.model = cp_model.CpModel()

        self.position_variables = {}
        self.strategy_variables = {}
        self.path_variables = {}
        for p in self.nta.states:
            for q1 in self.nta.states:
                for q2 in self.nta.states:
                    for a in self.nta.alphabet:
                        self.position_variables[(p, q1, q2, a, "Adam")] = self.model.new_bool_var(
                            f'position_{p.id}_{q1.id}_{q2.id}_{a}_{"Adam"}')
                        self.position_variables[(p, q1, q2, a, "Eve")] = self.model.new_bool_var(
                            f'position_{p.id}_{q1.id}_{q2.id}_{a}_{"Eve"}')
                        p_primes: list[NTA.Transition] = p.transitions.get(a, [])
                        for p_prime in p_primes:
                            self.strategy_variables[(p, q1, q2, a, p_prime.target)] = self.model.new_bool_var(
                                f'strategy_{p.id}_{q1.id}_{q2.id}_{a}_{p_prime.target.id}')
                    for q1_prime in self.nta.states:
                        for q2_prime in self.nta.states:
                            for p_prime in self.nta.states:
                                self.path_variables[
                                    (p, q1, q2, p_prime, q1_prime, q2_prime, 0)] = self.model.new_bool_var(
                                    f'path_{p.id}_{q1.id}_{q2.id}_{p_prime.id}_{q1_prime.id}_{q2_prime.id}_{0}')
                                self.path_variables[
                                    (p, q1, q2, p_prime, q1_prime, q2_prime, 1)] = self.model.new_bool_var(
                                    f'path_{p.id}_{q1.id}_{q2.id}_{p_prime.id}_{q1_prime.id}_{q2_prime.id}_{1}')
                                self.path_variables[
                                    (p, q1, q2, p_prime, q1_prime, q2_prime, 2)] = self.model.new_bool_var(
                                    f'path_{p.id}_{q1.id}_{q2.id}_{p_prime.id}_{q1_prime.id}_{q2_prime.id}_{2}')

        self.solver = cp_model.CpSolver()
        self.status = None

    def eve_strategy(self):
        for p in self.nta.states:
            for a in self.nta.alphabet:
                for q1 in self.nta.states:
                    for q2 in self.nta.states:
                        p_primes: list[NTA.Transition] = p.transitions.get(a, [])
                        strategy_variables = [self.strategy_variables[(p, q1, q2, a, p_prime.target)] for p_prime in p_primes]
                        self.model.add_exactly_one(strategy_variables)

    """
    Eve chooses the transition given by her strategy for symbol a at position p; transition.target is p' in formula
    => p' = strategy(p, q1, q2, a); i.e., strategy(p, q1, q2, a, p') = True
    => (p', q1, q2, a, Adam) is true if (p, q1, q2, a, Eve) is true and strategy(p, q1, q2, a) = p'
    """
    def eve_adam_sequence(self):
        for p in self.nta.states:
            for q1 in self.nta.states:
                for q2 in self.nta.states:
                    for a in self.nta.alphabet:
                        p_primes = p.transitions.get(a, [])
                        for p_prime in p_primes:
                            self.model.add(self.position_variables[(p_prime.target, q1, q2, a, "Adam")] == True).only_enforce_if(
                                self.position_variables[(p, q1, q2, a, "Eve")],
                                self.strategy_variables[(p, q1, q2, a, p_prime.target)]
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
        start_state = self.nta.states[0]
        for a in self.nta.alphabet:
            self.model.add(self.position_variables[(start_state, start_state, start_state, a, "Eve")] == True)

        for p in self.nta.states:
            for a in self.nta.alphabet:
                for q1 in self.nta.states:
                    q1_primes = q1.transitions.get(a, [])
                    for q1_prime in q1_primes:
                        for q2 in self.nta.states:
                            q2_primes = q2.transitions.get(a, [])
                            for q2_prime in q2_primes:
                                for b in self.nta.alphabet:
                                    position_variable = self.position_variables[
                                        (p, q1_prime.target, q2_prime.target, b, "Eve")]

                                    self.model.add(position_variable == True).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")]
                                    )

    """
    computing paths
    """
    def pathing(self):
        for p in self.nta.states:
            for q1 in self.nta.states:
                for q2 in self.nta.states:
                    for a in self.nta.alphabet:
                        self.model.add_exactly_one(self.path_variables[(p, q1, q2, p, q1, q2, 0)]).only_enforce_if(
                            self.position_variables[(p, q1, q2, a, "Eve")])

        for a in self.nta.alphabet:
            for q1 in self.nta.states:
                for q1_prime in self.nta.states:
                    for q2 in self.nta.states:
                        for q2_prime in self.nta.states:
                            for p in self.nta.states:
                                for p_prime in self.nta.states:
                                    for p_seconde in p_prime.transitions.get(a, []):
                                        for n in range(3):
                                            literals = [
                                                self.path_variables[(p, q1, q2, p_prime, q1_prime, q2_prime, n)],
                                                self.position_variables[(p_prime, q1_prime, q2_prime, a, "Eve")],
                                                self.position_variables[
                                                    (p_seconde.target, q1_prime, q2_prime, a, "Adam")]]
                                            if p_seconde.is_accepting:
                                                self.model.add(self.path_variables[
                                                                   (p, q1, q2, p_seconde.target, q1_prime, q2_prime,
                                                                    2)] == True).only_enforce_if(
                                                    literals
                                                )
                                            else:
                                                self.model.add(self.path_variables[
                                                                   (p, q1, q2, p_seconde.target, q1_prime, q2_prime,
                                                                    n)] == True).only_enforce_if(
                                                    literals
                                                )


        for a in self.nta.alphabet:
            for b in self.nta.alphabet:
                for q1 in self.nta.states:
                    for q1_prime in self.nta.states:
                        for q2 in self.nta.states:
                            for q2_prime in self.nta.states:
                                for p in self.nta.states:
                                    for p_prime in self.nta.states:
                                        for q1_seconde in q1_prime.transitions.get("a", []):
                                            for q2_seconde in q2_prime.transitions.get("a", []):
                                                for n in range(2):
                                                    literals = [self.path_variables[
                                                                (p, q1, q2, p_prime, q1_prime, q2_prime, n)],
                                                                self.position_variables[
                                                                (p_prime, q1_prime, q2_prime, a, "Adam")],
                                                                self.position_variables[
                                                                    (p_prime, q1_seconde.target, q2_seconde.target, b,
                                                                     "Eve")]]

                                                    if q1_seconde.is_accepting or q2_seconde.is_accepting:
                                                        self.model.add(self.path_variables[
                                                                           (p, q1, q2, p_prime, q1_seconde.target,
                                                                            q2_seconde.target,
                                                                            1)] == True).only_enforce_if(
                                                            literals
                                                        )
                                                    else:
                                                        self.model.add(self.path_variables[
                                                                           (p, q1, q2, p_prime, q1_seconde.target,
                                                                            q2_seconde.target,
                                                                            n)] == True).only_enforce_if(
                                                            literals
                                                        )

                                                self.model.add(self.path_variables[
                                                                   (p, q1, q2, p_prime, q1_seconde.target,
                                                                    q2_seconde.target,
                                                                    2)] == True).only_enforce_if(
                                                    self.path_variables[
                                                        (p, q1, q2, p_prime, q1_prime, q2_prime, 2)],
                                                    self.position_variables[
                                                        (p_prime, q1_prime, q2_prime, a, "Adam")],
                                                    self.position_variables[
                                                        (p_prime, q1_seconde.target, q2_seconde.target, b, "Eve")]
                                                )


    def cycle_closing(self):
        for a in self.nta.alphabet:
            for b in self.nta.alphabet:
                for q1 in self.nta.states:
                    for q2 in self.nta.states:
                        for p in self.nta.states:
                            self.model.add(self.path_variables[
                               (p, q1, q2, p, q1, q2, 1)] == False)



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
            for p in self.nta.states:
                for q1 in self.nta.states:
                    for q2 in self.nta.states:
                        for a in self.nta.alphabet:
                            for p_prime in p.transitions.get(a, []):
                                if self.solver.Value(
                                    self.position_variables[(p, q1, q2, a, "Eve")]) == 1 and self.solver.Value(
                                    self.position_variables[(p_prime.target, q1, q2, a, "Adam")]) == 1:
                                    print(f'At position ({p.id}, {q1.id}, {q2.id}), for symbol {a}, Eve chooses {p_prime.target.id}')

                            for q1_prime in q1.transitions.get(a, []):
                                for q2_prime in q2.transitions.get(a, []):
                                    if self.solver.Value(
                                        self.position_variables[(p, q1, q2, a, "Adam")]
                                        ) == 1 and self.solver.Value(
                                        self.position_variables[(p, q1_prime.target, q2_prime.target, a, "Eve")]
                                        ) == 1:
                                        print(f'At position ({p.id}, {q1.id}, {q2.id}), for symbol {a}, Adam chooses {q1_prime.target.id} and {q2_prime.target.id}')
        else:
            print("No solution found")



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

    print("GFG NTA:")
    game1 = Game(GFG_nta)
    game1.solve()
    game1.get_solution()

    non_GFG_nta = NTA()
    non_GFG_nta.alphabet = {'a', 'b'}
    p = NTA.State('p')
    q = NTA.State('q')
    p.add_transition('a', p)
    p.add_transition('b', p)
    p.add_transition('a', q, True)
    p.add_transition('b', q, True)
    q.add_transition('a', q, True)
    non_GFG_nta.add_state(p)
    non_GFG_nta.add_state(q)
    non_GFG_nta.complete()

    print("Non-GFG NTA:")
    game2 = Game(non_GFG_nta)
    game2.solve()
    game2.get_solution()