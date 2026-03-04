//=======================
// A program for reading the output of ltl2dstar into a deterministic Büchi automaton,
// whenever possible. Then, we minimize it using SAT techniques.
//
// (C) 2010 Rüdiger Ehlers
//=======================
#include <iostream>
#include <fstream>
#include <sstream>
#include <map>
#include "buechi.hpp"

DBW::DBW(const char *inputFilename, const char *satFilename) {
	
	// Read original File
	DBW original(inputFilename);
	
	// Read SAT file
	std::ifstream desc(satFilename);
	
	// Read header string
	std::string init;
    init = "c";
    while (init[0]=='c') {
    	std::getline(desc,init);
    }
	if (init!="s SATISFIABLE") {
        std::cerr << "Error: First line of SAT input file does not contain the satisfiability results.\n";
        std::cerr << "Instead the following line was found: " << init << std::endl;
        throw "Thus, I cannot proceed.";
	}
	
	std::map<int,bool> values;
	
	std::string currentLine;
	do {
		std::getline(desc,currentLine);
		if (currentLine!="") {
			std::istringstream in(currentLine);
			std::string vPrefix;
			in >> vPrefix;
			
			int num;
			do {
				in >> num;
				if (!in.fail()) {
					if (num!=0) {
						values[std::abs(num)] = num>0;
					} else {
						currentLine = "";
					}
				} else if (in.eof()) {
					// Nothing
				} else if (in.fail()) {
					throw "Failed to read number.\n";
				}
			} while ((!in.eof()) && (num!=0));
			
			if (vPrefix != "v") {std::cerr << currentLine << std::endl; throw "Illegal line in SAT solution!"; }
			
		}
	} while (currentLine!="");
	
	// Allocate the resources
	sizeSigma = original.sizeSigma;
	nofStates = original.nofStates-1;
	acceptingStates = new bool[nofStates];
	transitionStructure = new int*[nofStates];
	for (int i=0;i<nofStates;i++) {
		transitionStructure[i] = new int[sizeSigma];
	}
	
	// Reconstruct the automaton
	propositionNames = original.propositionNames;
	
	// Now read the transitions
	int posInVars = 1;
	for (int state=0;state<nofStates;state++) {
		for (int sigma=0;sigma<sizeSigma;sigma++) {
			for (int succstate=0;succstate<nofStates;succstate++) {
				int currentVar = posInVars++;
				std::map<int,bool>::iterator it = values.find(currentVar);
				if (it==values.end()) {
					std::cerr << "Warning: Did not found a solution for transition " << state << "-(" << sigma << ")->"<<succstate<<std::endl;
					transitionStructure[state][sigma]=succstate;
				} else if (it->second) {
					transitionStructure[state][sigma]=succstate;
				}
			}
		}
		
		int currentVar = posInVars++;
		std::map<int,bool>::iterator it = values.find(currentVar);
		if (it==values.end()) {
			std::cerr << "Warning: Did not find out where state " << state << " is accepting. "<<std::endl;
			acceptingStates[state] = true;
		} else if (it->second) {
			acceptingStates[state] = true;
		} else {
			acceptingStates[state] = false;
		}
	}
	
	
}

int main(int argc, char **argv) {
	
	 // Assuming that we have some file names given
	if (argc<3) {
		std::cerr << "Error: Expecting .aut and SAT solver result file given\n";
		return 1;
	}
	
	const char *inputFile = argv[1];
	const char *satFile = argv[2];

	
	try {
		DBW smaller(inputFile,satFile);
		smaller.printLTL2DSTARForm();
		return 0;
		
	} catch (const char *c) {
		std::cerr << c << std::endl;
		return 1;
	}
	
	
}

