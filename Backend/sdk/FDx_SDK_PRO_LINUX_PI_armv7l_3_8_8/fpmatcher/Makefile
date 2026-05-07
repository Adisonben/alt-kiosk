#*************************************************************
#*
#* Author :      SecuGen Corporation
#* Description : FPMatcher Makefile
#* Copyright(c): 2004 SecuGen Corporation, All rights reserved
#* History :
#* date        person   comments
#* ======================================================
#*
#*
#*************************************************************
PORT = pi
CPP=g++
#GTK1.0##########################
#CFLAGS = -D__LINUX
#INCPATH = -I./ -I../include `gtk-config --cflags`
#LIBS =  -L../lib/$(PORT) `gtk-config --libs`
#################################
#GTK1.2##########################
CFLAGS = -D__LINUX -D__GTK12
INCPATH = -I./ -I../include `pkg-config --cflags gtk+-2.0`
LIBS =  -L../lib/$(PORT) `pkg-config --libs gtk+-2.0`
#################################



OBJS=	main.o \
	interface.o \
	callbacks.o \
	configure.o

SRCS = main.cpp \
	interface.cpp \
	callbacks.cpp \
	configure.cpp


FDU03_TARGET = ../bin/$(PORT)/fpmatcher_fdu03
FDU04_TARGET = ../bin/$(PORT)/fpmatcher_fdu04
FDU05_TARGET = ../bin/$(PORT)/fpmatcher_fdu05
FDU06_TARGET = ../bin/$(PORT)/fpmatcher_fdu06
FDU07_TARGET = ../bin/$(PORT)/fpmatcher_fdu07
FDU08_TARGET = ../bin/$(PORT)/fpmatcher_fdu08

all : $(FDU08_TARGET) $(FDU07_TARGET) $(FDU06_TARGET) $(FDU05_TARGET) $(FDU04_TARGET) $(FDU03_TARGET)

#Hamster Pro 20 (U20-A, U20-AP)
$(FDU08_TARGET) : $(OBJS)
	$(CPP) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage -lsgfpamx -lsgfdu08 -lpthread -lusb

#Hamster Pro 10 (U10)
$(FDU07_TARGET) : $(OBJS)
	$(CPP) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage -lsgfpamx -lsgfdu07 -lpthread -lusb

#Hamster Pro (UPx)
$(FDU06_TARGET) : $(OBJS)
	$(CPP) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage -lsgfpamx -lsgfdu06 -lpthread -lusb

#Hamster Pro 20 (U20)
$(FDU05_TARGET) : $(OBJS)
	$(CPP) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage -lsgfpamx -lsgfdu05 -lpthread -lusb

#Hamster IV (FDU04)
$(FDU04_TARGET) : $(OBJS)
	$(CPP) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage -lsgfpamx -lsgfdu04 -lpthread -lusb

#Hamster Plus (FDU03)
$(FDU03_TARGET) : $(OBJS)
	$(CPP) -o $@ $(OBJS) $(LIBS) -lsgfplib -lsgnfiq -lsgimage -lsgfpamx -lsgfdu03 -lpthread -lusb

.cc.o :
	$(CPP) $(CFLAGS) $(INCPATH) -c $<

.c.o :
	$(CPP) $(CFLAGS) $(INCPATH) -c $<

.cpp.o :
	$(CPP) $(CFLAGS) $(INCPATH) -c $<

dep :
	gccmakedep $(INCPATH) $(SRCS)

clean :
	rm -rf *.raw *.min $(OBJS) $(FDU07_TARGET) $(FDU06_TARGET) $(FDU05_TARGET) $(FDU04_TARGET) $(FDU03_TARGET) core
	rm -rf $(PORT)
	mkdir $(PORT)
