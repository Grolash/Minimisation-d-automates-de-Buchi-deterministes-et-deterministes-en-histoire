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

int main(int argc, char **argv) {
	
	 // Assuming that we have some file name given
	if (argc<2) {
		std::cerr << "Error: Expecting .aut file given\n";
		return 1;
	}
	
	const char *inputFile = argv[1];
	
	try {
		DBW original(inputFile);
		original.dumpDot(std::cout);
		return 0;
		
	} catch (const char *c) {
		std::cerr << c << std::endl;
		return 1;
	}
	
	
}

