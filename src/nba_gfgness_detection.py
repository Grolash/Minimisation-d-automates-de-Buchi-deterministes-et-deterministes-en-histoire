from ortools.sat.python import cp_model

from src.na import NA

class Game:
    def __init__(self, na: NA):
        self.na = na
        self.model = cp_model.CpModel()

        self.position_variables = {}
        self.strategy_variables = {}
        self.path_variables = {}
        for p in self.na.states:
            for a in self.na.alphabet:
                p_primes = p.transitions.get(a, [])
                for p_prime in p_primes:
                    self.strategy_variables[(p,a, p_prime)] = self.model.new_bool_var(f'strategy_{p.id}_{a}_{p_prime.id}')
            for q1 in self.na.states:
                for q2 in self.na.states:
                    for a in self.na.alphabet:
                        self.position_variables[(p, q1, q2, a, "Adam")] = self.model.new_bool_var(f'position_{p.id}_{q1.id}_{q2.id}_{a}_{"Adam"}')
                        self.position_variables[(p, q1, q2, a, "Eve")] = self.model.new_bool_var(f'position_{p.id}_{q1.id}_{q2.id}_{a}_{"Eve"}')
                    for q1_prime in self.na.states:
                        for q2_prime in self.na.states:
                            for p_prime in self.na.states:
                                self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)] = self.model.new_bool_var(f'path_{p.id}_{p_prime.id}_{q1.id}_{q1_prime.id}_{q2.id}_{q2_prime.id}')

        # Initialize all ranks so lookups never crash.
        self.rank = {
            (p, q1, q2): 0
            for p in self.na.states
            for q1 in self.na.states
            for q2 in self.na.states
        }
        self.win = self.model.new_bool_var('win')

        self.solver = cp_model.CpSolver()
        self.status = None

    """
    Among all transition targets for letter a, choose one.
    """
    def strategy_choice(self):
        for p in self.na.states:
            for a in self.na.alphabet:
                p_primes = p.transitions.get(a, [])
                if len(p_primes) > 0:
                    self.model.add_exactly_one(self.strategy_variables[(p, a, p_prime)] for p_prime in p_primes)

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
                            position_variable = self.position_variables[(p_prime, q1, q2, a, "Adam")]

                            literals = (self.position_variables[(p, q1, q2, a, "Eve")],
                                        self.strategy_variables[(p, a, p_prime)])
                            or_not_literals = self.model.new_bool_var(f'not_{p.id}_{a}_{p_prime.id}')
                            self.model.add_bool_or([l.Not() for l in literals]).only_enforce_if(or_not_literals)

                            self.model.add(position_variable == True).only_enforce_if(
                                literals
                            )
                            self.model.add(position_variable == False).only_enforce_if(
                                or_not_literals
                            )
                            self.rank[(p_prime, q1, q2)] = max(
                                self.rank.get((p, q1, q2), 0),
                                2 if p_prime.is_accepting else 0
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
                                    position_variable = self.position_variables[(p, q1_prime, q2_prime, b, "Eve")]

                                    self.model.add(position_variable == True).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")]
                                    )
                                    self.model.add(position_variable == False).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")].Not()
                                    )
                                self.rank[(p, q1_prime, q2_prime)] = max(
                                    self.rank.get((p, q1, q2), 0),
                                    1 if (q1_prime.is_accepting or q2_prime.is_accepting) else 0
                                )

    """
    computing paths
    """
    def pathing(self):
        self.model.add(self.path_variables[(self.na.states[0], self.na.states[0],
                                            self.na.states[0], self.na.states[0],
                                            self.na.states[0], self.na.states[0])] == True)


        for a in self.na.alphabet:
            for q1 in self.na.states:
                for q1_prime in self.na.states:
                    for q2 in self.na.states:
                        for q2_prime in self.na.states:
                            for p in self.na.states:
                                for p_prime in self.na.states:
                                    for p_seconde in p_prime.transitions.get(a, []):
                                        if p_seconde != p:
                                            self.model.add(self.path_variables[(p, p_seconde, q1, q1_prime, q2, q2_prime)] == True).only_enforce_if(
                                                self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)],
                                                self.position_variables[(p_prime, q1_prime, q2_prime, a, "Eve")],
                                                self.position_variables[(p_seconde, q1_prime, q2_prime, a, "Adam")]
                                            )
        for a in self.na.alphabet:
            for q1 in self.na.states:
                for q1_prime in self.na.states:
                    for q2 in self.na.states:
                        for q2_prime in self.na.states:
                            for p in self.na.states:
                                for p_prime in self.na.states:
                                    for q1_seconde in q1_prime.transitions.get("a", []):
                                        if q1_seconde != q1:
                                            for q2_seconde in q2_prime.transitions.get("a", []):
                                                if q2_seconde != q2:
                                                    for b in self.na.alphabet:
                                                        self.model.add(self.path_variables[(p, p_prime, q1, q1_seconde, q2,
                                                                                            q2_seconde)] == True).only_enforce_if(
                                                            self.path_variables[(p, p_prime, q1, q1_prime, q2, q2_prime)],
                                                            self.position_variables[
                                                                (p_prime, q1_prime, q2_prime, a, "Adam")],
                                                            self.position_variables[
                                                                (p_prime, q1_seconde, q2_seconde, b, "Eve")]
                                                        )


    def cycle_closing(self):
        for a in self.na.alphabet:
            for q1 in self.na.states:
                for q1_prime in self.na.states:
                    for q2 in self.na.states:
                        for q2_prime in self.na.states:
                            for p in self.na.states:
                                for p_prime in self.na.states:
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
            for p in self.na.states:
                for q1 in self.na.states:
                    for q2 in self.na.states:
                        for a in self.na.alphabet:
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
    na = NA()
    i = NA.State('i')
    a = NA.State('a')
    a_prime = NA.State('a_prime')
    a_seconde = NA.State('a_seconde')
    a_third = NA.State('a_third')
    a_third.is_accepting = True
    b = NA.State('b')
    b_prime = NA.State('b_prime')
    b_seconde = NA.State('b_seconde')
    b_third = NA.State('b_third')
    b_third.is_accepting = True
    i.add_transition('x', a)
    a.add_transition('b', i)
    a.add_transition('a', a_prime)
    a_prime.add_transition('x', a_seconde)
    a_seconde.add_transition('a', a_third)
    a_third.add_transition('a', i)
    a_seconde.add_transition('b', b_prime)
    i.add_transition('x', b)
    b.add_transition('a', i)
    b.add_transition('b', b_prime)
    b_prime.add_transition('x', b_seconde)
    b_seconde.add_transition('b', b_third)
    b_third.add_transition('b', i)
    b_seconde.add_transition('a', a_prime)
    na.add_state(i)
    na.add_state(a)
    na.add_state(a_prime)
    na.add_state(a_seconde)
    na.add_state(a_third)
    na.add_state(b)
    na.add_state(b_prime)
    na.add_state(b_seconde)
    na.add_state(b_third)
    na.alphabet = {'x', 'b', 'a'}
    game = Game(na)
    game.solve()
    game.get_solution()
