import copy

from ortools.sat.python import cp_model
from itertools import combinations

from ortools.sat.python.cp_model import OPTIMAL

from tga import TGA


def powerset(s):
    return frozenset(frozenset(comb) for r in range(len(s) + 1) for comb in combinations(s, r))


class TGBuchiMinimizationProblem:
    def __init__(self, reference_tga: TGA, maxsize: int, maxsets: int, deterministic: bool = True):
        self.reference_tga = reference_tga
        self.candidate_tga = TGA()
        self.deterministic = deterministic
        self.model = cp_model.CpModel()
        self.size = maxsize  # |Q_c| = n
        self.maxsets = maxsets  # |F_c| = m
        self.sccr = self.reference_tga.non_trivial_sccs()  # SCCs of the reference TGA (i.e. R)
        self.f_r = frozenset(range(reference_tga.num_acceptance_sets))
        self.f_c = frozenset(range(maxsets))

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
                reachable_state = self.model.new_bool_var(f'[{q.id},{q_prime.id},{q.id},{q_prime.id},{frozenset()},{frozenset()}]')
                self.product_reachable_states[(q, q_prime, q, q_prime, frozenset(), frozenset())] = reachable_state

        self.product_path_variables = {}
        for q1 in self.candidate_tga.states:
            for q2 in self.candidate_tga.states:
                for s in self.sccr:
                    for q1_prime in s:
                        for q2_prime in s:
                            for f in self.fs:
                                for f_prime in self.f_primes:
                                    product_path_variable = self.model.new_bool_var(
                                        f'[{q1.id},{q1_prime.id},{q2.id},{q2_prime.id},{f},{f_prime}]')
                                    self.product_path_variables[(q1, q1_prime, q2, q2_prime, f, f_prime)] = product_path_variable

        self.product_variables = self.product_reachable_states
        self.product_variables.update(self.product_path_variables)

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
                                               frozenset(), frozenset())] == True)
        for q1 in self.candidate_tga.states:
            for q2 in self.candidate_tga.states:
                for q1_prime in self.reference_tga.states:
                    for s in self.reference_tga.alphabet:
                        q2_prime = q1_prime.transitions[s].target
                        self.model.add(self.product_variables[(q2, q2_prime, q2, q2_prime, frozenset(), frozenset())] == True).only_enforce_if(
                            self.product_variables[(q1, q1_prime, q1, q1_prime, frozenset(), frozenset())],
                            self.candidate_transitions[q1, s, q2])

    def three(self):
        for q1 in self.candidate_tga.states:
            for q2 in self.candidate_tga.states:
                for q3 in self.candidate_tga.states:
                    for symbol in self.reference_tga.alphabet:
                        for f in self.fs:
                            for g in self.fs:
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
                                g_memberships = self.model.new_bool_var(f'{g}_memberships')
                                g_not_memberships = self.model.new_bool_var(f'{g}_not_memberships')
                                self.model.add_bool_and(a_in_g_memberships).only_enforce_if(g_memberships)
                                self.model.add_bool_or([v.Not() for v in a_in_g_memberships]).only_enforce_if(g_memberships.Not())
                                self.model.add_bool_and([v.Not() for v in a_not_in_g_memberships]).only_enforce_if(
                                    g_not_memberships)
                                self.model.add_bool_or(a_not_in_g_memberships).only_enforce_if(g_not_memberships.Not())
                                for s in self.sccr:
                                    for q1_prime in s:
                                        for q2_prime in s:
                                            for f_prime in self.f_primes:
                                                q3_prime = q2_prime.transitions[symbol].target
                                                acc_q2_prime_symbol_q3_prime = q2_prime.transitions[symbol].acceptance_sets
                                                (self.model.add(self.product_variables[
                                                                   (q1, q1_prime, q3, q3_prime, frozenset(f.union(g)),
                                                                    frozenset(f_prime.union(acc_q2_prime_symbol_q3_prime)))] == True)
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
                                                non_acceptance_check = []
                                                for acceptance_set in self.f_c.difference(f):
                                                    non_acceptance_check.append(self.candidate_transition_acceptance_set_memberships[
                                                            q2, symbol, q1, acceptance_set])
                                                self.model.add_at_least_one([v.Not() for v in non_acceptance_check]).only_enforce_if(
                                                                                self.product_variables[
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

    def solve(self):
        self.one()
        self.two()
        self.three()
        self.four_and_five()
        self.status = self.solver.solve(self.model)
        return self.status

    def get_solution(self):
        if self.status == cp_model.OPTIMAL:
            print("Solution found:")
            for q1 in self.candidate_tga.states:
                for symbol in self.reference_tga.alphabet:
                    for q2 in self.candidate_tga.states:
                        if self.solver.Value(self.candidate_transitions[q1, symbol, q2]) == 1:
                            print(f"Transition: {q1.id} --{symbol}--> {q2.id}")
                            acceptance_sets = []
                            for acceptance_set in range(self.maxsets):
                                if self.solver.Value(self.candidate_transition_acceptance_set_memberships[q1, symbol, q2, acceptance_set]) == 1:
                                    acceptance_sets.append(acceptance_set)
                            print(f"Acceptance sets: {acceptance_sets}")
        else:
            print("No solution found")

def find_minimal_solution(reference_tga: TGA, deterministic: bool = True):
    print("Original automaton size: ", reference_tga.size(), "; original number of acceptance sets: ", reference_tga.num_acceptance_sets)
    maxsize = reference_tga.size()-1
    maxsets = reference_tga.num_acceptance_sets
    solution_exists, problem = solve_for(reference_tga, maxsize, maxsets, deterministic)
    if solution_exists:
        problem.get_solution()
    else:
        print("No solution found")

def solve_for(reference_tga: TGA, maxsize, maxsets, deterministic: bool = True):
    if maxsize >= 1:
        print("Solving for size: ", maxsize, "; number of acceptance sets: ", maxsets)
        problem = TGBuchiMinimizationProblem(reference_tga, maxsize, maxsets, deterministic)
        solution_exists = problem.solve()
        if solution_exists in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print("Solution found for size: ", maxsize, "; number of acceptance sets: ", maxsets)
            smaller_problem = solve_for(reference_tga, maxsize-1, maxsets, deterministic)
            if smaller_problem[0]:
                return smaller_problem
            else:
                print("Minimal size found: ", maxsize, "; number of acceptance sets: ", maxsets)
                return True, problem
        print("No solution found for size: ", maxsize, "; number of acceptance sets: ", maxsets, "\nEnd of search.\n")
        return False, None
    else:
        print("Reached invalid size 0.")
        return False, None




if __name__ == '__main__':
    reference_tga = TGA(2)
    q0 = TGA.State('q0')
    q1 = TGA.State('q1')
    q0.add_transition('a', q1, acceptance_sets={0,1})
    q1.add_transition('b', q0, acceptance_sets={0,1})
    q0.add_transition('b', q0, acceptance_sets={0})
    q1.add_transition('a', q1, acceptance_sets={0})
    reference_tga.add_state(q0)
    reference_tga.add_state(q1)
    reference_tga.alphabet = {'a', 'b'}
    print(reference_tga.__repr__())
    find_minimal_solution(reference_tga)