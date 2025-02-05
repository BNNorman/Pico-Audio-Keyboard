'''
VL53_Keyboard

Normalises the key readings by dynamically adjusting the min/max


'''
from adafruit_tca9548a import TCA9548A,TCA9548A_Channel
from adafruit_vl53l0x import VL53L0X
import busio
import board
from digitalio import DigitalInOut,Direction,Pull
import sys

NUM_KEYS=8 	# also number of channels on the MUX


class Keyboard():
    def __init__(self,SDA,SCL,RST):
        # pins should be like board.GP2,board.GP3,board.GP4
        self.reset_pin=DigitalInOut(RST)
        self.reset_pin.direction=Direction.OUTPUT
        self.reset_pin.value=1 # Low to reset

        # as keys are read the min/max readings are updated
        # so that a 0..1 range can be calculated later
        self.minLevel=[1000]*NUM_KEYS	 # adjusted when keys are read
        self.maxLevel=[0]*NUM_KEYS       # ditto
        
        # last valid reading
        # if not data_ready then this value is used
        # updated as keys are read
        self.cache=[0.0]*NUM_KEYS 

        # create the mux
        try:
            self.i2c=busio.I2C(SCL,SDA) # MUX
            self.mux=TCA9548A(self.i2c) # using default MUX address 0x70
        except Exception as e:
            sys.exit(f"EXCEPTION: Unable to setup the MIDI Keyboard")

        # associate the 'key' sensors to the device channels
        self.tsl=[None]*NUM_KEYS
        for ch in range(NUM_KEYS):
            self.tsl[ch]=VL53L0X(self.mux[ch])
            # all the sensors run in parallel
            self.tsl[ch].start_continuous()
            self.tsl[ch].measurement_timing_budget = 33000 # us 
            #self.tsl[ch].io_timeout_s=0.02 # 2x timing budget

    def scanChannels(self):
        # check for sensors on each mux port
        for ch in range(NUM_KEYS):
            if self.mux[ch].try_lock():
                print(f"Ch {ch}, end=''")
                addresses = self.mux[channel].scan()
                print([hex(address) for address in addresses if address != 0x70])
                self.mux[channel].unlock()
                
    
    def normalise(self,ch,value):
        # map value to 0..1 range
        # check if value is outside the current range
        # if so adjust the range
        
        #print(f"Normalise value {value} min {self.minLevel[ch]} max {self.maxLevel[ch]}")
                    
        if value < self.minLevel[ch]:
            # update the minLevel
            self.minLevel[ch]=value
            
        elif value > self.maxLevel[ch]:
            self.maxLevel[ch]=value

        # return normalised value

        range=self.maxLevel[ch]-self.minLevel[ch]
        if range>0:
            return round((value-self.minLevel[ch])/range,2)
        # (val-min)/range would be an infinite value
        return self.maxLevel[ch]
        
    def getAllLevels(self):
        # read all the sensors and return a list of readings
        # sensor must be calibrated so they produce the same range 0..MAX_DIST
        levels=[0]*NUM_KEYS
        for ch in range(NUM_KEYS):
            
            if self.tsl[ch].data_ready:
                norm=self.normalise(ch,self.tsl[ch].distance)
                
                # there are glitches when the output is 90% less
                # if that happens in one pass it's a glitch
                if norm<0.1*levels[ch]:
                    levels[ch]=self.cache[ch]
                else:
                    levels[ch]=norm
                    self.cache[ch]=norm
            else:
                # if there's no data ready used the last reading to
                # smooth the changes
                # print("data not ready")
                levels[ch]=self.cache[ch]
                
        return levels

    def reset(self):
        import time
        print("Keyboard resetting")
        self.reset_pin.value=0
        time.sleep(0.001) # 500ns is all that's needed
        self.reset_pin.value=1
        time.sleep(0.1)
    
    def getNumKeys(self):
        return NUM_KEYS
            
    def dumpRanges(self):
        print("Min",self.minLevel)
        print("Max",self.maxLevel)
        
if __name__=="__main__":
    
    # SDA,SCL,RST
    kbd=Keyboard(board.GP2,board.GP3,board.GP4)
    import time
    
    print("Scanning channels/keys")
    #kbd.scanChannels()
    
    try:
        count=0
        while True:
            lev=kbd.getAllLevels()
            print(f"{count} {lev}")
            time.sleep(.2)
            count+=1
            
    except Exception as e:
        print("EXCEPTION ",e)
        kbd.dumpRanges()