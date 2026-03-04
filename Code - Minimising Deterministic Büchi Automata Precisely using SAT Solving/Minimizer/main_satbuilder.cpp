//=======================
// A program for reading the output of ltl2dstar into a deterministic Büchi automaton,
// whenever possible. Then, we minimize it using SAT techniques.
//
// (C) 2010 Rüdiger Ehlers
//=======================
#include <iostream>
#include <sstream>
#include "buechi.hpp"

int main(int argc, char **argv) {
	
	 // Assuming that we have some file names given
	if (argc<4) {
		std::cerr << "Error: Expecting input- and output file given as well as a optimization code (1-digit: 0,1 for symmetry breaking \n";
		return 1;
	}
	
	const char *inputFile = argv[1];
	const char *outputFile = argv[2];
	char symmetryBreakingType = argv[3][0];
	
	// Get size if existing
	int newSize = -1;
	if (argc>4) {
		std::istringstream is(argv[4]);
		is >> newSize;
		if (is.fail()) {
			std::cerr << "Illegal number of states in the destination automaton given!\n";
			exit(1);
		}
	}
	
	if ((symmetryBreakingType<'0') || (symmetryBreakingType>'3')) {
		std::cerr << "Illegal symmetry-breaking type";
		return 1;
	}
	
	
	try {
		DBW initial(inputFile);
		initial.encodeAsSatInstance(outputFile,symmetryBreakingType,newSize);
		//initial.dumpDot(std::cerr);
		return 0;
		
	} catch (const char *c) {
		std::cerr << c << std::endl;
		return 1;
	}
	
	
}

