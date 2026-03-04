.cpp.o:
	g++ -c -O3 -o $@ $<

default: reconstructor satbuilder dotbuilder buechinizer prereducer

prereducer: buechi_basics.o main_prereducer.o
	g++ -o $@ buechi_basics.o main_prereducer.o

reconstructor: buechi_basics.o main_reconstructor.o
	g++ -o $@ buechi_basics.o main_reconstructor.o

satbuilder: buechi_basics.o main_satbuilder.o sat_solving_minimizer.o
	g++ -o $@ buechi_basics.o main_satbuilder.o sat_solving_minimizer.o

dotbuilder: buechi_basics.o main_dotconverter.o
	g++ -o $@ buechi_basics.o main_dotconverter.o

buechinizer: buechi_basics.o main_buechinizer.o
	g++ -o $@ buechi_basics.o main_buechinizer.o

clean:
	rm *.o
