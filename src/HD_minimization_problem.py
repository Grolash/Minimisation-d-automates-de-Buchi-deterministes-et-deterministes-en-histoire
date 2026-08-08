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
                transitions = []
                for q_prime in self.candidate_na.states:
                    transition_var = self.model.new_bool_var('')
                    self.candidate_transitions[(q, symbol, q_prime)] = transition_var
                    transitions.append(transition_var)
                self.model.add_at_least_one(transitions)
            self.candidate_states_acceptance[q] = self.model.new_bool_var('')

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
        self.adam_edge_variables = {}

        n = cand_na.size()
        for p in ref_na.states:
            for q in cand_na.states:
                for a in ref_na.alphabet:
                    self.position_variables[(p, q, a, "Adam")] = self.model.new_bool_var('')
                    self.mu_variables[(p, q, a, "Adam")] = self.model.new_int_var(0, n * n * len(ref_na.alphabet), '')
                    self.position_variables[(p, q, a, "Eve")] = self.model.new_bool_var('')
                    self.mu_variables[(p, q, a, "Eve")] = self.model.new_int_var(0, n * n * len(ref_na.alphabet), '')

                    p_primes: list[NA.State] = p.transitions.get(a, [])
                    for p_prime in p_primes:
                        self.strategy_variables[(p, q, a, p_prime)] = self.model.new_bool_var('')

                    for q_prime in cand_na.states:
                        for b in ref_na.alphabet:
                            adam_edge_variable = self.model.new_bool_var('')
                            self.adam_edge_variables[(p, q, a, q_prime, b)] = adam_edge_variable
                            self.model.add(adam_edge_variable == False).only_enforce_if(
                                self.candidate_transitions[(q, a, q_prime)].Not()
                            )


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

    def adam_edges(self):
        for p in self.ref_na.states:
            for q in self.cand_na.states:
                for a in self.ref_na.alphabet:
                    for q_prime in self.cand_na.states:
                        for b in self.ref_na.alphabet:
                            self.model.add(self.adam_edge_variables[(p, q, a, q_prime, b)] == True).only_enforce_if(
                                self.position_variables[(p, q, a, "Adam")],
                                self.candidate_transitions[(q, a, q_prime)]
                            )

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
                                self.adam_edge_variables[(p, q, a, q_prime, b)]
                            )

    def mu_condition(self):
        for p in self.ref_na.states:
            for q in self.cand_na.states:
                for a in self.ref_na.alphabet:
                    p_primes = p.transitions.get(a, [])
                    for p_prime in p_primes:
                        if not p_prime.is_accepting: # rank != 0
                            self.model.add(self.mu_variables[(p, q, a, "Eve")] >
                                           self.mu_variables[(p_prime, q, a, "Adam")]
                                           ).only_enforce_if(
                                self.strategy_variables[(p, q, a, p_prime)],
                                self.candidate_states_acceptance[q]  # rank 1 depends on a variable in this case
                            )

                            self.model.add(self.mu_variables[(p, q, a, "Eve")] >=
                                           self.mu_variables[(p_prime, q, a, "Adam")]
                                           ).only_enforce_if(
                                self.strategy_variables[(p, q, a, p_prime)],
                                self.candidate_states_acceptance[q].Not() # rank 2 only if neither accepting
                            )
                    for q_prime in self.cand_na.states:
                        if not p.is_accepting:
                            for b in self.ref_na.alphabet:
                                self.model.add(self.mu_variables[(p, q, a, "Adam")] >
                                               self.mu_variables[(p, q_prime, b, "Eve")]
                                               ).only_enforce_if(
                                    self.adam_edge_variables[(p, q, a, q_prime, b)],
                                    self.candidate_states_acceptance[q_prime]
                                    )

                            for b in self.ref_na.alphabet:
                                self.model.add(self.mu_variables[(p, q, a, "Adam")] >=
                                               self.mu_variables[(p, q_prime, b, "Eve")]
                                               ).only_enforce_if(
                                    self.adam_edge_variables[(p, q, a, q_prime, b)],
                                    self.candidate_states_acceptance[q_prime].Not()
                                    )


    def encode(self):
        self.eve_strategy()
        self.eve_adam_sequence()
        self.adam_edges()
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
                    self.mu_variables[(p, q, a, "Adam")] = self.model.new_int_var(0, n * n * len(cand_na.alphabet), '')
                    self.position_variables[(p, q, a, "Eve")] = self.model.new_bool_var('')
                    self.mu_variables[(p, q, a, "Eve")] = self.model.new_int_var(0, n * n * len(cand_na.alphabet), '')

                    for p_prime in cand_na.states:
                        strategy_variable = self.model.new_bool_var('')
                        self.strategy_variables[(p, q, a, p_prime)] = strategy_variable
                        self.model.add(strategy_variable == False).only_enforce_if(
                            self.candidate_transitions[(p, a, p_prime)].Not()
                            # Can't be true if no transition from p to p_prime.
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
                                self.position_variables[(p, q, a, "Adam")],
                                # Adam follows every edge,
                                # and here the transitions are known, so the edges are known
                            )

    def mu_condition(self):
        for p in self.cand_na.states:
            for q in self.ref_na.states:
                for a in self.cand_na.alphabet:
                    for p_prime in self.cand_na.states:
                        if q.is_accepting:
                            self.model.add(self.mu_variables[(p, q, a, "Eve")] >
                                           self.mu_variables[(p_prime, q, a, "Adam")]
                                           ).only_enforce_if(
                                self.strategy_variables[(p, q, a, p_prime)],
                                self.candidate_states_acceptance[p_prime].Not() # rank 1 only if p is not accepting
                            )
                        else:
                            self.model.add(self.mu_variables[(p, q, a, "Eve")] >=
                                           self.mu_variables[(p_prime, q, a, "Adam")]
                                           ).only_enforce_if(
                                self.strategy_variables[(p, q, a, p_prime)],
                                self.candidate_states_acceptance[p_prime].Not()
                            )

                    q_primes = q.transitions.get(a, [])
                    for q_prime in q_primes:
                        for b in self.cand_na.alphabet:
                            if q_prime.is_accepting:
                                self.model.add(self.mu_variables[(p, q, a, "Adam")] >
                                               self.mu_variables[(p, q_prime, b, "Eve")]
                                               ).only_enforce_if(
                                    self.position_variables[(p, q, a, "Adam")],
                                    self.position_variables[(p, q_prime, b, "Eve")],
                                    self.candidate_states_acceptance[p].Not() # rank 1 idem
                                )
                            else:
                                self.model.add(self.mu_variables[(p, q, a, "Adam")] >=
                                               self.mu_variables[(p, q_prime, b, "Eve")]
                                               ).only_enforce_if(
                                    self.position_variables[(p, q, a, "Adam")],
                                    self.position_variables[(p, q_prime, b, "Eve")],
                                    # ok because q -a-> q_prime in Delta is known
                                    self.candidate_states_acceptance[p].Not()  # rank 2 idem
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
        self.adam_edge_variables = {}

        n = cand_na.size()
        for p in cand_na.states:
            for q1 in cand_na.states:
                for q2 in cand_na.states:
                    for a in cand_na.alphabet:
                        self.position_variables[(p, q1, q2, a, "Adam")] = self.model.new_bool_var('')
                        self.mu_variables[(p, q1, q2, a, "Adam")] = self.model.new_int_var(0, n * n * n * len(cand_na.alphabet), '')
                        self.position_variables[(p, q1, q2, a, "Eve")] = self.model.new_bool_var('')
                        self.mu_variables[(p, q1, q2, a, "Eve")] = self.model.new_int_var(0, n * n * n * len(cand_na.alphabet), '')
                        for p_prime in cand_na.states:
                            strategy_variable = self.model.new_bool_var('')
                            self.strategy_variables[(p, q1, q2, a, p_prime)] = strategy_variable
                            self.model.add(strategy_variable == False).only_enforce_if(
                                self.candidate_transitions[(p, a, p_prime)].Not()
                                # Can't be true if no transition from p to p_prime, same as in GameBA
                            )
                        for q1_prime in cand_na.states:
                            for q2_prime in cand_na.states:
                                for b in cand_na.alphabet:
                                    adam_edge_variable = self.model.new_bool_var('')
                                    self.adam_edge_variables[(p, q1, q2, a, q1_prime, q2_prime, b)] = adam_edge_variable
                                    self.model.add(adam_edge_variable == False).only_enforce_if(
                                        self.candidate_transitions[(q1, a, q1_prime)].Not()
                                    )
                                    self.model.add(adam_edge_variable == False).only_enforce_if(
                                        self.candidate_transitions[(q2, a, q2_prime)].Not()
                                    )


    def eve_strategy(self):
        for p in self.cand_na.states:
            for q1 in self.cand_na.states:
                for q2 in self.cand_na.states:
                    for a in self.cand_na.alphabet:
                        strategy_variables = [self.strategy_variables[(p, q1, q2, a, p_prime)] for p_prime in
                                              self.cand_na.states]
                        self.model.add_exactly_one(strategy_variables).only_enforce_if(
                            self.position_variables[(p, q1, q2, a, "Eve")],
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

    def adam_eve_edges(self):
        for p in self.cand_na.states:
            for q1 in self.cand_na.states:
                for q2 in self.cand_na.states:
                    for a in self.cand_na.alphabet:
                        for q1_prime in self.cand_na.states:
                            for q2_prime in self.cand_na.states:
                                for b in self.cand_na.alphabet:
                                    edge_variable = self.adam_edge_variables[(p, q1, q2, a, q1_prime, q2_prime, b)]
                                    self.model.add(edge_variable == True).only_enforce_if(
                                        self.position_variables[(p, q1, q2, a, "Adam")],
                                        self.candidate_transitions[(q1, a, q1_prime)],
                                        self.candidate_transitions[(q2, a, q2_prime)]
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
                                        self.adam_edge_variables[(p, q1, q2, a, q1_prime, q2_prime, b)]
                                    )

    def mu_condition(self):
        for p in self.cand_na.states:
            for q1 in self.cand_na.states:
                for q2 in self.cand_na.states:
                    for a in self.cand_na.alphabet:
                        for p_prime in self.cand_na.states:
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
                            self.model.add(self.mu_variables[(p, q1, q2, a, "Eve")] >=
                                           self.mu_variables[(p_prime, q1, q2, a, "Adam")]
                                           ).only_enforce_if(
                                self.strategy_variables[(p, q1, q2, a, p_prime)],
                                self.candidate_states_acceptance[p_prime].Not(),
                                q1_or_q2.Not()
                                # rank 2 depends on a variable in this case
                            )

                        for q1_prime in self.cand_na.states:
                            for q2_prime in self.cand_na.states:
                                for b in self.cand_na.alphabet:
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
                                        self.adam_edge_variables[(p, q1, q2, a, q1_prime, q2_prime, b)],
                                        self.candidate_states_acceptance[p].Not(),
                                        q1_prime_or_q2_prime
                                    )
                                    self.model.add(self.mu_variables[(p, q1, q2, a, "Adam")] >=
                                                   self.mu_variables[(p, q1_prime, q2_prime, b, "Eve")]
                                                   ).only_enforce_if(
                                        self.adam_edge_variables[(p, q1, q2, a, q1_prime, q2_prime, b)],
                                        self.candidate_states_acceptance[p],
                                        q1_prime_or_q2_prime.Not()
                                    )

    def encode(self):
        self.eve_strategy()
        self.eve_adam_sequence()
        self.adam_eve_edges()
        self.adam_eve_sequence()
        self.mu_condition()


if __name__ == '__main__':
    from nta import NTA

    # too big...
    """GFG_nta = NTA()
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
    game.find_candidate_for_size(GFG_na.size()-1)"""

    fake_na = NA()  # actually deterministic but deterministic means HD
    print("Fake NA")
    q0 = NA.State('q0')
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
    fake_na.__repr__()
    print("Candidate NA:")
    game = HDMinimizationProblem(fake_na)
    game.find_candidate_for_size(fake_na.size()-1)

    print("------------------------------")

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

    print("Candidate NA:")
    game1 = HDMinimizationProblem(non_hd_na)
    game1.find_candidate_for_size(non_hd_na.size())








