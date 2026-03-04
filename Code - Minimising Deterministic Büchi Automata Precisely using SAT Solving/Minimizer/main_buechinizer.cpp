//=======================
// A program for reading the output of ltl2dstar into a deterministic Büchi automaton,
// whenever possible. Then, we put out the Büchi automaton.
//
// (C) 2010 Rüdiger Ehlers
//=======================
#include <iostream>
#include <fstream>
#include <sstream>
#include <map>
#include "buechi.hpp"

int main(int argc, char **argv) {
	
	 // Assuming that we have some file name given
	if (argc<2) {
		std::cerr << "Error: Expecting .aut file given\n";
		return 1;
	}
	
	const char *inputFile = argv[1];
	
	try {
		DBW original(inputFile);
		original.printLTL2DSTARForm();
		return 0;
		
	} catch (const char *c) {
        std::cerr << c << std::endl;
        if (c==std::string("The given DRA automaton cannot be represented by a DBA.")) {
    		return 1;
        } else {
            return 100;
        }
	}
	
	
}

