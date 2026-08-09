from ortools.sat.python import cp_model

from src.nta import NTA

class InclusionGame:
    def __init__(self, a_nta: NTA, b_nta: NTA):
        self.a_nta = a_nta
        self.b_nta = b_nta
        self.model = cp_model.CpModel()

        self.position_variables = {}
        self.strategy_variables = {}
        self.path_variables = {}
        for p in self.a_nta.states:
            for q in self.b_nta.states:
                for a in self.a_nta.alphabet:
                    self.position_variables[(p, q, a, "Adam")] = self.model.new_bool_var(
                        '')
                    self.position_variables[(p, q, a, "Eve")] = self.model.new_bool_var(
                        '')
                    p_primes: list[NTA.Transition] = p.transitions.get(a, [])
                    for p_prime in p_primes:
                        self.strategy_variables[(p, q, a, p_prime.target)] = self.model.new_bool_var(
                            '')
                    for q_prime in self.b_nta.states:
                        for p_prime in self.a_nta.states:
                            for b in self.a_nta.alphabet:
                                for player in ["Adam", "Eve"]:
                                    self.path_variables[
                                        (p, q, a, p_prime, q_prime, b, player, 0)] = self.model.new_bool_var(
                                        '')
                                    self.path_variables[
                                        (p, q, a, p_prime, q_prime, b, player, 1)] = self.model.new_bool_var(
                                        '')
                                    self.path_variables[
                                        (p, q, a, p_prime, q_prime, b, player, 2)] = self.model.new_bool_var(
                                        '')

        self.solver = cp_model.CpSolver()
        self.status = None

    def eve_strategy(self):
        for p in self.a_nta.states:
            for a in self.a_nta.alphabet:
                for q in self.b_nta.states:
                    p_primes: list[NTA.Transition] = p.transitions.get(a, [])
                    strategy_variables = [self.strategy_variables[(p, q, a, p_prime.target)] for p_prime in p_primes]
                    self.model.add_exactly_one(strategy_variables)

    def eve_adam_sequence(self):
        for p in self.a_nta.states:
            for q in self.b_nta.states:
                for a in self.a_nta.alphabet:
                    p_primes = p.transitions.get(a, [])
                    for p_prime in p_primes:
                        self.model.add(self.position_variables[(p_prime.target, q, a, "Adam")] == True).only_enforce_if(
                            self.strategy_variables[(p, q, a, p_prime.target)]
                        )

    def adam_eve_sequence(self):
        start_state_a = self.a_nta.states[0]
        start_state_b = self.b_nta.states[0]
        for a in self.a_nta.alphabet:
            self.model.add(self.position_variables[(start_state_a, start_state_b, a, "Eve")] == True)

        for p in self.a_nta.states:
            for a in self.a_nta.alphabet:
                for q in self.b_nta.states:
                    q_primes = q.transitions.get(a, [])
                    for q_prime in q_primes:
                        for b in self.b_nta.alphabet:
                            position_variable = self.position_variables[
                                (p, q_prime.target, b, "Eve")]

                            self.model.add(position_variable == True).only_enforce_if(
                                self.position_variables[(p, q, a, "Adam")]
                            )

    """
    computing paths
    """
    def pathing(self):
        for p in self.a_nta.states:
            for q in self.b_nta.states:
                for a in self.a_nta.alphabet:
                    self.model.add_exactly_one(self.path_variables[(p, q, a, p, q, a, "Eve", 0)]).only_enforce_if(
                        self.position_variables[(p, q, a, "Eve")])

        for a in self.a_nta.alphabet:
            for q in self.b_nta.states:
                for q_prime in self.b_nta.states:
                    for p in self.a_nta.states:
                        for p_prime in self.a_nta.states:
                            for p_seconde in p_prime.transitions.get(a, []):
                                for b in self.a_nta.alphabet:
                                    for n in range(3):
                                        literals = [
                                            self.path_variables[(p, q, b, p_prime, q_prime, a, "Eve", n)],
                                            self.strategy_variables[(p_prime, q_prime, a, p_seconde.target)]]

                                        if p_seconde.is_accepting:
                                            self.model.add(self.path_variables[
                                                               (p, q, b, p_seconde.target, q_prime, a, "Adam",
                                                                2)] == True).only_enforce_if(
                                                literals
                                            )
                                        else:
                                            self.model.add(self.path_variables[
                                                               (p, q, b, p_seconde.target, q_prime, a, "Adam",
                                                                n)] == True).only_enforce_if(
                                                literals
                                            )

        for a in self.a_nta.alphabet:
            for b in self.b_nta.alphabet:
                for q in self.b_nta.states:
                    for q_prime in self.b_nta.states:
                        for p in self.a_nta.states:
                            for p_prime in self.a_nta.states:
                                for q_seconde in q_prime.transitions.get("a", []):
                                    for c in self.a_nta.alphabet:
                                        for n in range(2):
                                            literals = [self.path_variables[
                                                        (p, q, c, p_prime, q_prime, a, "Eve", n)],
                                                        self.position_variables[
                                                        (p_prime, q_prime, a, "Adam")],
                                                        self.position_variables[
                                                            (p_prime, q_seconde.target, b,
                                                             "Eve")]]

                                            if q_seconde.is_accepting:
                                                self.model.add(self.path_variables[
                                                                   (p, q, c, p_prime, q_seconde.target, b, "Eve",
                                                                    1)] == True).only_enforce_if(
                                                    literals
                                                )
                                            else:
                                                self.model.add(self.path_variables[
                                                                   (p, q, c, p_prime, q_seconde.target, b, "Eve",
                                                                    n)] == True).only_enforce_if(
                                                    literals
                                                )

                                        self.model.add(self.path_variables[
                                                           (p, q, c, p_prime, q_seconde.target, b, "Eve",
                                                            2)] == True).only_enforce_if(
                                            self.path_variables[
                                                (p, q, c, p_prime, q_prime, a, "Eve", 2)],
                                            self.position_variables[
                                                (p_prime, q_prime, a, "Adam")],
                                            self.position_variables[
                                                (p_prime, q_seconde.target, b, "Eve")]
                                        )


    def cycle_closing(self):
        for a in self.a_nta.alphabet:
            for b in self.b_nta.alphabet:
                for q in self.b_nta.states:
                    for p in self.a_nta.states:
                        self.model.add(self.path_variables[
                           (p, q, a, p, q, a, "Eve", 1)] == False)

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
            for p in self.a_nta.states:
                for q in self.b_nta.states:
                    for a in self.a_nta.alphabet:
                        for p_prime in p.transitions.get(a, []):
                            if (self.solver.Value(self.position_variables[(p, q, a, "Eve")]) == 1 and
                                    self.solver.Value(self.position_variables[(p_prime.target, q, a, "Adam")]) == 1):
                                print(f'At position ({p.id}, {q.id}), for symbol {a}, Eve chooses {p_prime.target.id}')

                        for q_prime in q.transitions.get(a, []):
                            if (self.solver.Value(self.position_variables[(p, q, a, "Adam")]) == 1 and
                                    self.solver.Value(self.position_variables[(p, q_prime.target, a, "Eve")]) == 1):
                                print(f'At position ({p.id}, {q.id}), for symbol {a}, Adam chooses {q_prime.target.id}')

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

    print("GFG NTA 1 = GFG NTA 2:")
    game1 = InclusionGame(GFG_nta, GFG_nta)
    game1.solve()
    game1.get_solution()

    non_GFG_nta = NTA()
    non_GFG_nta.alphabet = {'a', 'b', 'x'}
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

    """print("GFG, Non-GFG NTA:")
    game2 = InclusionGame(GFG_nta, non_GFG_nta)
    game2.solve()
    game2.get_solution()"""

    """print("Non-GFG, GFG NTA:")
    game3 = InclusionGame(non_GFG_nta, GFG_nta)
    game3.solve()
    game3.get_solution()"""