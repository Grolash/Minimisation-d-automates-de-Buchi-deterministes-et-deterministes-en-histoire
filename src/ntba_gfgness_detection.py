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
            for a in self.nta.alphabet:
                p_primes = p.transitions.get(a, [])
                for p_prime in p_primes:
                    self.strategy_variables[(p,a, p_prime.target)] = self.model.new_bool_var(f'strategy_{p.id}_{a}_{p_prime.target.id}')
            for q1 in self.nta.states:
                for q2 in self.nta.states:
                    for a in self.nta.alphabet:
                        self.position_variables[(p, q1, q2, a, "Adam")] = self.model.new_bool_var(f'position_{p.id}_{q1.id}_{q2.id}_{a}_{"Adam"}')
                        self.position_variables[(p, q1, q2, a, "Eve")] = self.model.new_bool_var(f'position_{p.id}_{q1.id}_{q2.id}_{a}_{"Eve"}')
                    for q1_prime in self.nta.states:
                        for q2_prime in self.nta.states:
                            for p_prime in self.nta.states:
                                self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)] = self.model.new_bool_var(f'path_{p.id}_{p_prime.id}_{q1.id}_{q1_prime.id}_{q2.id}_{q2_prime.id}')

        # Initialize all ranks so lookups never crash.
        self.rank = {
            (p, q1, q2): 0
            for p in self.nta.states
            for q1 in self.nta.states
            for q2 in self.nta.states
        }
        self.win = self.model.new_bool_var('win')

        self.solver = cp_model.CpSolver()
        self.status = None

    """
    Among all transition targets for letter a, choose one.
    """
    def strategy_choice(self):
        for p in self.nta.states:
            for a in self.nta.alphabet:
                p_primes = p.transitions.get(a, [])
                if len(p_primes) > 0:
                    self.model.add_exactly_one(self.strategy_variables[(p, a, p_prime.target)] for p_prime in p_primes)

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
                            position_variable = self.position_variables[(p_prime.target, q1, q2, a, "Adam")]

                            literals = (self.position_variables[(p, q1, q2, a, "Eve")],
                                        self.strategy_variables[(p, a, p_prime.target)])
                            or_not_literals = self.model.new_bool_var(f'not_{p.id}_{a}_{p_prime.target.id}')
                            self.model.add_bool_or([l.Not() for l in literals]).only_enforce_if(or_not_literals)

                            self.model.add(position_variable == True).only_enforce_if(
                                literals
                            )
                            self.model.add(position_variable == False).only_enforce_if(
                                or_not_literals
                            )
                            self.rank[(p_prime.target, q1, q2)] = max(
                                self.rank.get((p, q1, q2), 0),
                                2 if p_prime.is_accepting else 0
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
                                    position_variable = self.position_variables[(p, q1_prime.target, q2_prime.target, b, "Eve")]

                                    self.model.add(position_variable == True).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")]
                                    )
                                    self.model.add(position_variable == False).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")].Not()
                                    )
                                self.rank[(p, q1_prime.target, q2_prime.target)] = max(
                                    self.rank.get((p, q1, q2), 0),
                                    1 if (q1_prime.is_accepting or q2_prime.is_accepting) else 0
                                )

    """
    computing paths
    """
    def pathing(self):
        self.model.add(self.path_variables[(self.nta.states[0], self.nta.states[0],
                                            self.nta.states[0], self.nta.states[0],
                                            self.nta.states[0], self.nta.states[0])] == True)

        for a in self.nta.alphabet:
            for q1 in self.nta.states:
                for q1_prime in self.nta.states:
                    for q2 in self.nta.states:
                        for q2_prime in self.nta.states:
                            for p in self.nta.states:
                                for p_prime in self.nta.states:
                                    for p_seconde in p_prime.transitions.get(a, []):
                                        if p_seconde.target != p:
                                            self.model.add(self.path_variables[(p, p_seconde.target, q1, q1_prime, q2, q2_prime)] == True).only_enforce_if(
                                                self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)],
                                                self.position_variables[(p_prime, q1_prime, q2_prime, a, "Eve")],
                                                self.position_variables[(p_seconde.target, q1_prime, q2_prime, a, "Adam")]
                                            )
        for a in self.nta.alphabet:
            for q1 in self.nta.states:
                for q1_prime in self.nta.states:
                    for q2 in self.nta.states:
                        for q2_prime in self.nta.states:
                            for p in self.nta.states:
                                for p_prime in self.nta.states:
                                    for q1_seconde in q1_prime.transitions.get("a", []):
                                        if q1_seconde.target != q1:
                                            for q2_seconde in q2_prime.transitions.get("a", []):
                                                if q2_seconde.target != q2:
                                                    for b in self.nta.alphabet:
                                                        self.model.add(self.path_variables[(p, p_prime, q1, q1_seconde.target, q2,
                                                                                            q2_seconde.target)] == True).only_enforce_if(
                                                            self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)],
                                                            self.position_variables[
                                                                (p_prime, q1_prime, q2_prime, a, "Adam")],
                                                            self.position_variables[
                                                                (p_prime, q1_seconde.target, q2_seconde.target, b, "Eve")]
                                                        )


    def cycle_closing(self):
        for a in self.nta.alphabet:
            for q1 in self.nta.states:
                for q1_prime in self.nta.states:
                    for q2 in self.nta.states:
                        for q2_prime in self.nta.states:
                            for p in self.nta.states:
                                for p_prime in self.nta.states:
                                    rank = self.rank[(p, q1_prime, q2_prime)]

                                    literals = (self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)],
                                            self.position_variables[(p_prime, q1_prime, q2_prime, a, "Eve")],
                                            self.position_variables[(p, q1_prime, q2_prime, a, "Adam")])

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
            for p in self.nta.states:
                for q1 in self.nta.states:
                    for q2 in self.nta.states:
                        for a in self.nta.alphabet:
                            if self.solver.Value(self.position_variables[(p, q1, q2, a, "Adam")]) == 1:
                                print(f"Position: --{a}--> {p.id} {q1.id} {q2.id} (Adam)")
                                print(
                                    f"Rank: {p.id} {q1.id} {q2.id} = {self.solver.Value(self.rank[(p, q1, q2)])}")
                            if self.solver.Value(self.position_variables[(p, q1, q2, a, "Eve")]) == 1:
                                print(f"Position: --{a}--> {p.id} {q1.id} {q2.id} (Eve)")
                                print(
                                    f"Rank: {p.id} {q1.id} {q2.id} = {self.solver.Value(self.rank[(p, q1, q2)])}")
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
    game = Game(nta)
    game.solve()
    game.get_solution()