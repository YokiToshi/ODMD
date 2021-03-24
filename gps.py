import serial
import time
import shlex, subprocess

#DebugMode = False

 
BtMacID           = "00:0B:0D:8E:A3:B5"
rfcommPortPraefix = "/dev/rfcomm" # This präefix is used by rfcomm bt connection and is constant
rfcommPortNumber  = "0"
SerialGpsPortName = rfcommPortPraefix + rfcommPortNumber # this port has to be connected with the GPS devoce


#sudo apt-get update
#sudo apt-get install bluetooth
#sudo apt-get install bluez
#sudo apt-get install python-bluez
#sudo pip3 install pybluez
import bluetooth

def getBtMacAddress(p_target_name):
  global DebugMode

  
  target_address = None
  print("looking for bt device", p_target_name)

  nearby_devices = bluetooth.discover_devices()

  for bdaddr in nearby_devices:
    if p_target_name == bluetooth.lookup_name( bdaddr ):
      target_address = bdaddr
      break

  if target_address is not None:
    print( "found target bluetooth device with address ", target_address)
  else:
    print ("could not find target bluetooth device nearby")
  return target_address


def decode_coord(coord):
    global DebugMode

    #Converts DDDMM.MMMMM > DD:MM.MMMMM
    try:
        x = coord.split(".")
        if len(x)>=2:
            # if i dont check this, the function sometimes crashes
            head = x[0]
            tail = x[1]
            deg = head[0:-2]
            min = head[-2:]
    
            return deg + ":" + min + "." + tail
        else:
            if DebugMode: print("error in decode_coord: " + coord)
            return None
    
    except:
        return None


def parseGPS(data_in):
    global DebugMode
    
    rc_gps_dict = dict()
    data=data_in.decode('utf-8')
    if DebugMode: print ("raw:", data) #prints raw data
    if DebugMode: print ("record type: " + data[0:6])
    
    if (data[0:6] == "$GPRMC"):
        sdata = data.split(",")
        if len(sdata)<9:
            return None
        if sdata[2] == 'V':
            if DebugMode:
                time = sdata[1][0:2] + ":" + sdata[1][2:4] + ":" + sdata[1][4:6]
                print ("no satellite position data available "+ time)
            return
        ##print ("---Parsing GPRMC---")
        time = sdata[1][0:2] + ":" + sdata[1][2:4] + ":" + sdata[1][4:6]
        lat = decode_coord(sdata[3]) #latitude
        dirLat = sdata[4]          #latitude direction N/S
        lon = decode_coord(sdata[5]) #longitute
        dirLon = sdata[6]          #longitude direction E/W
        speed = sdata[7]           #Speed in knots
        speedKM = str( round(float(speed)*1.852, 2) )
        trCourse = sdata[8]        #True course
        date = sdata[9][0:2] + "." + sdata[9][2:4] + ".20" + sdata[9][4:6] #date

        if lon==None or lat==None:
            return None
        gps_string ="time : %s, latitude : %s(%s), longitude : %s(%s), speed : %s, speedKM : %s, True Course : %s, Date : %s" %  (time,lat,dirLat,lon,dirLon,speed,speedKM,trCourse,date) 
        if DebugMode: print(gps_string)
        
        rc_gps_dict= dict(g_date=date, g_time=time, g_lat=lat, g_dirLat=dirLat, g_lon=lon, g_dirLon=dirLon, g_speed=speed, g_speedKM=speedKM, g_trCourse=trCourse, g_string=gps_string)
    else:
        if DebugMode: print ("not a $GPRMC record")
        
    return rc_gps_dict



def releaseBtGps(p_rfcommPortNumber):
    global DebugMode

    try:
        #subprocess.run(["rfcomm", "release", rfcommPort])
        p.subprocess.Popen(["rfcomm", "release", p_rfcommPortNumber], stdout=subprocess.PIPE)
        result = p.communicate()[0]
        print (result)
        # Can't release device: No such device
        return True
    except:
        return False


def connectBt2Serial(p_rfcommPortNumber, p_BtMacID):
    
    global SerialGpsPortName
    global DebugMode

    SerialGpsPortName = rfcommPortPraefix + p_rfcommPortNumber
    
    try:
        Prc = subprocess.run(["sudo", "rfcomm", "bind", p_rfcommPortNumber, p_BtMacID])
        # Can't create device: Address already in use
        if Prc.returncode != 0:
          return False

        return True
    except:
        print("exception in connectBt2Serial")
        return False


def initSerialGPS(p_SerialGpsPortName):
    global DebugMode

    try:
        if DebugMode: print("Initialice: " + p_SerialGpsPortName)
        ser_rc = serial.Serial(p_SerialGpsPortName, baudrate = 9600, timeout = 1.0)
    except:
        if DebugMode: print("could not use: " + p_SerialGpsPortName)
        ser_rc = None

    return ser_rc


def initBtGps(p_rfcommPortNumber, p_BtMacID):
    """Connects the bt gps to a serial port and opens this serial port"""
    global SerialGpsPortName
    global DebugMode

    ser = None
    #gps.checkBtGps()
    releaseBtGps(p_rfcommPortNumber)
    print("connect BT " + p_BtMacID + " to serial %s" % p_rfcommPortNumber )
    if connectBt2Serial(p_rfcommPortNumber, p_BtMacID):
        print("connect serial port " + SerialGpsPortName)
        time.sleep(1)
        ser=initSerialGPS(SerialGpsPortName)
        if ser == None:
            print("could not open: " + SerialGpsPortName)
        else: 
            print("device opend: " + SerialGpsPortName)
    else:
        print("could not connect BT " + p_BtMacID + " to serial " + p_rfcommPortNumber )
        ser = None
    return ser


def reconnectGps():
    global DebugMode

    if DebugMode: print("reconnectGps")
    # #################
    

SerialErrorCount = 0
SerialErrorLoopCount = 0

def readGPS(p_ser):
    global SerialErrorCount
    global SerialErrorLoopCount
    global DebugMode

    rc_gps_dict = None
    rc = False
    data = None
    
    try:
        n = 0
        while n<=6 and (data == None or data==""):
            n = n + 1
            if DebugMode: print("read serial n=" + str(n))
            data = p_ser.readline()
        rc = True
    except:
        SerialErrorCount = SerialErrorCount + 1
        if SerialErrorCount == 1:
            if DebugMode: print("could not read from serial port errc="+str(SerialErrorCount))
        elif SerialErrorCount == 5:
            SerialErrorCount = 0
            SerialErrorLoopCount = SerialErrorLoopCount + 1
            if SerialErrorLoopCount > 5:
                reconnectGps()

    if data != None:
        if data != "":
            rc_gps_dict = parseGPS(data)
    else:
        rc = False

    return rc, rc_gps_dict

