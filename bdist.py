#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Creation:    03.08.2013
# Last Update: 07.04.2015
#
# Copyright (c) 2013-2015 by Georg Kainzbauer <http://www.gtkdb.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

#
# Changed 2019 by Klaus Schneider
# PYTHON3!!
#
# Messurement of distance to overtaking cars
# Distances are stored to a csv file
# If available gps information is stored also
#

# import required modules

# GUI
from tkinter import *
import tkinter.font as tkFont

# time
import time
from datetime import datetime

#GPIO
import RPi.GPIO as GPIO

# import to connect gps
import gps

# To call system. Set system time, or shutdown
import subprocess


# DebugMode=True activates some print outputs with
# informations about the program run
DebugMode = False
gps.DebugMode = DebugMode


DispIntervalGps = 1000
DispInt = 200
MaxDistanceToDisplay = 200 # Oberhalb dieser Entfernung (cm) werden Werte nicht angezeigt
MaxDistanceToStore   = 180

# GPIO ###################################
# define GPIO pins
# ultrasonic distance messurement
GPIOTrigger = 18  # GPIO-Pin 12
GPIOEcho    = 17  # GPIO-Pin 11
# external button as a event marker
GPIOTaster1 = 16  # GPIO-Pin 36
GPIOinitialiced = False

def setup_gpio():
  ###if DebugMode:
  GPIO.VERSION

  GPIO.setwarnings(False)

  # use GPIO pin numbering convention
  GPIO.setmode(GPIO.BCM)

  # set up GPIO pins
  GPIO.setup(GPIOTrigger, GPIO.OUT)
  GPIO.setup(GPIOEcho,    GPIO.IN)
  GPIO.setup(GPIOTaster1, GPIO.IN, pull_up_down=GPIO.PUD_UP)

  # set trigger to false
  GPIO.output(GPIOTrigger, False)

  #Set Taster-Event (Der Taster ist als Schließer gegen GND geschaltet)
  GPIO.add_event_detect(GPIOTaster1, GPIO.FALLING, callback=do_Taster1Event, bouncetime=200)
  print('Taster1 Event initialisiert')

  GPIOinitialiced = True
  
#endDef setup_gpio


# csv file to store messurements ##################
Filename = ""
OutFile = None

def openCsvFile():
  global FileName

  FileName = 'Dist_' + time.strftime("%Y%m%d_%H%M%S") + '.csv'
  OutFile = open(FileName, 'x')
  OutFile.write("Date;Time;Event;Distance;Dist Unit;GPS Time;GPS Speed;GPS Long;GPS Long Dir;GPS Lat;GPS Lat Dir\n")
  if DebugMode:
    print("Datei geoeffnet: "+FileName)
  return OutFile
#endDef


# end routine ###########################
ExitInitiated=False

def endProgram():
    global ExitInitiated
    global OutFile
    global FileName
    global GPIOinitialiced

    if not ExitInitiated:
      ExitInitiated=True
      print("Measurement stopped by user")
      lbl_message.config(font=("Arial", 30))
	  
      if not OutFile==None:
        messageText.set("File: "+FileName)
        print("File closed: "+FileName)
        OutFile.close()

      if GPIOinitialiced:
        GPIO.cleanup()

      runButton.pack_forget()
      endButton.pack_forget()
      lbl_gps.pack_forget()
      lbl_ExtButton1.pack_forget()
    else:
      #endButton.pack_forget()
      quitButton.pack(side = LEFT)
      shutdownButton.pack(side = LEFT)
      #time.sleep(5)
      #win.quit()
#endDef 

def quitProgram():
    win.destroy()
#endDef 

def shutdownPI():
    subprocess.run(["sudo", "shutdown", "now"])
#endDef 


# messure distance ##########################
DistanceMin1SecIni = 300
# Minimum distance in interval
DistanceMin1Sec    = DistanceMin1SecIni
DistanceMin1SecTime = time.time()
DistanceNULL = 0

# function to measure the distance
def MeasureDistance():
  global DistanceMin1Sec
  global DistanceMin1SecTime
  global DistanceNULL
  
  # Timeout while waiting to messure to big distances
  MaxTimeoutCount=5000
  N=1 

  # start sensor  -------------
  # set trigger to high
  GPIO.output(GPIOTrigger, True)
  # set trigger after 10µs to low
  time.sleep(0.00001)
  GPIO.output(GPIOTrigger, False)
  # store initial start time
  StartTime = time.time()

  # store start time
  N=1 
  while GPIO.input(GPIOEcho) == 0 and N<10000:
    N=N+1
  StartTime = time.time()
  if N >= MaxTimeoutCount:
    print("timeout on: GPIO store start time") 
    return DistanceNULL

  # store stop time
  N=1 
  while GPIO.input(GPIOEcho) == 1 and N<MaxTimeoutCount:
    N=N+1
  StopTime = time.time()
  if N >= MaxTimeoutCount:
    print("timeout on: GPIO store stop time") 
    return DistanceNULL

  # calculate distance
  TimeElapsed = StopTime - StartTime
  if DebugMode:
    print("%.5f " % TimeElapsed)
    print("%.1f " % N)

  if N < MaxTimeoutCount:
    Distance = (TimeElapsed * 34300) / 2
    
    if (StopTime - DistanceMin1SecTime) > 1 or Distance <= DistanceMin1Sec:
      # Min distance has to be refrehed
      DistanceMin1Sec = Distance
      DistanceMin1SecTime = StopTime
  else:
    return DistanceNULL
	
  return Distance
#endDef MeasureDistance


# external button event #######################
Taster1Pushed = False
Taster1PushedTime = None

def do_Taster1Event(channel):
  global Taster1Pushed
  global Taster1PushedTime
  global lbl_ExtButton1

  print('Taster wurde gedrueckt')
  Taster1Pushed = True
  Taster1PushedTime = time.time()
  lbl_ExtButton1.config(bg="red")
#endDef 
	
def switchDebugMode():
   global debugButton
   global DebugMode
   
   if DebugMode:
     print('Switch DebugMode off')
     DebugMode = False
     debugButton.config(bg="light grey")
   else:
     print('Switch DebugMode on')
     DebugMode = True
     debugButton.config(bg="light green")
#endDef 


def undo_Taster1Event():
  global Taster1Pushed
  global Taster1PushedTime

  Taster1Pushed = False
  Taster1PushedTime = None
  lbl_ExtButton1.config(bg="light green")
#endDef 


def Utc2Local(p_DatetimeUtc):
  epoch = time.mktime(p_DatetimeUtc.timetuple())
  offset = datetime.fromtimestamp (epoch) - datetime.utcfromtimestamp ( epoch )
  return p_DatetimeUtc + offset
  
SystemTimeSet = 0

def setSystemTime(p_DateString, p_TimeString, p_TimeZone):
  global SystemTimeSet
  
  try:
    SystemTimeSet = SystemTimeSet + 1
    if SystemTimeSet >= 10: return 
    if DebugMode: print("setSystemTime %s %s %s" % (p_DateString, p_TimeString, p_TimeZone))
    CurrentDateTime = datetime.now()
    DateTimeFromParmString = Utc2Local( datetime.strptime("%s %s %s" % (p_DateString, p_TimeString, p_TimeZone), "%d.%m.%Y %H:%M:%S %Z") )
    if DebugMode: print("delta seconds to gps time %d" % ( (DateTimeFromParmString - CurrentDateTime).total_seconds()) )
    if abs((DateTimeFromParmString - CurrentDateTime).total_seconds() ) >= 10:
       # delta >= 10 seconds
      TimeString4Update = datetime.strftime(DateTimeFromParmString, "%m%d%H%M%y") # "MMDDHHMIYY"
      if DebugMode: print("TimeString4Update %s" % TimeString4Update )
      subprocess.run(["sudo", "date", TimeString4Update])
      -print("system time updated "+TimeString4Update)
    else:
      if DebugMode: print("no system time updated needed")
  except:
    print("exception in setSystemTime %s %s %s" % (p_DateString, p_TimeString, p_TimeZone) )
    return
    


gps_dict = None

# running messurements, display and store to output file ####
def ReadGpsAndShow():
  global DispIntervalGps
  global serialDevice
  global gps_dict

  # read gps
  rc = False
  gps_dict = None
  
  try:
      if ExitInitiated:  # Exit wurde begonnen und für Anzeige unterbrochen
        endProgram()
        return

      CurrentTime = time.time()

      # read from serial gps
      if serialDevice != None:
        n = 0
        while n<=9 and (gps_dict=={} or gps_dict == None):
          # serveral empty records hav to be read from serial port
          # WHY ???????????????????????
          n = n+1
          rc, gps_dict = gps.readGPS(serialDevice)
          if rc:
            if DebugMode: print("readGPS: ok n="+ str(n))
            if gps_dict != {} and gps_dict != None:
                if DebugMode: print("gps data: ", gps_dict)
                lbl_gps.config(bg="light green")
                messageTextGpsStatus.set("GPS "+ gps_dict.get('g_time'))
                #print(gps_dict.get('g_date',"01.01.1970"))
                #print(gps_dict.get('g_time', "00:00:00"))
                setSystemTime(gps_dict.get('g_date',"01.01.1970"), gps_dict.get('g_time', "00:00:00"), "UTC")
                DispIntervalGps=500
            else:
                if DebugMode: print("readGPS no position data")
                gps_dict = None
                lbl_gps.config(bg="yellow")
                messageTextGpsStatus.set("GPS wait")
                DispIntervalGps=3000

      if serialDevice == None or rc == False:
          # read not ok
          lbl_gps.config(bg="red")
          messageTextGpsStatus.set("no GPS")
          DispIntervalGps=8000
          if DebugMode: print("reconnect")
          if not rc:
            if DebugMode: print("close serial port")
            #serialDevice.close()
            serialDevice.__del__()
          serialDevice = gps.initBtGps(gps.rfcommPortNumber, gps.BtMacID)
          if serialDevice == None:
            # reconnect does not work on serial device!!!!!
            serialDevice = initSerialGPS("/dev/ttyACM0")
          #serialDevice=gps.initSerialGPS(gps.SerialGpsPortName)

      if DebugMode: print("      win.after("+str(DispIntervalGps)+", ReadGpsAndShow)")
      win.after(DispIntervalGps, ReadGpsAndShow)

  # reset GPIO settings if user pressed Ctrl+C
  except KeyboardInterrupt:
    endProgram()
	
#endDef ReadGpsAndShow

	
# running messurements, display and store to output file ####
def MessureAndShow():
  global DispInt
  global Taster1Pushed
  global Taster1PushedTime
  global OutFile
  global MaxDistanceToDisplay
  global MaxDistanceToStore
  
  global gps_dict

  global DistanceMin1Sec

  try:
      if ExitInitiated:  # Exit wurde begonnen und für Anzeige unterbrochen
        endProgram()
        return

      CurrentTime = time.time()
      
      # Messure distance
      Distance = MeasureDistance()

      TimeString=time.strftime("%H:%M:%S")
      EventString=""
      
      if Taster1PushedTime != None:
        if (CurrentTime - Taster1PushedTime) >= 3.0:
          undo_Taster1Event()
      if Taster1Pushed:
         EventString="T1"
         if Distance != DistanceNULL:
           if Distance > 150:
             topFrame.config(bg="light green")
           elif Distance > 100:
             topFrame.config(bg="yellow")
           else:
             topFrame.config(bg="orange")
      else:
        topFrame.config(bg="grey")

      MText=TimeString + "\n---"
      if Distance != DistanceNULL:
        DateString=time.strftime("%Y-%m-%d")
        if Distance<=MaxDistanceToStore or Taster1Pushed:
          if DebugMode: print("write distance data to csv  -->")
          OutFile.write(DateString + ";" + TimeString + ";" + EventString + ";%.0f;cm" % Distance)
          if gps_dict != None:
            if DebugMode: print("write gps data to csv  -------->")
            # Struct. gps_dict:
            #         d_date, g_time, g_lat, g_dirLat, g_lon,
            #         g_dirLon, g_speed, g_speedKM, g_trCourse, g_string)
            # Struct. CSV file:
            #         Date;Time;Event;Distance;Dist Unit;GPS Time;GPS Speed;GPS Long;GPS Long Dir;
			#         GPS Lat;GPS Lat Dir
            OutFile.write(";%s;%s;%s;%s;%s;%s" % ( gps_dict.get('g_time',"") , gps_dict.get('g_speedKM',""), gps_dict.get('g_lon',""), gps_dict.get('g_dirLon',""), gps_dict.get('g_lat',""), gps_dict.get("g_dirLat","") ) )
          OutFile.write("\n")
          
        if Distance <= MaxDistanceToDisplay:
          # set text for display
          MText = TimeString + " " + EventString + "\n%.0f cm" % ( DistanceMin1Sec )
          #MText=TimeString + " " + EventString + "\n%.0f  %.0f cm" % (Distance, DistanceMin1Sec)
      if DebugMode: print(MText)
      messageText.set(MText)
      lbl_message.config(font=("Arial", 104))

      if DebugMode: print("      win.after("+str(DispInt)+", MessureAndShow)")
      win.after(DispInt, MessureAndShow)

  # reset GPIO settings if user pressed Ctrl+C
  except KeyboardInterrupt:
    endProgram()
	
#endDef MessureAndShow

	
serialDevice = None

# start function
def runProgram():
  global OutFile
  global serialDevice

  setup_gpio()

  OutFile=openCsvFile()
   
  runButton.pack_forget()

  MessureAndShow()
#endDef 
  

# Create Main Window
win = Tk()
myFont = tkFont.Font(family = 'Helvetica', size = 36, weight = 'bold')
win.title("measure overtaking distance")
win.geometry('800x480')

topFrame =Frame(win, bg="grey")
topFrame.pack(fill=X, ipady=2)

bottomFrame =Frame(win, bg="grey")
bottomFrame.pack(side = BOTTOM)

messageTextGpsStatus = StringVar()
messageTextGpsStatus.set("GPS")
lbl_gps = Label(topFrame,textvariable=messageTextGpsStatus, bd=1, relief="solid", font="Arial 20", bg = "orange", width=13, height=2)
lbl_gps.pack(side="left",padx=10)

runButton  = Button(topFrame, text = "Start measure", font = myFont, command = runProgram, height =1 , width = 12)
runButton.pack(side="left",padx=10)

messageTextExtButton1Status = StringVar()
messageTextExtButton1Status.set("Ext Button")
lbl_ExtButton1 = Label(topFrame,textvariable=messageTextExtButton1Status, bd=1, relief="solid", font="Arial 20", bg = "light green", width=14, height=2)
lbl_ExtButton1.pack(side="left",padx=10)

debugButton  = Button(bottomFrame, text = "Debug", font = myFont, command = switchDebugMode, height =1 , width = 6) 
debugButton.pack(side = RIGHT)
if DebugMode:
  debugButton.config(bg="light green")
else:
  debugButton.config(bg="light grey")

endButton  = Button(bottomFrame, text = "End", font = myFont, command = endProgram, height =1 , width = 6) 
endButton.pack(side = LEFT)

quitButton  = Button(bottomFrame, text = "Quit", font = myFont, command = quitProgram, height =1 , width = 6) 

shutdownButton  = Button(bottomFrame, text = "SHUTDOWN", font = myFont, command = shutdownPI, height =1 , width = 11) 


messageText = StringVar()
messageText.set("overtaking distance")
lbl_message= Label(win,textvariable=messageText, bd=1, relief="solid", font="Arial 68", height=3)
lbl_message.pack(fill=BOTH)


BtDeviceName = "iBT-GPS"

# call main function
if __name__ == '__main__':
  ExitInitiated=False

  serialDevice = gps.initSerialGPS("/dev/ttyACM0")
  if serialDevice == None:
    BtMacID = gps.getBtMacAddress(BtDeviceName)
    if BtMacID==None:
      BtMacID=gps.BtMacID
    serialDevice = gps.initBtGps(gps.rfcommPortNumber, BtMacID)
  
  ReadGpsAndShow()

  win.mainloop()
