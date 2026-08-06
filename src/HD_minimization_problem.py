from ortools.sat.python import cp_model

from src.na import NA


class HDMinimizationProblem:
    def __init__(self, na: NA):
        self.na = na
        self.model = cp_model.CpModel()

        self.candidate_na = NA()
        self.candidate_na.alphabet = na.alphabet
        self.candidate_transitions = {}
        self.candidate_states_acceptance = {}

        self.solver = cp_model.CpSolver()
        self.status = None


    def init_candidate_na(self, maxsize: int):
        for i in range(maxsize):
            state = NA.State(f'q{i}')
            self.candidate_na.add_state(state)

        for q in self.candidate_na.states:
            for symbol in self.candidate_na.alphabet:
                for q_prime in self.candidate_na.states:
                    self.candidate_transitions[(q, symbol, q_prime)] = self.model.new_bool_var('')
            self.candidate_states_acceptance[q] = self.model.new_bool_var('')
        self.model.add_at_least_one(self.candidate_states_acceptance.values())

    def find_candidate_for_size(self, maxsize: int):
        self.init_candidate_na(maxsize)
        game_ab = GameAB(self.na, self.candidate_na, self.candidate_transitions, self.candidate_states_acceptance, self.model)
        game_ab.encode()
        game_ba = GameBA(self.candidate_na, self.candidate_transitions, self.candidate_states_acceptance, self.na, self.model)
        game_ba.encode()
        game_g2 = GameG2(self.candidate_na, self.candidate_transitions, self.candidate_states_acceptance, self.model)
        game_g2.encode()
        self.status = self.solver.Solve(self.model)
        if self.status == cp_model.OPTIMAL:
            print("Solution found:")
            for p in self.candidate_na.states:
                for q in self.candidate_na.states:
                    for a in self.candidate_na.alphabet:
                        if self.solver.BooleanValue(self.candidate_transitions[(p, a, q)]):
                            print(f"Transition: {p.id} --{a}--> {q.id}")
            for q in self.candidate_na.states:
                if self.solver.BooleanValue(self.candidate_states_acceptance[q]):
                    print(f"Accepting state: {q.id}")
        else:
            print("No solution found.")


class GameAB:
    def __init__(self, ref_na: NA, cand_na: NA, candidate_transitions: dict, candidate_states_acceptance: dict, model: cp_model.CpModel):
        self.ref_na = ref_na
        self.cand_na = cand_na
        self.candidate_transitions = candidate_transitions
        self.candidate_states_acceptance = candidate_states_acceptance
        self.model = model
        self.position_variables = {}
        self.mu_variables = {}
        self.strategy_variables = {}
        # self.adam_edge_variables = {}

        n = cand_na.size()
        for p in ref_na.states:
            for q in cand_na.states:
                for a in ref_na.alphabet:
                    self.position_variables[(p, q, a, "Adam")] = self.model.new_bool_var('')
                    self.mu_variables[(p, q, a, "Adam")] = self.model.new_int_var(0, n * n * n * len(ref_na.alphabet), '')
                    self.position_variables[(p, q, a, "Eve")] = self.model.new_bool_var('')
                    self.mu_variables[(p, q, a, "Eve")] = self.model.new_int_var(0, n * n * n * len(ref_na.alphabet), '')

                    p_primes: list[NA.State] = p.transitions.get(a, [])
                    for p_prime in p_primes:
                        self.strategy_variables[(p, q, a, p_prime)] = self.model.new_bool_var('')

                    """for q_prime in cand_na.states:
                        for b in ref_na.alphabet:
                            adam_eve_edge = self.model.new_bool_var('')
                            self.adam_edge_variables[(p, q, a, "Adam", q_prime, b)] = adam_eve_edge
                            self.model.add(adam_eve_edge == False).only_enforce_if(
                                candidate_transitions[(q, a, q_prime)].Not())"""


    def eve_strategy(self):
        for p in self.ref_na.states:
            for q in self.cand_na.states:
                for a in self.ref_na.alphabet:
                    p_primes = p.transitions.get(a, [])
                    strategy_variables = [self.strategy_variables[(p, q, a, p_prime)] for p_prime in
                                          p_primes]
                    self.model.add_exactly_one(strategy_variables).only_enforce_if(
                        self.position_variables[(p, q, a, "Eve")]
                    )

    def eve_adam_sequence(self):
        for p in self.ref_na.states:
            for q in self.cand_na.states:
                for a in self.ref_na.alphabet:
                    p_primes = p.transitions.get(a, [])
                    for p_prime in p_primes:
                        self.model.add(self.position_variables[(p_prime, q, a, "Adam")] == True).only_enforce_if(
                            self.strategy_variables[(p, q, a, p_prime)]
                        )

    """def adam_edges(self):
        for p in self.ref_na.states:
            for q in self.cand_na.states:
                for a in self.ref_na.alphabet:
                    for q_prime in self.cand_na.states:
                        for b in self.ref_na.alphabet:
                            self.model.add(self.adam_edge_variables[(p, q, a, "Adam", q_prime, b)] == True).only_enforce_if(
                                self.position_variables[(p, q, a, "Adam")],
                                self.candidate_transitions[(q, a, q_prime)]
                            )"""

    def adam_eve_sequence(self):
        start_state_ref = self.ref_na.states[0]
        start_state_cand = self.cand_na.states[0]
        for a in self.ref_na.alphabet:
            self.model.add(self.position_variables[(start_state_ref, start_state_cand, a, "Eve")] == True)

        for p in self.ref_na.states:
            for a in self.ref_na.alphabet:
                for q in self.cand_na.states:
                    for q_prime in self.cand_na.states:
                        for b in self.ref_na.alphabet:
                            position_variable = self.position_variables[(p, q_prime, b, "Eve")]
                            self.model.add(position_variable == True).only_enforce_if(
                                self.position_variables[(p, q, a, "Adam")],
                                self.candidate_transitions[(q, a, q_prime)]
                                # Actually, no need for Adam-Eve edges because
                                # transitions variables check the same thing
                                # in the non-generic encoding?
                            )
                            self.model.add(position_variable == False).only_enforce_if(
                                self.candidate_transitions[(q, a, q_prime)].Not()
                                # Still need an iff tho. Contrary to other constraints
                                # that only make the solver shoot itself in the foot if variables are set to true
                                # when not enforced, this one would create wrong solutions if they could
                                # be set to true when not enforced.
                            )

    def mu_condition(self):
        for p in self.ref_na.states:
            for q in self.cand_na.states:
                for a in self.ref_na.alphabet:
                    p_primes = p.transitions.get(a, [])
                    for p_prime in p_primes:
                        if p_prime.is_accepting: # rank 2
                            self.model.add(self.mu_variables[(p, q, a, "Eve")] >=
                                           self.mu_variables[(p_prime, q, a, "Adam")]
                                           ).only_enforce_if(
                                self.strategy_variables[(p, q, a, p_prime)],
                            )
                        else: # rank != 2
                            self.model.add(self.mu_variables[(p, q, a, "Eve")] >
                                           self.mu_variables[(p_prime, q, a, "Adam")]
                                           ).only_enforce_if(
                                    self.strategy_variables[(p, q, a, p_prime)],
                                    self.candidate_states_acceptance[q] # rank 1 depends on a variable in this case
                                )

                    for q_prime in self.cand_na.states:
                        if p.is_accepting:
                            for b in self.ref_na.alphabet:
                                self.model.add(self.mu_variables[(p, q, a, "Adam")] >=
                                               self.mu_variables[(p, q_prime, b, "Eve")]
                                               ).only_enforce_if(
                                    self.position_variables[(p, q, a, "Adam")],
                                    self.position_variables[(p, q_prime, b, "Eve")],
                                    self.candidate_transitions[(q, a, q_prime)]
                                    )
                        else:
                            for b in self.ref_na.alphabet:
                                self.model.add(self.mu_variables[(p, q, a, "Adam")] >
                                               self.mu_variables[(p, q_prime, b, "Eve")]
                                               ).only_enforce_if(
                                    self.position_variables[(p, q, a, "Adam")],
                                    self.position_variables[(p, q_prime, b, "Eve")],
                                    self.candidate_transitions[(q, a, q_prime)],
                                    self.candidate_states_acceptance[q]
                                    )

    def encode(self):
        self.eve_strategy()
        self.eve_adam_sequence()
        self.adam_eve_sequence()
        self.mu_condition()

class GameBA:
    def __init__(self, cand_na: NA, candidate_transitions: dict, candidate_states_acceptance: dict, ref_na: NA, model: cp_model.CpModel):
        self.cand_na = cand_na
        self.candidate_transitions = candidate_transitions
        self.candidate_states_acceptance = candidate_states_acceptance
        self.ref_na = ref_na
        self.model = model
        self.position_variables = {}
        self.mu_variables = {}
        self.strategy_variables = {}

        n = cand_na.size()
        for p in cand_na.states:
            for q in ref_na.states:
                for a in cand_na.alphabet:
                    self.position_variables[(p, q, a, "Adam")] = self.model.new_bool_var('')
                    self.mu_variables[(p, q, a, "Adam")] = self.model.new_int_var(0, n * n * n * len(cand_na.alphabet), '')
                    self.position_variables[(p, q, a, "Eve")] = self.model.new_bool_var('')
                    self.mu_variables[(p, q, a, "Eve")] = self.model.new_int_var(0, n * n * n * len(cand_na.alphabet), '')

                    for p_prime in cand_na.states:
                        strategy_variable = self.model.new_bool_var('')
                        self.strategy_variables[(p, q, a, p_prime)] = strategy_variable
                        self.model.add(strategy_variable == False).only_enforce_if(
                            self.candidate_transitions[(p, a, p_prime)].Not()
                            # Can't be true if no transition from p to p_prime.
                            # Here we still need an edge (strategy) variable because not all possible edges
                            # are chosen by Eve, only one of them
                        )

    def eve_strategy(self):
        for p in self.cand_na.states:
            for q in self.ref_na.states:
                for a in self.cand_na.alphabet:
                    strategy_variables = [self.strategy_variables[(p, q, a, p_prime)] for p_prime in
                                          self.cand_na.states]
                    self.model.add_exactly_one(strategy_variables).only_enforce_if(
                        self.position_variables[(p, q, a, "Eve")],
                    )

    def eve_adam_sequence(self):
        for p in self.cand_na.states:
            for q in self.ref_na.states:
                for a in self.cand_na.alphabet:
                    for p_prime in self.cand_na.states:
                        self.model.add(self.position_variables[(p_prime, q, a, "Adam")] == True).only_enforce_if(
                            self.strategy_variables[(p, q, a, p_prime)]
                        )

    def adam_eve_sequence(self):
        start_state_cand = self.cand_na.states[0]
        start_state_ref = self.ref_na.states[0]
        for a in self.cand_na.alphabet:
            self.model.add(self.position_variables[(start_state_cand, start_state_ref, a, "Eve")] == True)

        for p in self.cand_na.states:
            for a in self.cand_na.alphabet:
                for q in self.ref_na.states:
                    q_primes = q.transitions.get(a, [])
                    for q_prime in q_primes:
                        for b in self.cand_na.alphabet:
                            position_variable = self.position_variables[(p, q_prime, b, "Eve")]
                            self.model.add(position_variable == True).only_enforce_if(
                                self.position_variables[(p, q, a, "Adam")], # Adam follows every edge
                            )

    def mu_condition(self):
        for p in self.cand_na.states:
            for q in self.ref_na.states:
                for a in self.cand_na.alphabet:
                    for p_prime in self.cand_na.states:
                        self.model.add(self.mu_variables[(p, q, a, "Eve")] >=
                                       self.mu_variables[(p_prime, q, a, "Adam")]
                                       ).only_enforce_if(
                            self.strategy_variables[(p, q, a, p_prime)],
                            self.candidate_states_acceptance[p_prime] # rank 2 depends on a variable in this case
                        )
                        if q.is_accepting:
                            self.model.add(self.mu_variables[(p, q, a, "Eve")] >
                                           self.mu_variables[(p_prime, q, a, "Adam")]
                                           ).only_enforce_if(
                                self.strategy_variables[(p, q, a, p_prime)],
                                self.candidate_states_acceptance[p_prime].Not() # rank 1 only if p is not accepting
                            )

                    q_primes = q.transitions.get(a, [])
                    for q_prime in q_primes:
                        for b in self.cand_na.alphabet:
                            self.model.add(self.mu_variables[(p, q, a, "Adam")] >=
                                           self.mu_variables[(p, q_prime, b, "Eve")]
                                           ).only_enforce_if(
                                self.position_variables[(p, q, a, "Adam")],
                                self.position_variables[(p, q_prime, b, "Eve")],
                                self.candidate_states_acceptance[p] # rank 2 idem
                            )
                            if q_prime.is_accepting:
                                self.model.add(self.mu_variables[(p, q, a, "Adam")] >
                                               self.mu_variables[(p, q_prime, a, "Eve")]
                                               ).only_enforce_if(
                                    self.position_variables[(p, q, a, "Adam")],
                                    self.position_variables[(p, q_prime, a, "Eve")],
                                    self.candidate_states_acceptance[p].Not() # rank 1 idem
                                )

    def encode(self):
        self.eve_strategy()
        self.eve_adam_sequence()
        self.adam_eve_sequence()
        self.mu_condition()

class GameG2:
    def __init__(self, cand_na: NA, candidate_transitions: dict, candidate_states_acceptance: dict, model: cp_model.CpModel):
        self.cand_na = cand_na
        self.candidate_transitions = candidate_transitions
        self.candidate_states_acceptance = candidate_states_acceptance
        self.model = model
        self.position_variables = {}
        self.mu_variables = {}
        self.strategy_variables = {}

        n = cand_na.size()
        for p in cand_na.states:
            for q_1 in cand_na.states:
                for q_2 in cand_na.states:
                    for a in cand_na.alphabet:
                        self.position_variables[(p, q_1, q_2, a, "Adam")] = self.model.new_bool_var('')
                        self.mu_variables[(p, q_1, q_2, a, "Adam")] = self.model.new_int_var(0, n * n * n * len(cand_na.alphabet), '')
                        self.position_variables[(p, q_1, q_2, a, "Eve")] = self.model.new_bool_var('')
                        self.mu_variables[(p, q_1, q_2, a, "Eve")] = self.model.new_int_var(0, n * n * n * len(cand_na.alphabet), '')
                        for p_prime in cand_na.states:
                            strategy_variable = self.model.new_bool_var('')
                            self.strategy_variables[(p, q_1, q_2, a, p_prime)] = strategy_variable
                            self.model.add(strategy_variable == False).only_enforce_if(
                                self.candidate_transitions[(p, a, p_prime)].Not()
                                # Can't be true if no transition from p to p_prime, same as in GameBA
                            )

    def eve_strategy(self):
        for p in self.cand_na.states:
            for q_1 in self.cand_na.states:
                for q_2 in self.cand_na.states:
                    for a in self.cand_na.alphabet:
                        strategy_variables = [self.strategy_variables[(p, q_1, q_2, a, p_prime)] for p_prime in
                                              self.cand_na.states]
                        self.model.add_exactly_one(strategy_variables).only_enforce_if(
                            self.position_variables[(p, q_1, q_2, a, "Eve")],
                        )

    def eve_adam_sequence(self):
        for p in self.cand_na.states:
            for q1 in self.cand_na.states:
                for q2 in self.cand_na.states:
                    for a in self.cand_na.alphabet:
                        for p_prime in self.cand_na.states:
                            self.model.add(self.position_variables[(p_prime, q1, q2, a, "Adam")] == True).only_enforce_if(
                                self.strategy_variables[(p, q1, q2, a, p_prime)]
                            )

    def adam_eve_sequence(self):
        start_state = self.cand_na.states[0]
        for a in self.cand_na.alphabet:
            self.model.add(self.position_variables[(start_state, start_state, start_state, a, "Eve")] == True)

        for p in self.cand_na.states:
            for q1 in self.cand_na.states:
                for q2 in self.cand_na.states:
                    for a in self.cand_na.alphabet:
                        for q1_prime in self.cand_na.states:
                            for q2_prime in self.cand_na.states:
                                for b in self.cand_na.alphabet:
                                    position_variable = self.position_variables[(p, q1_prime, q2_prime, b, "Eve")]
                                    self.model.add(position_variable == True).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")],
                                        self.candidate_transitions[(q1, a, q1_prime)],
                                        self.candidate_transitions[(q2, a, q2_prime)]
                                    )
                                    self.model.add(position_variable == False).only_enforce_if(
                                        self.candidate_transitions[(q1, a, q1_prime)].Not()
                                    )
                                    self.model.add(position_variable == False).only_enforce_if(
                                        self.candidate_transitions[(q2, a, q2_prime)].Not()
                                    )

    def mu_condition(self):
        for p in self.cand_na.states:
            for q1 in self.cand_na.states:
                for q2 in self.cand_na.states:
                    for a in self.cand_na.alphabet:
                        for p_prime in self.cand_na.states:
                            self.model.add(self.mu_variables[(p, q1, q2, a, "Eve")] >=
                                           self.mu_variables[(p_prime, q1, q2, a, "Adam")]
                                           ).only_enforce_if(
                                self.strategy_variables[(p, q1, q2, a, p_prime)],
                                self.candidate_states_acceptance[p_prime]
                                # rank 2 depends on a variable in this case
                            )
                            q1_or_q2 = self.model.new_bool_var('')
                            self.model.add_bool_or(self.candidate_states_acceptance[q1],
                                                   self.candidate_states_acceptance[q2]
                                                   ).only_enforce_if(
                                q1_or_q2
                            )
                            self.model.add_bool_and(self.candidate_states_acceptance[q1].Not(),
                                                    self.candidate_states_acceptance[q2].Not()
                                                    ).only_enforce_if(
                                q1_or_q2.Not()
                            )
                            # this just means q1_or_q2 <=> (q1 or q2)
                            # I did this because I can't only_enforce_if on a boolean expression, only on a variable

                            self.model.add(self.mu_variables[(p, q1, q2, a, "Eve")] >
                                           self.mu_variables[(p_prime, q1, q2, a, "Adam")]
                                           ).only_enforce_if(
                                self.strategy_variables[(p, q1, q2, a, p_prime)],
                                self.candidate_states_acceptance[p_prime].Not(),
                                q1_or_q2
                            )

                        for q1_prime in self.cand_na.states:
                            for q2_prime in self.cand_na.states:
                                for b in self.cand_na.alphabet:
                                    self.model.add(self.mu_variables[(p, q1, q2, a, "Adam")] >=
                                                   self.mu_variables[(p, q1_prime, q2_prime, b, "Eve")]
                                                   ).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")],
                                        self.position_variables[(p, q1_prime, q2_prime, b, "Eve")],
                                        self.candidate_transitions[(q1, a, q1_prime)],
                                        self.candidate_transitions[(q2, a, q2_prime)],
                                        self.candidate_states_acceptance[p]
                                    )
                                    q1_prime_or_q2_prime = self.model.new_bool_var('')
                                    self.model.add_bool_or(self.candidate_states_acceptance[q1_prime],
                                                           self.candidate_states_acceptance[q2_prime]
                                                           ).only_enforce_if(
                                        q1_prime_or_q2_prime
                                    )
                                    self.model.add_bool_and(self.candidate_states_acceptance[q1_prime].Not(),
                                                            self.candidate_states_acceptance[q2_prime].Not()
                                                            ).only_enforce_if(
                                        q1_prime_or_q2_prime.Not()
                                    )
                                    self.model.add(self.mu_variables[(p, q1, q2, a, "Adam")] >
                                                   self.mu_variables[(p, q1_prime, q2_prime, b, "Eve")]
                                                   ).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")],
                                        self.position_variables[(p, q1_prime, q2_prime, b, "Eve")],
                                        self.candidate_transitions[(q1, a, q1_prime)],
                                        self.candidate_transitions[(q2, a, q2_prime)],
                                        self.candidate_states_acceptance[p].Not(),
                                        q1_prime_or_q2_prime
                                    )

    def encode(self):
        self.eve_strategy()
        self.eve_adam_sequence()
        self.adam_eve_sequence()
        self.mu_condition()


if __name__ == '__main__':
    from nta import NTA

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
    GFG_na = GFG_nta.to_na()

    print("GFG NA:")
    game = HDMinimizationProblem(GFG_na)
    game.find_candidate_for_size(GFG_na.size()-1)







