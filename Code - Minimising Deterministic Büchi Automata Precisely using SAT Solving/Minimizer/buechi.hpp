//
// Büchi-Automaton minimizer.
//
// New version labelling transitions instead of states
//
// (C) 2009 by Ruediger Ehlers

#ifndef __BUECHI_HPP__
#define __BUECHI_HPP__

#include <iostream>
#include <vector>
#include <stdlib.h>
#include <set>


/**
 * Class für Deterministic Büch Word automata
 *
 */
class DBW{
protected:
	int sizeSigma;
	int nofStates;
	int** transitionStructure;
	bool* acceptingStates;
	std::vector<std::string> propositionNames;

public:
	DBW(int _sizeSigma, int _nofStates);
	DBW(std::string &dotString);
	DBW(const char *inputFilename);
	DBW(const char *inputFilename, const char *satFilename);
	~DBW();
    inline int getNofStates() const { return nofStates; }
    inline int getSizeSigma() const { return sizeSigma; }
	void dumpDot(std::ostream &where) const;
    bool checkStateLanguageSubsumption(int stateA, int stateB);
    bool isAcceptingState(int stateNr) const { return acceptingStates[stateNr]; }
    int getTransition(int from, int s) const { return transitionStructure[from][s]; }
	DBW swapStates(int one, int two) const;
    std::string getAlphabetCharacterName(int number) const;
    std::vector<std::string> getPropositionNames() const { return propositionNames; }
    void removeUnreachableStates();
	
	DBW &operator= (const DBW& other);
	DBW (const DBW &other);
	static std::string convertToAlphabeticalStateIdentifier(int stateNum);
	static int convertFromAlphabeticalStateIdentifier(std::string s);

	void encodeAsSatInstance(const char *outFilename, char symmetryBreakingType, int destSize) const;
	void printLTL2DSTARForm() const;
    void minimiseUsingLanguageEquivalence();
	
	
};


//==================================================
// Define some hash-functions for unordered_sets
//==================================================
#include <tr1/unordered_set>
#include <boost/functional/hash.hpp>
#include <boost/tuple/tuple.hpp>
				 
namespace std { namespace tr1
	{
		template <>	struct hash<boost::tuple<int,int,int> > : public unary_function<boost::tuple<int,int,int>, size_t>
		{
			inline size_t operator()(const boost::tuple<int,int,int>& hist) const
			{
				std::size_t seed = 0;
				boost::hash_combine(seed, boost::get<0>(hist));
				boost::hash_combine(seed, boost::get<1>(hist));
				boost::hash_combine(seed, boost::get<2>(hist));
				return seed;
			}
		};
		
		template <>	struct hash<boost::tuple<int,int> > : public unary_function<boost::tuple<int,int>, size_t>
		{
			inline size_t operator()(const boost::tuple<int,int>& hist) const
			{
				std::size_t seed = 0;
				boost::hash_combine(seed, boost::get<0>(hist));
				boost::hash_combine(seed, boost::get<1>(hist));
				return seed;
			}
		};
	}
}


 

#endif

