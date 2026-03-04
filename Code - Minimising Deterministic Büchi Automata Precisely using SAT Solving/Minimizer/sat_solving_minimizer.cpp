//
// Büchi-Automaton minimizer.
//
// New version labelling transitions instead of states
//
// (C) 2009 by Ruediger Ehlers

#include "buechi.hpp"
#include <boost/tuple/tuple.hpp>
#include <boost/tuple/tuple_comparison.hpp>
#include <boost/tuple/tuple_io.hpp>
#include <string>
#include <algorithm>
#include <sstream>
#include <list>
#include <set>
#include <fstream>
#include <map>

//#define SHOW_SAT_TRANSITION_DETAILS

/**
 * Applies a SAT solver to find a smaller automaton representing the same language
 * 
 * @param destSize The size of the smaller automaton desired. If "-1", it will be one less
 * than the size of this automaton
 * @return Whether the SAT solver succeeded
 */
void DBW::encodeAsSatInstance(const char *outFilename, char symmetryBreakingType, int destSize) const {
	
	int varsSoFar = 0;
		
	std::map<boost::tuple<int,int,int>,int> transitionVars;
	std::map<int,int> stateAcceptingVars;
	int nofStatesInGuessedAutomaton = (destSize==-1)?getNofStates()-1:destSize;
	
	std::ofstream dimacsFile(outFilename);
		
	// Trivial?
	if (nofStatesInGuessedAutomaton==0) {
		dimacsFile << "p cnf 1 2\n-1 0\n1 0\n";
		dimacsFile.close();
		return;
	}
	
	dimacsFile << "                                                                 \n";
	
	int nofDimacsLines = 0;
	
	// Adding variables for the solution
	for (int i=0;i<nofStatesInGuessedAutomaton;i++) {
		for (int s=0;s<sizeSigma;s++) {
			for (int j=0;j<nofStatesInGuessedAutomaton;j++) {
				transitionVars[boost::make_tuple(i,s,j)] = ++varsSoFar;
#ifdef SHOW_SAT_TRANSITION_DETAILS
				std::cout << "Transition description var: " << boost::make_tuple(convertToAlphabeticalStateIdentifier(i),s,convertToAlphabeticalStateIdentifier(j)) << ", Var: " << varsSoFar << "\n";
#endif
			}
		}
		stateAcceptingVars[i] = ++varsSoFar;
#ifdef SHOW_SAT_TRANSITION_DETAILS
		std::cout << "State acceptance var: " << i << ", Var: " << varsSoFar << "\n";
#endif
	}
	
	// Make pair-wise exclusion such that transitions are deterministic
	for (int i=0;i<nofStatesInGuessedAutomaton;i++) {
		for (int s=0;s<sizeSigma;s++) {
			// One must be set
			for (int j=0;j<nofStatesInGuessedAutomaton;j++) {
				dimacsFile	<< transitionVars[boost::make_tuple(i,s,j)] << " ";
			}
			dimacsFile << "0\n";
			nofDimacsLines++;
			
			// Any pair must not be both set
			/*for (int j=0;j<nofStatesInGuessedAutomaton;j++) {
				for (int j2=j+1;j2<nofStatesInGuessedAutomaton;j2++) {
					dimacsLines << -1*transitionVars[boost::make_tuple(i,s,j)] << " ";
					dimacsLines << -1*transitionVars[boost::make_tuple(i,s,j2)] << " 0\n";
					nofDimacsLines++;
				}
			}*/
		}
	}

	// Compute reachable pairs in the product automaton: 1. Allocate variables
	std::map<boost::tuple<int,int>,int > reachablePairs; // First item= Guessed automaton, Second item = original automaton
	for (int i=0;i<nofStatesInGuessedAutomaton;i++) {
		for (int j=0;j<getNofStates();j++) {
			reachablePairs[boost::make_tuple(i,j)] = ++varsSoFar;
#ifdef SHOW_SAT_TRANSITION_DETAILS
			std::cout << "Reachable Pair var: " << boost::make_tuple(convertToAlphabeticalStateIdentifier(i),convertToAlphabeticalStateIdentifier(j)) << ", Var: " << varsSoFar << "\n";
#endif
		}
	}

	// Compute reachable pairs in the product automaton: 2. Make initial reachability
	dimacsFile << reachablePairs[boost::make_tuple(0,0)] << " 0\n";
	nofDimacsLines++;

	// Compute reachable pairs in the product automaton: 3. Make closure
	for (int i=0;i<nofStatesInGuessedAutomaton;i++) {
		for (int j=0;j<getNofStates();j++) {
			for (int s=0;s<sizeSigma;s++) {
				for (int possibleSucc=0;possibleSucc<nofStatesInGuessedAutomaton;possibleSucc++) {
					// Cases: 1. Either not reachable
					dimacsFile << -1*reachablePairs[boost::make_tuple(i,j)] << " ";
					// 2. Or does not move from i to possibleSucc under s:
					dimacsFile << -1*transitionVars[boost::make_tuple(i,s,possibleSucc)] << " ";
					// 3. Or is marked
					dimacsFile << reachablePairs[boost::make_tuple(possibleSucc,transitionStructure[j][s])] << " 0\n";
					nofDimacsLines++;
				}
			}
		}
	}
	

	// For every basis state in the product automaton, compute what can be reached using only transitions that are non-accepting
	// in the reference automaton. All transitions that close the circle must be non-accepting.
	for (int basisGuessed = 0; basisGuessed < nofStatesInGuessedAutomaton; basisGuessed++) {
		for (int basisReference = 0;basisReference < getNofStates();basisReference++) {
			std::map<boost::tuple<int,int>,int > loops;
			for (int i=0;i<nofStatesInGuessedAutomaton;i++) {
				for (int j=0;j<getNofStates();j++) {
					loops[boost::make_tuple(i,j)] = ++varsSoFar;
#ifdef SHOW_SAT_TRANSITION_DETAILS
					std::cout << "Non accepting loops: Basis:" << boost::make_tuple(convertToAlphabeticalStateIdentifier(basisGuessed),convertToAlphabeticalStateIdentifier(basisReference)) << ", Position: " << boost::make_tuple(convertToAlphabeticalStateIdentifier(i),convertToAlphabeticalStateIdentifier(j)) << ", Var: " << varsSoFar << "\n";
#endif	
				}
			}
			
			// Create initial marking
			dimacsFile << -1*reachablePairs[boost::make_tuple(basisGuessed,basisReference)] << " ";
			dimacsFile << loops[boost::make_tuple(basisGuessed,basisReference)] << " 0\n";
			nofDimacsLines++;
			
			// Perform closure
			for (int i=0;i<nofStatesInGuessedAutomaton;i++) {
				for (int j=0;j<getNofStates();j++) {
					for (int s=0;s<sizeSigma;s++) {
						for (int possibleSucc=0;possibleSucc<nofStatesInGuessedAutomaton;possibleSucc++) {
							if (!acceptingStates[j])  {
								// Cases: 1. Either original position not set
								dimacsFile << -1*loops[boost::make_tuple(i,j)] << " ";
								// 2. No transitions here
								dimacsFile << -1*transitionVars[boost::make_tuple(i,s,possibleSucc)] << " ";
								// 3. Split: Either going back to the "roots", then that transition should not be accepting
								if ((basisGuessed==possibleSucc) && (basisReference==transitionStructure[j][s])) {
									dimacsFile << -1*stateAcceptingVars[i] << " 0\n";
								} else {
									// Or, the successor should be labelled.
									dimacsFile << loops[boost::make_tuple(possibleSucc,transitionStructure[j][s])] << " 0\n";
								}
								nofDimacsLines++;
							}
						}
					}
				}
			}
		}
	}

	// Finally, all Loops that are accepting in the reference should also be accepting in the new one.
	for (int basisGuessed = 0; basisGuessed < nofStatesInGuessedAutomaton; basisGuessed++) {
		for (int basisReference = 0;basisReference < getNofStates();basisReference++) {
			if (acceptingStates[basisReference]) {
				std::map<boost::tuple<int,int>,int > loops;
				for (int i=0;i<=nofStatesInGuessedAutomaton;i++) {
					for (int j=0;j<getNofStates();j++) {
						loops[boost::make_tuple(i,j)] = ++varsSoFar;
		#ifdef SHOW_SAT_TRANSITION_DETAILS
						std::cout << "Accepting loops: Basis:" << boost::make_tuple(convertToAlphabeticalStateIdentifier(basisGuessed),convertToAlphabeticalStateIdentifier(basisReference)) << ", Position: " << boost::make_tuple(convertToAlphabeticalStateIdentifier(i),convertToAlphabeticalStateIdentifier(j)) << ", Var: " << varsSoFar << "\n";
		#endif
					}
				}
				
				// Create initial marking
				dimacsFile << -1*reachablePairs[boost::make_tuple(basisGuessed,basisReference)] << " ";
				dimacsFile << loops[boost::make_tuple(basisGuessed,basisReference)] << " 0\n";
				nofDimacsLines++;
				
				// Perform closure
				for (int i=0;i<nofStatesInGuessedAutomaton;i++) {
					for (int j=0;j<getNofStates();j++) {
						for (int s=0;s<sizeSigma;s++) {
						
							for (int possibleSucc=0;possibleSucc<nofStatesInGuessedAutomaton;possibleSucc++) {
								// Cases: 1. Either original position not set
								dimacsFile << -1*loops[boost::make_tuple(i,j)] << " ";
								// 2. No transitions here
								dimacsFile << -1*transitionVars[boost::make_tuple(i,s,possibleSucc)] << " ";
								// 3. Already accepting
								dimacsFile << stateAcceptingVars[i] << " ";
										
								// 3. Split: Either going back to the "roots" or not
								if ((basisGuessed==possibleSucc) && (basisReference==transitionStructure[j][s])) {
									dimacsFile << "0\n";
								} else {
									// Or, the successor should be labelled.
									dimacsFile << loops[boost::make_tuple(possibleSucc,transitionStructure[j][s])] << " 0\n";
								}
								nofDimacsLines++;
							}

						}
					}
				}
			}
		}
	}

	switch (symmetryBreakingType) {
		case '0':
			// Done!
			break;
		case '1':
		{
			// Accelerator: Very basic pseudo-normal-form property - Only if there's no starting point given!
			for (int i = 0;i<nofStatesInGuessedAutomaton;i++) {
				for (int s=0;s<sizeSigma;s++) {	
					for (int j=i*sizeSigma+s+2;j<nofStatesInGuessedAutomaton;j++) {
						dimacsFile << -1*transitionVars[boost::make_tuple(i,s,j)] << " 0\n";
						nofDimacsLines++;
					}
				}
			}
		}
		case '2':
			// Partial symmetry breaking: Exchanging a state i with i+1 may not lead to a lexicographically smaller result.
			// Uses either variables for intermediate results (3) or chains (2)
		{
			for (int base=0;base<nofStatesInGuessedAutomaton-1;base++) {
				std::list<boost::tuple<int,int> > exchangers;
				
				// Add transitions to the candidates to the exchangers list
				for (int i=0;i<nofStatesInGuessedAutomaton;i++) {
					if ((i!=base) && (i!=(base+1))) {
						for (int s=0;s<sizeSigma;s++) {
							exchangers.push_back(boost::make_tuple(transitionVars[boost::make_tuple(i,s,base)],transitionVars[boost::make_tuple(i,s,base+1)]));
						}
					}
				}
				
				// Add transitions from the candidates to the exchangers list
				for (int i=0;i<nofStatesInGuessedAutomaton;i++) {
					if (i==base) {
						for (int s=0;s<sizeSigma;s++) {
							exchangers.push_back(boost::make_tuple(transitionVars[boost::make_tuple(base,s,base)],transitionVars[boost::make_tuple(base+1,s,base+1)]));
						}
					} else if (i==base+1) {
						for (int s=0;s<sizeSigma;s++) {
							exchangers.push_back(boost::make_tuple(transitionVars[boost::make_tuple(base,s,base+1)],transitionVars[boost::make_tuple(base+1,s,base)]));
						}
					} else {
						for (int s=0;s<sizeSigma;s++) {
							exchangers.push_back(boost::make_tuple(transitionVars[boost::make_tuple(base,s,i)],transitionVars[boost::make_tuple(base+1,s,i)]));
						}
					}
				}
			
				if (symmetryBreakingType=='2') {
					
					// Do it like in the Handbook of Satisfiability, up to page 321
					
					// Allocate variables
					std::set<int> equalityVars;
					for (std::list<boost::tuple<int,int> >::iterator it = exchangers.begin();it!=exchangers.end();it++) {
						
						// Create new equalityVars
						int currentVarLess = ++varsSoFar;
						dimacsFile << -1*currentVarLess << " " << it->get<0>() << " " << -1*it->get<1>() << " 0 \n";
						dimacsFile << currentVarLess << " " << -1*it->get<0>() << " 0\n";
						dimacsFile << currentVarLess << " " << it->get<1>() << " 0\n";
						nofDimacsLines +=3;
						
						// Write old less queue
						for (std::set<int>::iterator it2 = equalityVars.begin();it2!=equalityVars.end();it2++) {
							dimacsFile << -1*(*it2) << " ";
						}
						dimacsFile << currentVarLess << " 0\n";
						nofDimacsLines++;
						
						std::list<boost::tuple<int,int> >::iterator checkEnd = it; checkEnd++;
						if (checkEnd!=exchangers.end()) {
							int currentVarGreater = ++varsSoFar;
							dimacsFile << -1*currentVarGreater << " " << -1*it->get<0>() << " " << it->get<1>() << " 0 \n";
							dimacsFile << currentVarGreater << " " << it->get<0>() << " 0\n";
							dimacsFile << currentVarGreater << " " << -1*it->get<1>() << " 0\n";
							nofDimacsLines +=3;
							equalityVars.insert(currentVarGreater);
						}
					}
					
				}
			
			}
		}
		break;
		default:
			throw "Illegal symmetry breaking type!";
	}
	
	dimacsFile.seekp(0);
	dimacsFile << "p cnf " << varsSoFar << " " << nofDimacsLines;
		
	dimacsFile.close();
	
}
