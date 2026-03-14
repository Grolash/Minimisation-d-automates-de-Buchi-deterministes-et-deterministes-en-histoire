import copy

from ortools.sat.python import cp_model
from itertools import combinations

from tga import TGA


def powerset(s):
    return set(frozenset(comb) for r in range(len(s) + 1) for comb in combinations(s, r))


class TGBuchiMinimizationProblem:
    def __init__(self, reference_tga: TGA, maxsize: int, maxsets: int, deterministic: bool = False):
        self.reference_tga = reference_tga
        self.candidate_tga = TGA()
        self.deterministic = deterministic
        self.model = cp_model.CpModel()
        self.size = maxsize  # |Q_c| = n
        self.maxsets = maxsets  # |F_c| = m
        self.sccr = self.reference_tga.non_trivial_sccs()  # SCCs of the reference TGA (i.e. R)
        self.f_r = set(range(reference_tga.num_acceptance_sets))
        self.f_c = set(range(maxsets))

        self.fs = powerset(self.f_c)
        self.f_primes = powerset(self.f_r)

        for i in range(maxsize):
            state = TGA.State(f'q{i}')
            self.candidate_tga.add_state(state)

        self.candidate_transitions = {}
        for q1 in self.candidate_tga.states:
            for symbol in self.reference_tga.alphabet:
                for q2 in self.candidate_tga.states:
                    self.candidate_transitions[q1, symbol, q2] = self.model.new_bool_var(
                        f'transition_{q1.id}_{symbol}_{q2.id}')

        self.candidate_transition_acceptance_set_memberships = {}
        for q1 in self.candidate_tga.states:
            for symbol in self.reference_tga.alphabet:
                for q2 in self.candidate_tga.states:
                    for acceptance_set in range(self.maxsets):
                        self.candidate_transition_acceptance_set_memberships[q1, symbol, q2, acceptance_set] = (
                            self.model.new_bool_var(
                                f'transition_{q1.id}_{symbol}_{q2.id}_in_acceptance_set_{acceptance_set}'))

        self.product_reachable_states = {}
        for q in self.candidate_tga.states:
            for q_prime in self.reference_tga.states:
                reachable_state = self.model.new_bool_var(f'[{q.id},{q_prime.id},{q.id},{q_prime.id},{set()},{set()}]')
                self.product_reachable_states[(q, q_prime, q, q_prime, set(), set())] = reachable_state

        self.product_path_variables = {}
        for q1 in self.candidate_tga.states:
            for q1_prime in self.sccr:
                for q2 in self.candidate_tga.states:
                    for q2_prime in self.sccr:
                        for f in self.fs:
                            for f_prime in self.f_primes:
                                product_path_variable = self.model.new_bool_var(
                                    f'[{q1.id},{q1_prime.id},{q2.id},{q2_prime.id},{f},{f_prime}]')
                                self.product_path_variables[(q1, q1_prime, q2, q2_prime, f, f_prime)] = product_path_variable

        self.product_variables = self.product_reachable_states.update(self.product_path_variables)

        self.solver = cp_model.CpSolver()
        self.status = None


    def one(self): #totality
        for q1 in self.candidate_tga.states:
            for symbol in self.reference_tga.alphabet:
                if self.deterministic:
                    self.model.add_exactly_one(
                        self.candidate_transitions[q1, symbol, q2] for q2 in self.candidate_tga.states)
                else:
                    self.model.add_at_least_one(
                        self.candidate_transitions[q1, symbol, q2] for q2 in self.candidate_tga.states)

    def two(self):
        self.model.add(self.product_variables[(self.candidate_tga.states[0], self.reference_tga.states[0],
                                               self.candidate_tga.states[0], self.reference_tga.states[0],
                                               set(), set())] == True)
        for q1 in self.candidate_tga.states:
            for q2 in self.candidate_tga.states:
                for q1_prime in self.reference_tga.states:
                    for s in self.reference_tga.alphabet:
                        q2_prime = q1_prime.transitions[s].target
                        self.model.add(self.product_variables[(q2, q2_prime, q2, q2_prime, set(), set())] == True).only_enforce_if(
                            self.product_variables[(q1, q1_prime, q1, q1_prime, set(), set())],
                            self.candidate_transitions[q1, s, q2])

    def three(self):
        for q1 in self.candidate_tga.states:
            for q2 in self.candidate_tga.states:
                for q3 in self.candidate_tga.states:
                    for symbol in self.reference_tga.alphabet:
                        for f in self.fs:
                            for g in self.fs:
                                for s in self.sccr:
                                    for q1_prime in s:
                                        for q2_prime in s:
                                            for f_prime in self.f_primes:
                                                q3_prime = q2_prime.transitions[symbol].target
                                                a_in_g_memberships = []
                                                a_not_in_g_memberships = []
                                                for acceptance_set in range(self.maxsets):
                                                    if acceptance_set in g:
                                                        a_in_g_memberships.append(
                                                            self.candidate_transition_acceptance_set_memberships[
                                                                q2, symbol, q3, acceptance_set])
                                                    else:
                                                        a_not_in_g_memberships.append(
                                                            self.candidate_transition_acceptance_set_memberships[
                                                                q2, symbol, q3, acceptance_set])
                                                acc_q2_prime_symbol_q3_prime = q2_prime.transitions[symbol].acceptance_sets
                                                g_memberships = self.model.new_bool_var(f'{g}_memberships')
                                                g_not_memberships = self.model.new_bool_var(f'{g}_not_memberships')
                                                self.model.add_bool_and(a_in_g_memberships).only_enforce_if(g_memberships)
                                                self.model.add_bool_and([v.Not() for v in a_not_in_g_memberships]).only_enforce_if(g_not_memberships)
                                                (self.model.add(self.product_variables[
                                                                   (q1, q1_prime, q3, q3_prime, f.union(g),
                                                                    f_prime.union(acc_q2_prime_symbol_q3_prime))] == True)
                                                 .only_enforce_if(
                                                    self.product_variables[(q1, q1_prime, q2, q2_prime, f, f_prime)],
                                                    self.candidate_transitions[q2, symbol, q3],
                                                    g_memberships,
                                                    g_not_memberships,
                                                ))

    def four_and_five(self):
        for q1 in self.candidate_tga.states:
            for q2 in self.candidate_tga.states:
                for symbol in self.reference_tga.alphabet:
                    for f in self.fs:
                        for s in self.sccr:
                            for q1_prime in s:
                                for q2_prime in s:
                                    for f_prime in self.f_primes:
                                        q3_prime = q2_prime.transitions[symbol].target
                                        acc_q2_prime_symbol_q3_prime = q2_prime.transitions[symbol].acceptance_sets
                                        if q3_prime == q1_prime:
                                            if f_prime.union(acc_q2_prime_symbol_q3_prime) != self.f_r:
                                                for acceptance_set in self.f_c.difference(f):
                                                    self.model.add(
                                                        self.candidate_transition_acceptance_set_memberships[
                                                            q2, symbol, q1, acceptance_set]
                                                        == False).only_enforce_if(self.product_variables[
                                                                                      (q1, q1_prime, q2, q2_prime, f,
                                                                                       f_prime)],
                                                                                  self.candidate_transitions[
                                                                                      q2, symbol, q1])
                                            elif f_prime.union(acc_q2_prime_symbol_q3_prime) == self.f_r:
                                                for acceptance_set in self.f_c.difference(f):
                                                    self.model.add(
                                                        self.candidate_transition_acceptance_set_memberships[
                                                            q2, symbol, q1, acceptance_set]
                                                        == True).only_enforce_if(self.product_variables[
                                                                                      (q1, q1_prime, q2, q2_prime, f,
                                                                                       f_prime)],
                                                                                  self.candidate_transitions[
                                                                                      q2, symbol, q1])





if __name__ == '__main__':
    test_set = {1, 2, 3}
    test_powerset = powerset(test_set)
    print(test_powerset)
    for i in test_powerset:
        print(i, len(i))
        for j in i:
            print(j)
    print(set([1, 2]) == frozenset([1, 2]))
    print(set([2, 1]) == frozenset([1, 2]))
    print(set([1, 2]) == frozenset([2, 1]))
    print({1, 2} == frozenset([2, 1]))
    print({1} == frozenset([1]))
    print({1} == frozenset({1}))
    a = {'a': 3, 'b': 2, 'c': 1}
    b = {'g': 2, 'f': 1, 'e': 12, 'a': 1}
    a.update(b)
    print(a)