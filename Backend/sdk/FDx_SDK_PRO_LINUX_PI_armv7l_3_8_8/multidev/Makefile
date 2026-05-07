#*************************************************************
#*
#* Author :      SecuGen Corporation
#* Description : FPLibTest Makefile
#* Copyright(c): 2009 SecuGen Corporation, All rights reserved
#* date        person   comments
#* ======================================================
#* 12/10/2009  driley   initial release
#*
#*************************************************************

PORT = pi
CFLAGS = -Wall -O
CXX=g++
CC=gcc
INCPATH = -I./ -I../include
LIBS =  -L../lib/$(PORT)

OBJS=	main.o

SRCS=	main.cpp

FDU03_TARGET = ../bin/$(PORT)/multidev_fdu03
FDU04_TARGET = ../bin/$(PORT)/multidev_fdu04
FDU05_TARGET = ../bin/$(PORT)/multidev_fdu05
FDU06_TARGET = ../bin/$(PORT)/multidev_fdu06
FDU07_TARGET = ../bin/$(PORT)/multidev_fdu07
FDU08_TARGET = ../bin/$(PORT)/multidev_fdu08

all : $(FDU08_TARGET) $(FDU07_TARGET) $(FDU06_TARGET) $(FDU05_TARGET) $(FDU04_TARGET) $(FDU03_TARGET)

#Hamster Pro 20 (U20-A, U20-AP)
$(FDU08_TARGET) : $(OBJS)
	$(CXX) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage -lsgfpamx -lsgfdu08 -lpthread  -lusb

#Hamster Pro 10 (U10)
$(FDU07_TARGET) : $(OBJS)
	$(CXX) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage -lsgfpamx -lsgfdu07 -lpthread  -lusb

#Hamster Pro (UPx)
$(FDU06_TARGET) : $(OBJS)
	$(CXX) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage -lsgfpamx -lsgfdu06 -lpthread  -lusb

#Hamster Pro 20 (U20)
$(FDU05_TARGET) : $(OBJS)
	$(CXX) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage  -lsgfpamx -lsgfdu05 -lpthread  -lusb

#Hamster IV (FDU04)
$(FDU04_TARGET) : $(OBJS)
	$(CXX) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage  -lsgfpamx -lsgfdu04 -lpthread  -lusb

#Hamster Plus (FDU03)
$(FDU03_TARGET) : $(OBJS)
	$(CXX) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage  -lsgfpamx -lsgfdu03 -lpthread  -lusb

.cc.o :
	$(CXX) $(FLAGS) $(INCPATH) -c $<

.c.o :
	$(CXX) $(FLAGS) $(INCPATH) -c $<

.cpp.o :
	$(CXX) $(FLAGS) $(INCPATH) -c $<

dep :
	gccmakedep $(INCPATH) $(SRCS)

clean :
	rm -rf *.raw *.min $(OBJS) $(FDU04_TARGET) $(FDU03_TARGET)  core
	rm -rf $(PORT)
	mkdir $(PORT)

