#! /usr/bin/env python
# -*- coding: ISO-8859-15 -*-
# 
# A wrapper for performing the task of minimizing deterministic Buechi automata
#
# (C) 2010 by Ruediger Ehlers
# Free for academic use

import getopt
import sys
import tempfile
import shutil
import os
import subprocess
import time

# Usage
usage = "DBA-minimize v.0.2 - (C) 2010/2011 by Ruediger Ehlers\n\nUsage: minimize.py [--timeout <nofSeconds>] inputFile.dba\n\nThe input file must be in the format as put out by the LTL2DSTAR tool. If the computation time of some call to the SAT solver exceeds the given number of seconds, the process is aborted and the best  automaton found is returned to the standard output.\n"

# Parse options
args = sys.argv[1:]
basePath = sys.argv[0].rsplit(os.sep,1)[0]
timeout = -1
try:
    (optlist, args) = getopt.getopt(args, 'x', ['timeout='])
except getopt.GetoptError:
    print usage
    exit(1)
if (len(args)<>1) or (len(optlist)>1):
    print usage
    exit(1)
if len(optlist)==1:
    try:
        timeout = float(optlist[0][1])
    except ValueError:
        print usage
        exit(1)


# Everything OK? Then let's go!
tempdir = tempfile.mkdtemp("")

# A function for cleaning up the temporary directory after we are done
def cleanUpTempDir(tempdir):
    for myfile in ["ref.dba","refPre.dba","ref.cnf","ref.picosat","new.dba"]:
        try:        
            os.remove(tempdir+os.sep+myfile)
        except OSError:
            # Ok, file probably wasn't there. Then it's all right...
            pass
    os.rmdir(tempdir)

# Copy the file there, "Büchinize it" and make some initial reduction
shutil.copy(args[0], tempdir+os.sep+"ref.dba")
cmdLine = basePath+os.sep+"Minimizer/buechinizer "+args[0]+" > "+tempdir+os.sep+"refPre.dba"
retVal = os.system(cmdLine)
if retVal<>0:
    sys.stderr.write(" Failed to run \""+cmdLine+"\" - command exited with an error\n")
    cleanUpTempDir(tempdir)
    exit(1)

cmdLine = basePath+os.sep+"Minimizer/prereducer "+tempdir+os.sep+"refPre.dba"+" > "+tempdir+os.sep+"ref.dba"
retVal = os.system(cmdLine)
if retVal<>0:
    sys.stderr.write(" Failed to run \""+cmdLine+"\" - command exited with an error\n")
    cleanUpTempDir(tempdir)
    exit(1)

# Go into the reduction loop
done = False
while not done:
    
    # Make CNF file 
    cmdLine = basePath+os.sep+"Minimizer/satbuilder "+tempdir+os.sep+"ref.dba "+tempdir+os.sep+"ref.cnf 1"
    retVal = os.system(cmdLine)
    if retVal<>0: # Failed or was killed
        sys.stderr.write(" Failed to run \""+cmdLine+"\" - command exited with an error\n")
        cleanUpTempDir(tempdir)
        exit(1)

    # Run picosat
    cmdLine = "picosat "+tempdir+os.sep+"ref.cnf > "+tempdir+os.sep+"ref.picosat"
    if timeout==-1:
        retVal = os.system(cmdLine)
    else:
        deadline = time.time() + timeout
        process = subprocess.Popen(cmdLine,shell=True)
        retVal = None
        while (retVal==None) and (time.time()<deadline):
            retVal=process.poll();
            time.sleep(0.1)
        if (retVal==None):
            # Kill process & print best result
            os.kill(process.pid,9)
            process.wait()
            bestOne = open(tempdir+os.sep+"ref.dba","r")
            for line in bestOne.readlines():
                print line,
            sys.stderr.write("Timeout!\n")
            cleanUpTempDir(tempdir)
            exit(0)
    if (retVal<>0) and (retVal<>20*256) and (retVal<>10*256) and (retVal<>20) and (retVal<>10): # Failed or was killed (other than for timeout reasons)
        sys.stderr.write(" Failed to run \""+cmdLine+"\" - command exited with an error\n")
        cleanUpTempDir(tempdir)
        exit(1)

    # Read back results
    # Open and check if it is satistiable
    satFile = open(tempdir+os.sep+"ref.picosat",'r')
    line = "c"
    while line[0]=='c':
        line = satFile.readline()
    if (line=="s SATISFIABLE\n"):
        cmdLine = basePath+os.sep+"Minimizer/reconstructor  "+tempdir+os.sep+"ref.dba "+tempdir+os.sep+"ref.picosat > "+tempdir+os.sep+"new.dba"
        retVal = os.system(cmdLine)
        if retVal<>0: # Failed or was killed
            sys.stderr.write(" Failed to run \""+cmdLine+"\" - command exited with an error\n")
            cleanUpTempDir(tempdir)
            exit(1)
        # Copy to "ref.dba"
        shutil.copy(tempdir+os.sep+"new.dba",tempdir+os.sep+"ref.dba")
    else:
        done = True

# Print out best found result
bestOne = open(tempdir+os.sep+"ref.dba","r")
for line in bestOne.readlines():
    print line,
bestOne.close()
cleanUpTempDir(tempdir)
exit(0)

