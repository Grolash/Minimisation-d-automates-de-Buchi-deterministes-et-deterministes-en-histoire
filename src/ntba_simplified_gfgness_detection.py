from ortools.sat.python import cp_model

from src.nta import NTA

class Game:
    def __init__(self, nta: NTA):
        self.nta = nta
        self.model = cp_model.CpModel()

        self.strategy_variables = {}
        self.path_variables = {}
        for p in self.nta.states:
            for q1 in self.nta.states:
                for q2 in self.nta.states:
                    for a in self.nta.alphabet:
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

    def path_building(self):
        for p in self.nta.states:
            for q1 in self.nta.states:
                for q2 in self.nta.states:
                    self.model.add(self.path_variables[(p, q1, q2, p, q1, q2, 0)] == True)

        """for p in self.nta.states:
            for q1 in self.nta.states:
                for q2 in self.nta.states:
                    for p_prime in self.nta.states:
                        for q1_prime in self.nta.states:
                            for q2_prime in self.nta.states:
                                for a in self.nta.alphabet:
                                    p_secondes: list[NTA.Transition] = p_prime.transitions.get(a, [])
                                    for p_seconde in p_secondes:
                                        for r in range(3):
                                            literals = [self.path_variables[(p, q1, q2, p_prime, q1_prime, q2_prime, r)],
                                                        self.strategy_variables[(p_prime, q1_prime, q2_prime, a, p_seconde.target)]]

                                            if p_seconde.is_accepting:
                                                self.model.add(self.path_variables[
                                                                   (p, q1, q2, p_seconde.target, q1_prime, q2_prime,
                                                                    2)] == True).only_enforce_if(
                                                    literals
                                                )
                                            else:
                                                self.model.add(self.path_variables[
                                                                   (p, q1, q2, p_seconde.target, q1_prime, q2_prime,
                                                                    r)] == True).only_enforce_if(
                                                    literals
                                                )"""

        for p in self.nta.states:
            for q1 in self.nta.states:
                for q2 in self.nta.states:
                    for p_prime in self.nta.states:
                        for q1_prime in self.nta.states:
                            for q2_prime in self.nta.states:
                                for a in self.nta.alphabet:
                                    q1_secondes: list[NTA.Transition] = q1_prime.transitions.get(a, [])
                                    q2_secondes: list[NTA.Transition] = q2_prime.transitions.get(a, [])
                                    p_secondes: list[NTA.Transition] = p_prime.transitions.get(a, [])
                                    for q1_seconde in q1_secondes:
                                        for q2_seconde in q2_secondes:
                                            for p_seconde in p_secondes:
                                                    for r in range(2):
                                                        if p_seconde.is_accepting:
                                                            self.model.add(self.path_variables[
                                                                               (p, q1, q2, p_seconde.target,
                                                                                q1_seconde.target, q2_seconde.target,
                                                                                2)] == True).only_enforce_if(
                                                                self.path_variables[
                                                                    (p, q1, q2, p_prime, q1_prime, q2_prime, r)],
                                                                self.strategy_variables[
                                                                    (p_prime, q1_prime, q2_prime, a, p_seconde.target)],
                                                            )
                                                        else:
                                                            if q1_seconde.is_accepting or q2_seconde.is_accepting:
                                                                self.model.add(self.path_variables[
                                                                                   (p, q1, q2, p_seconde.target, q1_seconde.target, q2_seconde.target,
                                                                                    1)] == True).only_enforce_if(
                                                                    self.path_variables[(p, q1, q2, p_prime, q1_prime, q2_prime, r)],
                                                                    self.strategy_variables[(p_prime, q1_prime, q2_prime, a, p_seconde.target)],
                                                                )
                                                            else:
                                                                self.model.add(self.path_variables[
                                                                                   (p, q1, q2, p_seconde.target, q1_seconde.target, q2_seconde.target,
                                                                                    r)] == True).only_enforce_if(
                                                                    self.path_variables[(p, q1, q2, p_prime, q1_prime, q2_prime, r)],
                                                                    self.strategy_variables[(p_prime, q1_prime, q2_prime, a, p_seconde.target)],
                                                                )

                                            self.model.add(self.path_variables[
                                                               (p, q1, q2, p_prime, q1_seconde.target, q2_seconde.target,
                                                                                2)] == True).only_enforce_if(
                                                self.path_variables[(p, q1, q2, p_prime, q1_prime, q2_prime, 2)],
                                            )

    def cycle_closing(self):
        for p in self.nta.states:
            for q1 in self.nta.states:
                for q2 in self.nta.states:
                    self.model.add(self.path_variables[(p, q1, q2, p, q1, q2, 1)] == False)

    def solve(self):
        self.eve_strategy()
        self.path_building()
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
                                if self.solver.Value(self.strategy_variables[(p, q1, q2, a, p_prime.target)]) == 1:
                                    print(f'At position ({p.id}, {q1.id}, {q2.id}), for symbol {a}, Eve chooses {p_prime.target.id}')
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
