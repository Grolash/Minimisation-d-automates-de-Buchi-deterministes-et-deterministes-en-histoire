//
// Büchi-Automaton minimizer.
//
// New version labelling transitions instead of states
//
// (C) 2009 by Ruediger Ehlers
#include "buechi.hpp"
#include <list>
#include <boost/tuple/tuple_comparison.hpp>
#include <boost/tuple/tuple_io.hpp>
#include <tr1/unordered_map>
#include <fstream>
#include <sstream>
#include <map>
#include <iostream>
#include <boost/tokenizer.hpp>
#include <boost/algorithm/string/trim.hpp>
#include <string>


//================================================
// Some basic housekeeping functions
//================================================
DBW::DBW(int _sizeSigma, int _nofStates) {
	sizeSigma = _sizeSigma;
	nofStates = _nofStates;
	acceptingStates = new bool[nofStates];
	transitionStructure = new int*[nofStates];
	for (int i=0;i<nofStates;i++) {
		transitionStructure[i] = new int[sizeSigma];
	}
}

DBW::~DBW() {
	delete[] acceptingStates;
	for (int i=0;i<nofStates;i++) {
		delete[] transitionStructure[i];
	}
	delete[] transitionStructure;
}

DBW& DBW::operator= (const DBW& other) {
	if (&other==this) return *this;

	// Delete old stuff
	delete[] acceptingStates;
	for (int i=0;i<nofStates;i++) {
		delete[] transitionStructure[i];
	}
	delete[] transitionStructure;

	// Copy basic stuff
	sizeSigma = other.sizeSigma;
	nofStates = other.nofStates;
	transitionStructure = new int*[nofStates];
	for (int i=0;i<nofStates;i++) {
		transitionStructure[i] = new int[sizeSigma];
		for (int j=0;j<sizeSigma;j++) {
			transitionStructure[i][j] = other.transitionStructure[i][j];
		}
	}

	acceptingStates = new bool[nofStates];
	for (int i=0;i<nofStates;i++) {
		acceptingStates[i] = other.acceptingStates[i];
	}
	
	return *this;
}


DBW::DBW(const DBW&other) {
	// Copy basic stuff
	sizeSigma = other.sizeSigma;
	nofStates = other.nofStates;
	transitionStructure = new int*[nofStates];
	for (int i=0;i<nofStates;i++) {
		transitionStructure[i] = new int[sizeSigma];
		for (int j=0;j<sizeSigma;j++) {
			transitionStructure[i][j] = other.transitionStructure[i][j];
		}
	}

	acceptingStates = new bool[nofStates];
	for (int i=0;i<nofStates;i++) {
		acceptingStates[i] = other.acceptingStates[i];
	}
}

std::string DBW::convertToAlphabeticalStateIdentifier(int stateNum) {
	std::string s;
	while (stateNum>0) {
		int c = stateNum % 26;
		s = char('a'+c) + s;
		stateNum /= 26;
	}
	if (s=="") return "a";
	return s;
}


int DBW::convertFromAlphabeticalStateIdentifier(std::string s) {
	int where = 0;
	for (uint i=0;i<s.length();i++) {
		if ((s[i]<'a') || (s[i]>'z')) throw "DBW::convertFromAlphabeticalStateIdentifier -- illegal state name.";
		where = where*26 + (s[i]-'a');
	}
	return where;
}

/**
 * Puts out a DBW as DOT-output
 * @param where The stream to be used to output stuff
 */
void DBW::dumpDot(std::ostream &where) const {
	where << "digraph G { size = \"8,8\" \n  center = true; \n";

    // Write the labelling
    where << " props [label=\"Variable order: ";
    for (uint i=0;i<propositionNames.size();i++) {
        if (i!=0) where << ",";        
        std::string propName = propositionNames[i];
        // Get rid of quotation marks
        if (propName[0]=='\"') propName = propName.substr(1,std::string::npos);
        if (propName[propName.length()-1]=='\"') propName = propName.substr(0,propName.length()-1);
        // Print the label
        where << propName;
    }
    where << "\",shape=note];\n";

	// Make states
	for (int i=0;i<nofStates;i++) {
		where << convertToAlphabeticalStateIdentifier(i);
		if (acceptingStates[i]) where << "[label = \""+convertToAlphabeticalStateIdentifier(i)+"+\"]";
		if (i==0) where << "[style=filled]";
		where << ";\n";
	}
	
	// Make transitions
	for (int i=0;i<nofStates;i++) {
		std::vector<std::string> labels[nofStates];
		for (int j=0;j<sizeSigma;j++) {
			int dest = transitionStructure[i][j];
			if (dest!=-1) {
				std::ostringstream label;
                int cp = j;
                for (uint i=0;i<propositionNames.size();i++) {
                    if ((cp & 1)==0) label << "0";
                    else label << "1";
                    cp >>= 1;
                }
				labels[dest].push_back(label.str());
			}
		}

        // Merge some labels. The procedure here is rather inefficient, but
        // this is not really a high-performance procedure.
        for (int pos=0;pos<nofStates;pos++) {
            std::vector<std::string> currentSet = labels[pos];
            bool done = false;
            while (!done) {
                done = true;
                // Try to find a match
                for (uint j=0;j<currentSet.size();j++) {
                    for (uint k=0;k<currentSet.size();k++) {
                        std::string one = currentSet[j];
                        std::string two = currentSet[k];
                        int diff = 0;
                        char newOne[one.length()+1];
                        newOne[one.length()] = '\0';
                        for (uint t=0;t<one.length();t++) {
                            if (one[t]!=two[t]) {
                                diff++;
                                newOne[t] = '*';
                            } else {
                                newOne[t] = one[t];
                            }
                        }
                        if (diff==1) {
                            done = false;
                            std::vector<std::string> newSet;
                            for (uint t=0;t<currentSet.size();t++) {
                                if ((t!=k) && (t!=j)) newSet.push_back(currentSet[t]);
                            }
                            k = currentSet.size();
                            j = currentSet.size();
                            newSet.push_back(newOne);
                            currentSet = newSet;
                        }
                    }
                }
            }
            labels[pos] = currentSet;
        }


		for (int j=0;j<nofStates;j++) {
			if (labels[j].size()>0) {
				where << convertToAlphabeticalStateIdentifier(i) << " -> " << convertToAlphabeticalStateIdentifier(j) << "[ label=\"";
				bool first = true;
				for (std::vector<std::string>::iterator it = labels[j].begin();it!=labels[j].end();it++) {
					if (!first) where << ",";
					where << *it;
					first = false;
				}
				where << "\"];\n";
			}
		}
	}
	where << "}\n";
}


/**
 * A function to swap two states in an automaton. Leaves the language unchanged, unless the initial state is involved.
 * @param one The one state
 * @param two The other state
 * @return The same automaton with states swapped
 */
DBW DBW::swapStates(int one, int two) const {
	DBW dest(sizeSigma,nofStates);
		
	// Build mapping
	std::map<int,int> map;
	for (int i=0;i<nofStates;i++) {
		map[i] = i;
	}
	map[one] = two;
	map[two] = one;
	
	// Copy the transitions
	for (int i=0;i<nofStates;i++) {
		dest.acceptingStates[map[i]] = acceptingStates[i];
		for (int s=0;s<sizeSigma;s++) {
			dest.transitionStructure[map[i]][s] = map[transitionStructure[i][s]];
		}
	}
	
	return dest;
}


void DBW::printLTL2DSTARForm() const {
	
	std::cout << "DRA v2 explicit\n";
	std::cout << "Comment: \"Automatically minimized\"\n";
	std::cout << "States: " << nofStates << "\n";
	std::cout << "Acceptance-Pairs: 1\nStart: 0\n";
	std::cout << "AP: " << propositionNames.size();
	for (std::vector<std::string>::const_iterator it = propositionNames.begin();it!=propositionNames.end();it++) {
		std::cout << " " << *it;
	}
	std::cout << "\n---\n";
	for (int i=0;i<nofStates;i++) {
		std::cout << "State: " << i << "\n";
		std::cout << "Acc-Sig:" << (acceptingStates[i]?" +0\n":"\n");
		for (int j=0;j<sizeSigma;j++) {
			std::cout << transitionStructure[i][j] << "\n";
		}
	}	
}

/**
 * Finds equivalent states in the DBW, checks whether they are in the same SCC and "rebends" some states if this is not the case.
 */
void DBW::minimiseUsingLanguageEquivalence() {
	
	// Find non-equivalent loop-bases
	bool equivalent[nofStates][nofStates];
	for (int base1=0;base1<nofStates;base1++) {
		for (int base2=0;base2<=base1;base2++) {
			if (base1==base2) {
				equivalent[base1][base1] = true;
			} else {
				
				// Allocate doToBuffers and stuff
				std::set<boost::tuple<int,int,int> > todoList;
				std::set<boost::tuple<int,int,int> > doneList;
				
				todoList.insert(boost::make_tuple(base1,base2,0));
				
				while (todoList.size()>0) {
					boost::tuple<int,int,int> current = *(todoList.begin());
					todoList.erase(todoList.begin());
					doneList.insert(current);
					
					for (int s=0;s<sizeSigma;s++) {
						int next1 = transitionStructure[current.get<0>()][s];
						int next2 = transitionStructure[current.get<1>()][s];
						int acc = current.get<2>();
						if (acceptingStates[next1]) acc |= 1;
						if (acceptingStates[next2]) acc |= 2;
						boost::tuple<int,int,int> next = boost::make_tuple(next1,next2,acc);
						if (doneList.count(next)==0) todoList.insert(next);
					}
				}
				
				equivalent[base1][base2] = ((doneList.count(boost::make_tuple(base1,base2,1))==0) && (doneList.count(boost::make_tuple(base1,base2,2))==0));
			}
		}
	}
	
        /*for (int base1=0;base1<nofStates;base1++) {
		for (int base2=0;base2<=base1;base2++) {
			if (equivalent[base1][base2]) {
				std::cerr << "Equivalent states: " << base1 << "," << base2 << "\n";
			}
		}
        }*/
	
	// Take transitive closure of the equivalent relation
	bool recentChange = true;
	while (recentChange) {
		recentChange = false;
		for (int i=0;i<nofStates;i++) {
			for (int j=0;j<i;j++) {
				if (equivalent[i][j]) {
					for (int s=0;s<sizeSigma;s++) {
						int next1 = transitionStructure[i][s];
						int next2 = transitionStructure[j][s];
						if (!equivalent[std::max(next1,next2)][std::min(next1,next2)]) {
							recentChange = true;
                                                        equivalent[i][j] = false;
						}
					}
				}
			}
		}
	}
	
	// Compute reachability relation
        std::set<boost::tuple<int,int> > reachable;
	{
		std::set<boost::tuple<int,int> > todoList;
		for (int i=0;i<nofStates;i++) todoList.insert(boost::make_tuple(i,i));
		while (todoList.size()>0) {
			boost::tuple<int,int> current = *(todoList.begin());
			todoList.erase(todoList.begin());
			reachable.insert(current);
			
			for (int s=0;s<sizeSigma;s++) {
				int dest = transitionStructure[current.get<1>()][s];
				boost::tuple<int,int> next = boost::make_tuple(current.get<0>(),dest);
				if (reachable.count(next)==0) todoList.insert(next);
			}
		}
	}

        /*for (std::set<boost::tuple<int,int> >::iterator it = reachable.begin();it!=reachable.end();it++) {
            std::cerr << "Reachable " << it->get<0>() << "," << it->get<1>() << std::endl;
        }*/

        // Compute SCC transitions
        std::set<boost::tuple<int,int> > sccTransitions;
        for (int i=0;i<nofStates;i++) {
            for (int j=0;j<nofStates;j++) {
                if (((reachable.count(boost::make_tuple(i,j))==1)&& (reachable.count(boost::make_tuple(j,i))==0))) {
                    sccTransitions.insert(boost::make_tuple(i,j));
                }
            }
        }
	
	// Merge: Computer merging relation
	std::map<int,int> merger;
	
	// Build initial merging relation
	for (int i=0;i<nofStates;i++) {
		merger[i] = i;
		for (int j=0;j<i;j++) {
                        if (equivalent[i][j] && (sccTransitions.count(boost::make_tuple(i,j))>0)) merger[i] = j;
		}
		for (int j=i+1;j<nofStates;j++) {
                        if (equivalent[j][i] && (sccTransitions.count(boost::make_tuple(i,j))>0)) merger[i] = j;
		}
	}
	
	// Make everything transitive
    recentChange = true;
	while (recentChange) {
		recentChange = false;
		for (int i=0;i<nofStates;i++) {
			int val = merger[i];
			if (val!=merger[val]) {
				merger[i] = merger[val];
				recentChange = true;
                                //if (reachable.count(boost::make_tuple(merger[i],i))!=0) throw "Error while minimizing automaton.";
			}
		}
        }
	
	// Merge: Print
        /*for (int i=0;i<nofStates;i++) {
                std::cerr << "Merge state " << i << " to " << merger[i] << "\n";
        }*/
	
	// Update transitions
	for (int i=0;i<nofStates;i++) {
		for (int s=0;s<sizeSigma;s++) {
			transitionStructure[i][s] = merger[transitionStructure[i][s]];	
		}
	}
	
	// Now get a swapping plan. By starting with 0, we can be sure to 
	std::set<int> assigned;
	int swap[nofStates];
	
	for (int i=0;i<nofStates;i++) {
		if (assigned.count(merger[i])==0) {
			swap[merger[i]] = assigned.size();
			assigned.insert(merger[i]);
		}
	}
	
	// Build a new transition relation and a new accepting state set
	int newNofStates = assigned.size();
	bool *_acceptingStates = new bool[newNofStates];
	int **_transitionStructure = new int*[newNofStates];
	for (int i=0;i<newNofStates;i++) {
		_transitionStructure[i] = new int[sizeSigma];
	}
		
	// Swap the automaton right
	for (std::set<int>::iterator it = assigned.begin();it != assigned.end();it++) {
		int current = *it;
		_acceptingStates[swap[current]] = acceptingStates[current];
		for (int s=0;s<sizeSigma;s++) {
			_transitionStructure[swap[current]][s] = swap[merger[transitionStructure[current][s]]];
		}
	}
		
	// Delete old stuff...
	delete[] acceptingStates;
	for (int i=0;i<nofStates;i++) {
		delete[] transitionStructure[i];
	}
	delete[] transitionStructure;
	transitionStructure = _transitionStructure;
	acceptingStates = _acceptingStates;
	nofStates = newNofStates;
	
    // post-optimization
    removeUnreachableStates();
}

void DBW::removeUnreachableStates() {
    std::set<int> todo;
    std::set<int> reachable;
    todo.insert(0);
    while (todo.size()>0) {
        int next = *todo.begin();
        todo.erase(next);
        reachable.insert(next);
        for (int j=0;j<sizeSigma;j++) {
            if (reachable.count(transitionStructure[next][j])==0) {
                todo.insert(transitionStructure[next][j]);
            }
        }
    }
    int newNofStates = 0;
    std::map<int,int> map;
    for (int i=0;i<nofStates;i++) {
        if (reachable.count(i)==0) {
            map[i] = -1;
        } else {
            map[i] = newNofStates++;
        }
    }

    // Copy the transitions
	for (int i=0;i<nofStates;i++) {
        if (map[i]!=-1) {
		    acceptingStates[map[i]] = acceptingStates[i];
		    for (int s=0;s<sizeSigma;s++) {
			    transitionStructure[map[i]][s] = map[transitionStructure[i][s]];
		    }
        }
	}
    // Delete old stuff
    for (int i=newNofStates;i<nofStates;i++) {
		delete[] transitionStructure[i];
	}
    nofStates = newNofStates;
}

/**
 * Special constructur that reads output from LTL2DSTAR and makes this a Büchi automaton, whenever possible (only one Rabin pair)
 * @param inputFilename Where to read from...
 */
DBW::DBW(const char *inputFilename) {
	
	std::ifstream desc(inputFilename);
	
	// Example input file:
	// DRA v2 explicit
	// Comment: "Safra[NBA=2]"
	// States: 2
	// Acceptance-Pairs: 1
	// Start: 0
	// AP: 1 "a"
	// ---
	// State: 0
	// Acc-Sig:
	// 0
	// 1
	// State: 1
	// Acc-Sig: +0
	// 0
	// 1

	// Read header string
	std::string init;
	std::getline(desc,init);
	if (init!="DRA v2 explicit") {
		throw "Error: First line of input file does not contain the file header.";
	}
	
	// Read comment
	std::string comment;
	std::getline(desc,comment);
	if (comment.substr(0,8)!="Comment:") {
		throw "Error: Second line of input file does not contain a comment.";
	}
		
	// Read nof states
	std::string states;
	std::getline(desc,states);
	if (states.substr(0,8)!="States: ") {
		throw "Error: Third line of input file does not start with 'States:'.";
	}
	{
		std::istringstream is(states.substr(8,std::string::npos));
		is >> nofStates;
		if (is.fail()) throw "Error: Number of states is invalid.";
	}
		
	// Read nof acceptance pairs
	std::string apairs;
	std::getline(desc,apairs);
	uint nofAcceptancePairs;
	{
		std::istringstream apairsIS(apairs);
		std::string name;
		apairsIS >> name;
		if (name!="Acceptance-Pairs:") {
			std::cerr << "<" << name << ">" << std::endl;
			throw "Error: Fourth line of input file does not contain the acceptance pairs string.";
		}
		apairsIS >> nofAcceptancePairs;
		if (apairsIS.fail()) throw "Error: Cannot read number of acceptance pairs!";
		if (nofAcceptancePairs>sizeof(uint)*4) throw "Error: Too many acceptance pairs for this platform.";
	}
	
	
	// Read starting state
	std::string start;
	std::getline(desc,start);
	if (start.substr(0,7)!="Start: ") {
		throw "Error: Fifth line of input file does not start with 'Start: '.";
	}
	uint startingState;
	{
		std::istringstream is(start.substr(7,std::string::npos));
		is >> startingState;
		if (is.fail()) throw "Error: Number of states is invalid.";
	}
	
	// Read atomic propsitions
	std::string ap;
	desc >> ap;
	if (ap!="AP:") throw "Expecting atomic propositions.";
	desc >> sizeSigma;
	
	if (desc.fail()) throw "Error: Number of atomic propositions is invalid!";
	
	for (int i=0;i<sizeSigma;i++) {
		std::string name;
		desc >> name;
		propositionNames.push_back(name);
	}
	
	// Take powerset
	sizeSigma = 1 << sizeSigma;

	
	// Allocate space
	acceptingStates = new bool[nofStates];
	transitionStructure = new int*[nofStates];
	for (int i=0;i<nofStates;i++) {
		transitionStructure[i] = new int[sizeSigma];
	}
	
	// Now read the states
	// Use variables for Rabin storing
	bool rabinPlus[nofStates][nofAcceptancePairs];
	bool rabinMinus[nofStates][nofAcceptancePairs];
		
	std::string minus;
	std::getline(desc,minus);
	std::getline(desc,minus);
	if (minus!="---") {
		std::cerr << "Got: <" << minus << ">\n";
		throw "Expected '---' between states!";
	}
	for (int i=0;i<nofStates;i++) {
		std::string stateNum;
		std::getline(desc,stateNum);
		std::string signature;
		std::getline(desc,signature);
		if (signature.substr(0,8)!="Acc-Sig:") {
			std::cerr << "Got: <" << signature << ">\n";
			throw "Excepted signature!";
		} else {
			// Interpret signature
			acceptingStates[i] = true;
			for (uint k=0;k<nofAcceptancePairs;k++) {
				rabinPlus[i][k] = false;
				rabinMinus[i][k] = false;
			}
			std::istringstream parts(signature.substr(8,std::string::npos));
			while (!parts.eof()) {
				std::string part;
				parts >> part;
				if (!(parts.eof() && (part==""))) {
					std::istringstream thisPart(part);
					char prefix;
					thisPart >> prefix;
					int number;
					thisPart >> number;
					if (thisPart.fail()) throw "Error: Cannot read signature of state.";
					if (prefix=='-') {
						rabinMinus[i][number] = true;
					} else if (prefix=='+') {
						rabinPlus[i][number] = true;
					} else throw "Error: Cannot interpret prefix symbol.";
				}
			}
		}
		for (int j=0;j<sizeSigma;j++) {
			std::string line;
			std::getline(desc,line);
			std::istringstream number(line);
			int num;
			number >> num;
			if (number.fail()) {
				throw "Cannot read number describing the transition!";
			}
			transitionStructure[i][j] = num;
		}
	}
	
	// We assume that non-reachable states have already been pruned!
	// Otherwise, the following procedure is not complete in the sense that it might detect
	// spec's as being non-Büchi even though they are (since the non-Rabin part
	// of the automaton might be unreachable).
	
	// Now we turn to something completety different: Making a Büchi automaton out of the given automaton.
	// First, find non-accepting loops. Make all states on such non-accepting.
	// By default, states are accepting (made in the loop above.)
	for (int base=0;base<nofStates;base++) {
		std::set<std::pair<int,uint> > doneList; // First: State, Second: Signature so far
		std::set<std::pair<int,uint> > todoList;
		todoList.insert(std::pair<uint,uint>(base,0));
		while (todoList.size()>0) {
			std::pair<int,uint> current = *(todoList.begin());
			todoList.erase(todoList.begin());
            // std::cerr << "Working on: " << current.first << "," << current.second << "\n";
						
			// Iterate over successors
			for (int s=0;s<sizeSigma;s++) {
                //std::cerr << "Considering character " << s << "\n";
				int dest = transitionStructure[current.first][s];
				// Update transition structure
				uint soFar = current.second;
				for (uint j=0;j<nofAcceptancePairs;j++) {
					if (rabinPlus[dest][j]) {
                        //std::cerr << "Detected Rabin plus pair " << j << "\n";
                        soFar |= 1 << (j*2);
                    }
					if (rabinMinus[dest][j]) {
                        soFar |= 1 << (j*2+1);
                        // std::cerr << "Detected Rabin minus pair " << j << "\n";
                    }
				}
				std::pair<uint,uint> next(dest,soFar);
				if (doneList.count(next)==0) {
					todoList.insert(next);
					doneList.insert(next);
					// std::cerr << "Base: " << base << ", insert: (" << next.first << "," << next.second << ")\n";
				}
			}
		}
		
		// Now check if there's a rejecting state
		bool fits = false;
		for (std::set<std::pair<int,uint> >::iterator it = doneList.begin();it!=doneList.end();it++) {
			// std::cerr << "Base: " << base << ", going: (" << it->first << "," << it->second << ")\n";
			std::pair<int,uint> current = *it;
			if (current.first==base) {
                bool fitsThis = true;
				for (uint j=0;j<nofAcceptancePairs;j++) {
					if (((current.second >> j*2) & 3)==1) {
                        fitsThis = false;
						// std::cerr << "found accepting cycle!\n";
					} else {
						// std::cerr << "Does not fit: " << current.second << " with result: " << ((current.second >> j*2) & 3) << "\n";
					}
				}
                fits |= fitsThis;
				if (fits) {
					it = doneList.end();
					it--;
				}
			}
		}
		if (fits) {
			// std::cerr << "Non-acc. state: " << base << std::endl;
			acceptingStates[base] = false;
		}

	}
	
	// Now that the rest of the states are accepting, try to find a cycle in the DBA that is non-accepting but is accepting for the DRA.
	for (int base=0;base<nofStates;base++) {
		if (!acceptingStates[base]) {
			std::set<std::pair<int,uint> > doneList; // First: State, Second: Signature so far
			std::set<std::pair<int,uint> > todoList;
			todoList.insert(std::pair<int,uint>(base,0));
			while (todoList.size()>0) {
				std::pair<int,uint> current = *(todoList.begin());
				
				// std::cerr << "Base: " << base << ", check: (" << current.first << "," << current.second << ")\n";
				
				todoList.erase(todoList.begin());
				doneList.insert(current);
				
				// Iterate over successors
				for (int s=0;s<sizeSigma;s++) {
					int dest = transitionStructure[current.first][s];
					if (!acceptingStates[dest]) {
						// Update transition structure
						uint soFar = current.second;
						for (uint j=0;j<nofAcceptancePairs;j++) {
							if (rabinPlus[dest][j]) soFar |= 1 << (j*2);
							if (rabinMinus[dest][j]) soFar |= 1 << (j*2+1);
						}
						std::pair<int,uint> next(dest,soFar);
						if (doneList.count(next)==0) todoList.insert(next);
					}
				}
			}
			
			// Now check if there's a rejecting state
			for (std::set<std::pair<int,uint> >::iterator it = doneList.begin();it!=doneList.end();it++) {
				std::pair<int,uint> current = *it;
				if (current.first==base) {
					bool fits = false;
					for (uint j=0;j<nofAcceptancePairs;j++) {
						if (((current.second >> j*2) & 3)==1) fits = true;
					}
					if (fits) throw "The given DRA automaton cannot be represented by a DBA.";
				}
			}
		}
	}
	
	// Finally, swap the initial state
	*this = swapStates(0,startingState);
}

bool DBW::checkStateLanguageSubsumption(int stateSpoiler, int stateDuplicator) {

    // First, check which state pairs are reachable. Then, check for "bad" cycles

    std::set<std::pair<int, int> > todoList;
    std::set<std::pair<int, int> > doneList;
    todoList.insert(std::pair<int,int>(stateSpoiler,stateDuplicator));
    doneList.insert(std::pair<int,int>(stateSpoiler,stateDuplicator));

    while (todoList.size()>0) {

        std::pair<int,int> thisOne = *todoList.begin();
        todoList.erase(todoList.begin());

        for (int i=0;i<sizeSigma;i++) {
            int t1 = transitionStructure[thisOne.first][i];
            int t2 = transitionStructure[thisOne.second][i];
            std::pair<int,int> nextOne(t1,t2);
            if (doneList.count(nextOne)==0) {
                doneList.insert(nextOne);
                todoList.insert(nextOne);
            }
        }
    }

    for (std::set<std::pair<int,int> >::const_iterator it = doneList.begin();it!=doneList.end();it++) {

        std::set<boost::tuple<int,int,bool> > todoList2;
        std::set<boost::tuple<int,int,bool> > doneList2;

        todoList2.insert(boost::make_tuple(it->first,it->second,false));
        doneList2.insert(boost::make_tuple(it->first,it->second,false));

        while (todoList2.size()>0) {
            boost::tuple<int,int,bool> thisOne = *todoList2.begin();
            todoList2.erase(todoList2.begin());

            for (int i=0;i<sizeSigma;i++) {
                int t1 = transitionStructure[thisOne.get<0>()][i];
                int t2 = transitionStructure[thisOne.get<1>()][i];
                if (acceptingStates[t2]==false) {
                    boost::tuple<int,int,bool> nextOne = boost::make_tuple(t1,t2,thisOne.get<2>() || acceptingStates[t1]);
                }
            }
        }

        if (doneList2.count(boost::make_tuple(it->first,it->second,true))>0) return false;
    }

    return true;
}


std::string DBW::getAlphabetCharacterName(int number) const {
    std::ostringstream os;
    for (uint j=0;j<propositionNames.size();j++) {
        if (j!=0) os << " ";
        if (((number >> j) & 1)==0) os << "!";
        os << propositionNames[j];
    }
    return os.str();
}
