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

        for p in a_nta.states:
            for a in a_nta.alphabet:
                p_primes = p.transitions.get(a, [])
                for p_prime in p_primes:
                    self.strategy_variables[(p, a, p_prime.target)] = self.model.new_bool_var(
                        f'strategy_{p.id}_{a}_{p_prime.target.id}')
            for q in b_nta.states:
                for a in a_nta.alphabet:
                    self.position_variables[(p, q, a, "Adam")] = self.model.new_bool_var(f'position_{p.id}_{q.id}_{a}_{"Adam"}')
                    self.position_variables[(p, q, a, "Eve")] = self.model.new_bool_var(f'position_{p.id}_{q.id}_{a}_{"Eve"}')
                    for q_prime in b_nta.states:
                        for p_prime in a_nta.states:
                            self.path_variables[(p, p_prime, q, q_prime)] = (
                                self.model.new_bool_var(f'path_{p.id}_{p_prime.id}_{q.id}_{q_prime.id}'))

        self.rank = {
            (p, q): 0
            for p in self.a_nta.states
            for q in self.b_nta.states
        }
        self.win = self.model.new_bool_var('win')

        self.solver = cp_model.CpSolver()
        self.status = None


    """
    Among all transition targets for letter a, choose one.
    """
    def strategy_choice(self):
        for p in self.a_nta.states:
            for a in self.a_nta.alphabet:
                p_primes = p.transitions.get(a, [])
                if len(p_primes) > 0:
                    self.model.add_exactly_one(self.strategy_variables[(p, a, p_prime.target)] for p_prime in p_primes)

    """
    Eve chooses the transition given by her strategy for symbol a at position p on automata A; transition.target is p' in formula
    => p' = strategy(p, q, a); i.e., strategy(p, q, a, p') = True
    => (p', q, a, Adam) is true if (p, q, a, Eve) is true and strategy(p, q, a) = p'
    """
    def eve_adam_sequence(self):
        for p in self.a_nta.states:
            for q in self.b_nta.states:
                for a in self.a_nta.alphabet:
                    p_primes = p.transitions.get(a, [])
                    for p_prime in p_primes:
                        position_variable = self.position_variables[(p_prime.target, q, a, "Adam")]

                        literals = (self.position_variables[(p, q, a, "Eve")],
                                    self.strategy_variables[(p, a, p_prime.target)])
                        or_not_literals = self.model.new_bool_var(f'not_{p.id}_{a}_{p_prime.target.id}')
                        self.model.add_bool_or([l.Not() for l in literals]).only_enforce_if(or_not_literals)

                        self.model.add(position_variable == True).only_enforce_if(
                            literals
                        )
                        self.model.add(position_variable == False).only_enforce_if(
                            or_not_literals
                        )
                        self.rank[(p_prime.target, q)] = max(
                            self.rank.get((p, q), 0),
                            2 if p_prime.is_accepting else 0
                        )


    """
    Adam 'chooses' a starting letter a and the Eve tuple (p0, q0, a, Eve) is true for a;

    Adam 'chooses' a q' such that it is reachable from q by letter a,
    and (p, q, a, Adam) is true.
    Adam also 'chooses' a letter b.
    => for all p in Qa, q in Qb, and a in alphabet of automata A,
    for all q' reachable from q by letter a,
    for all b in alphabet of automata A,
    all (p, q', b, Eve) tuples are true.
    If the (p, q, a, Adam) tuple is false, then (p, q', b, Eve) is false.
    """
    def adam_eve_sequence(self):
        for a in self.a_nta.alphabet:
            self.model.add(self.position_variables[(self.a_nta.states[0], self.b_nta.states[0], a, "Eve")] == True)

        for p in self.a_nta.states:
            for a in self.a_nta.alphabet:
                for q in self.b_nta.states:
                    q_primes = q.transitions.get(a, [])
                    for q_prime in q_primes:
                        for b in self.a_nta.alphabet:
                            position_variable = self.position_variables[
                                (p, q_prime.target, b, "Eve")]

                            self.model.add(position_variable == True).only_enforce_if(
                                self.position_variables[(p, q, a, "Adam")]
                            )
                            self.model.add(position_variable == False).only_enforce_if(
                                self.position_variables[(p, q, a, "Adam")].Not()
                            )
                        self.rank[(p, q_prime.target)] = max(
                            self.rank.get((p, q), 0),
                            1 if q_prime.is_accepting else 0
                        )


    def pathing(self):
        self.model.add(self.path_variables[(self.a_nta.states[0], self.a_nta.states[0],
                                            self.b_nta.states[0], self.b_nta.states[0])] == True)

        for a in self.a_nta.alphabet:
            for q in self.b_nta.states:
                for q_prime in self.b_nta.states:
                    for p in self.a_nta.states:
                        for p_prime in self.a_nta.states:
                            for p_seconde in p_prime.transitions.get(a, []):
                                if p_seconde.target != p:
                                    self.model.add(self.path_variables[(p, p_seconde.target, q, q_prime)] == True).only_enforce_if(
                                        self.path_variables[(p, p_prime, q, q_prime)],
                                        self.position_variables[(p_prime, q_prime, a, "Eve")],
                                        self.position_variables[(p_seconde.target, q_prime, a, "Adam")]
                                    )
        for a in self.a_nta.alphabet:
            for q in self.b_nta.states:
                for q_prime in self.b_nta.states:
                    for p in self.a_nta.states:
                        for p_prime in self.a_nta.states:
                            for q_seconde in q_prime.transitions.get("a", []):
                                if q_seconde.target != q:
                                    for b in self.a_nta.alphabet:
                                        self.model.add(self.path_variables[(p, p_prime, q, q_seconde.target)] == True).only_enforce_if(
                                            self.path_variables[(p, p_prime, q, q_prime)],
                                            self.position_variables[
                                                (p_prime, q_prime, a, "Adam")],
                                            self.position_variables[
                                                (p_prime, q_seconde.target, b, "Eve")]
                                        )

    def cycle_closing(self):
        for a in self.a_nta.alphabet:
            for q in self.b_nta.states:
                for q_prime in self.b_nta.states:
                    for p in self.a_nta.states:
                        for p_prime in self.a_nta.states:
                            rank = self.rank[(p, q_prime)]

                            literals = (self.path_variables[(p, p_prime, q, q_prime)],
                                    self.position_variables[(p_prime, q_prime, a, "Eve")],
                                    self.position_variables[(p, q_prime, a, "Adam")])

                            if rank == 0 or rank == 2:
                                self.model.add(self.win == True).only_enforce_if(
                                    literals,
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
            print(f"Win: {self.solver.Value(self.win)}")
            for p in self.a_nta.states:
                for q in self.b_nta.states:
                    for a in self.a_nta.alphabet:
                        if self.solver.Value(self.position_variables[(p, q, a, "Adam")]) == 1:
                            print(f"Position: --{a}--> {p.id} {q.id} (Adam)")
                            print(
                                f"Rank: {p.id} {q.id} = {self.solver.Value(self.rank[(p, q)])}")
                        if self.solver.Value(self.position_variables[(p, q, a, "Eve")]) == 1:
                            print(f"Position: --{a}--> {p.id} {q.id} (Eve)")
                            print(
                                f"Rank: {p.id} {q.id} = {self.solver.Value(self.rank[(p, q)])}")
            print(f"Win: {self.solver.Value(self.win)}")
        else:
            print("No solution found")


if __name__ == "__main__":
    nta = NTA()
    nta.alphabet = {'a', 'b', 'x'}
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
    nta.add_state(i)
    nta.add_state(a)
    nta.add_state(a_prime)
    nta.add_state(a_seconde)
    nta.add_state(b)
    nta.add_state(b_prime)
    nta.add_state(b_seconde)
    game = InclusionGame(nta, nta)
    game.solve()
    game.get_solution()