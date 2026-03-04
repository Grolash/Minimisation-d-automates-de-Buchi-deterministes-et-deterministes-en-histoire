from ortools.sat.python import cp_model

from automaton import Automaton

class BuchiMinimizationProblem:
    def __init__(self, reference_automaton : Automaton, maxsize : int, deterministic : bool = False):
        self.reference_automaton = reference_automaton
        self.candidate_automaton = Automaton()
        self.deterministic = deterministic
        self.alphabet = reference_automaton.alphabet
        self.model = cp_model.CpModel()
        self.size = maxsize

        for i in range(maxsize):
            state = Automaton.State(f'q{i}')
            self.candidate_automaton.add_state(state)

        self.candidate_transitions = {}
        for q1 in self.candidate_automaton.states:
            for symbol in self.alphabet:
                for q2 in self.candidate_automaton.states:
                    self.candidate_transitions[q1, symbol, q2] = self.model.new_bool_var(f'transition_{q1.id}_{symbol}_{q2.id}')

        self.candidate_accepting_states = {}
        for q in self.candidate_automaton.states:
            self.candidate_accepting_states[q] = self.model.new_bool_var(f'accepting_{q.id}')

        self.product_states = {}
        for state in self.candidate_automaton.states:
            for state_prime in self.reference_automaton.states:
                product_state = self.model.new_bool_var(f'[{state.id},{state_prime.id}]G')
                self.product_states[(state, state_prime)] = product_state

        self.product_non_accepting_reference_path = {}
        self.product_non_accepting_candidate_path = {}
        for q1 in self.candidate_automaton.states:
            for q1_prime in self.reference_automaton.states:
                for q2 in self.candidate_automaton.states:
                    for q2_prime in self.reference_automaton.states:
                        self.product_non_accepting_reference_path[(q1, q1_prime, q2, q2_prime)] = self.model.new_bool_var(f'[{q1.id},{q1_prime.id},{q2.id},{q2_prime.id}]N')
                        self.product_non_accepting_candidate_path[(q1, q1_prime, q2, q2_prime)] = self.model.new_bool_var(f'[{q1.id},{q1_prime.id},{q2.id},{q2_prime.id}]A')


        self.solver = cp_model.CpSolver()
        self.status = None


    def one(self): #totality
        for q1 in self.candidate_automaton.states:
            for symbol in self.alphabet:
                if self.deterministic:
                    self.model.add_exactly_one(
                        self.candidate_transitions[q1, symbol, q2] for q2 in self.candidate_automaton.states)
                else:
                    self.model.add_at_least_one(
                        self.candidate_transitions[q1, symbol, q2] for q2 in self.candidate_automaton.states)


    def two(self):
        for q1 in self.candidate_automaton.states:
            for q2 in self.candidate_automaton.states:
                for q_prime in self.reference_automaton.states:
                    for s in self.alphabet:
                        delta = q_prime.transitions[s]
                        self.model.add(self.product_states[(q2, delta)] == True).only_enforce_if(
                            self.candidate_transitions[q1, s, q2], self.product_states[(q1, q_prime)])

    def three_and_five(self):
        for q1 in self.candidate_automaton.states:
            for q2 in self.candidate_automaton.states:
                for q3 in self.candidate_automaton.states:
                    for s in self.alphabet:
                        for q1_prime in self.reference_automaton.states:
                            for q2_prime in self.reference_automaton.states:
                                delta = q2_prime.transitions[s]
                                #three
                                if (not delta.is_accepting) and ((q1_prime != delta) | (q1 != q3)):
                                    (self.model.add(
                                        self.product_non_accepting_reference_path[(q1, q1_prime, q3, delta)] == True)
                                        .only_enforce_if(self.candidate_transitions[q2, s, q3],
                                                         self.product_non_accepting_reference_path[
                                                             (q1, q1_prime, q2, q2_prime)]))
                                #five
                                if (q1_prime.is_accepting) and ((q1_prime != delta) | (q1 != q3)):
                                    (self.model.add(
                                        self.product_non_accepting_candidate_path[(q1, q1_prime, q3, delta)] == True)
                                        .only_enforce_if(self.product_non_accepting_candidate_path[(q1, q1_prime, q2, q2_prime)],
                                                         self.candidate_transitions[q2, s, q3],
                                                         self.candidate_accepting_states[q3].Not()))

    def four_six(self):
        for q1 in self.candidate_automaton.states:
            for q2 in self.candidate_automaton.states:
                for q1_prime in self.reference_automaton.states:
                    for q2_prime in self.reference_automaton.states:
                        for s in self.alphabet:
                            delta = q2_prime.transitions[s]
                            if q1_prime == delta:
                                # four
                                if not q1_prime.is_accepting:
                                    self.model.add(self.candidate_accepting_states[q1] == False).only_enforce_if(
                                        self.product_non_accepting_reference_path[(q1, q1_prime, q2, q2_prime)],
                                        self.candidate_transitions[q2, s, q1])
                                # six
                                elif q1_prime.is_accepting:
                                    self.model.add(self.candidate_accepting_states[q1] == True).only_enforce_if(
                                        self.product_non_accepting_candidate_path[(q1, q1_prime, q2, q2_prime)],
                                        self.candidate_transitions[q2, s, q1]
                                    )

    def seven(self):
        self.model.add(self.product_states[(self.candidate_automaton.states[0], self.reference_automaton.states[0])] == True)
        for q in self.candidate_automaton.states:
            for q_prime in self.reference_automaton.states:
                self.model.add(self.product_non_accepting_reference_path[(q, q_prime, q, q_prime)] == True).only_enforce_if(
                    self.product_states[(q, q_prime)])
                self.model.add(self.product_non_accepting_candidate_path[(q, q_prime, q, q_prime)] == True).only_enforce_if(
                    self.product_states[(q, q_prime)])

    def solve(self):
        self.one()
        self.two()
        self.three_and_five()
        self.four_six()
        self.seven()
        self.status = self.solver.solve(self.model)
        return self.status == cp_model.OPTIMAL

    def get_solution(self):
        if self.status == cp_model.OPTIMAL:
            print("Solution found:")
            for q1 in self.candidate_automaton.states:
                for symbol in self.alphabet:
                    for q2 in self.candidate_automaton.states:
                        if self.solver.Value(self.candidate_transitions[q1, symbol, q2]) == 1:
                            print(f"Transition: {q1.id} --{symbol}--> {q2.id}")
            for q in self.candidate_automaton.states:
                if self.solver.Value(self.candidate_accepting_states[q]) == 1:
                    print(f"Accepting state: {q.id}")
        else:
            print("No solution found")


def find_minimal_solution(reference_automaton : Automaton):
    print("Original automaton size: ", reference_automaton.size(), "")
    solution_exists, problem = solve_for(reference_automaton, reference_automaton.size()-1)
    if solution_exists:
        problem.get_solution()
    else:
        print("No solution found")



def solve_for(reference_automaton : Automaton, size : int):
    if size >= 1:
        print("Solving for size: ", size, "")
        problem = BuchiMinimizationProblem(reference_automaton, size)
        solution_exists = problem.solve()
        if solution_exists:
            print("Solution found for size: ", size, "")
            smaller_problem = solve_for(reference_automaton, size - 1)
            if smaller_problem[0]:
                return smaller_problem
            else:
                print("Minimal size found: ", size, "")
                return solution_exists, problem
        print("No solution found for size: ", size, "\nEnd of search.\n")
        return False, None
    else:
        print("Reached invalid size 0.")
        return False, None




if __name__ == "__main__":
    reference_automaton = Automaton()
    q0 = Automaton.State('q0')
    q1 = Automaton.State('q1')
    q2 = Automaton.State('q2')
    q3 = Automaton.State('q3')
    q0.is_accepting = True
    q1.is_accepting = True
    q0.add_transition('a', q1)
    q0.add_transition('b', q2)
    q1.add_transition('a', q3)
    q1.add_transition('b', q0)
    q2.add_transition('a', q1)
    q2.add_transition('b', q2)
    q3.add_transition('a', q3)
    q3.add_transition('b', q0)
    reference_automaton.add_state(q0)
    reference_automaton.add_state(q1)
    reference_automaton.add_state(q2)
    reference_automaton.add_state(q3)
    reference_automaton.alphabet = {'a', 'b'}
    find_minimal_solution(reference_automaton)