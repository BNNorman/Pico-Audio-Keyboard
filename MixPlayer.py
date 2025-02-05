'''
MixPlayer.py
The VL53_Keyboard consists of 10 VL53L0X sensors which are multiplexed and free running.
The driver returns key values normalised to the range 0 .. 1.0

1.0 represents the max distance 0.819m. In practice fingering the keyboard should
produce values 0 .. 0.01


Waveshare pico-audio
GP 26
GP 27
GP 28

I2C - connection to "keyboard" via TCA9548 I2C MUX
GP 2 SDA
GP 3 SCL
GP 4 RST resets the MUX

'''

import board
import busio
import audiobusio
import audiocore
import audiomixer
import digitalio
import sys

import random # for testing only
import array
import math
import VL53_Keyboard 
import gc
import time

from audiocore import WaveFile

MAX_DIST=0.1 # scale is 0..1.0 # min..max

# left hand plays rythm loops, right plays single
# max number = keys on keyboard (8)
LOOPS=[
    # left hand
    "Music/tom-toms_phrase.wav",
    "Music/bass-drum_rhythm.wav",
    "Music/tam-tam_phrase.wav",
    "Music/tenor-drum_phrase.wav",
    # right hand
    "Music/bass-drum.wav",
    "Music/tom-tom.wav",
    "Music/tam-tam.wav",
    "Music/tenor-drum.wav"
       ]

# access to the keyboard (SDA,SCL and RST)

keyboard=VL53_Keyboard.Keyboard(board.GP2,board.GP3,board.GP4)
keyboard.reset()

# audio output
try:
    # using the waveshare pico-Audio I2S pins
    audio = audiobusio.I2SOut(board.GP27, board.GP28, board.GP26) 
except Exception as e:
    exit(f"EXCEPTION: Unable to setup I2S, {e}")
    
mixer=audiomixer.Mixer(voice_count=keyboard.getNumKeys(), sample_rate=8000, channel_count=1,bits_per_sample=16, samples_signed=True)
audio.play(mixer) # add loops after , always playing we just adjust the volume of each loop

loops=[None]*len(LOOPS)

def getLoops():
    global loops, mixer
    for v in range(len(LOOPS)):
        #print(f"Loading wav file {LOOPS[l]}")
        loops[v]=WaveFile(open(LOOPS[v],"rb"))
        mixer.voice[v].play(loops[v],loop=True)
        mixer.voice[v].level=0.0 # silent for now
        print(f"playing {v} playing {mixer.voice[v].playing}")


last_keys=[]
count=0
def setLoopLevels():
    # get the distance readings from the keyboard
    # and set the mixer channel levels accordingly
    # the keyboard normalises the key value to the range 0..1.0
    global last_keys,count
    distances=keyboard.getAllLevels()
    
    if distances!=last_keys:
        last_keys=distances
        print(f"{count} ",distances) # just makes it obvious on screen
        count+=1
    for k in range(keyboard.getNumKeys()):
        # key values are return in normalise values 0..1.0
        # typical values will be 0..0.01
        # we need to remap them to range 0 .. 1.0 for controlling volume
        mixer.voice[k].level=MAX_DIST-min(distances[k],MAX_DIST)
        
# let's rock on

getLoops()

for l in range(len(LOOPS)):
    print(f"{l} playing {mixer.voice[l].playing}")

try:
    print("mem_free",gc.mem_free())
    
    # Play voices updating volume levels
    while True:
        setLoopLevels()
        time.sleep(.2) # cannot be faster
        
except Exception as e:
    print("Player Exception",e)
    for k in range(keyboard.getNumKeys()):
        # silence the mixer
        mixer.stop_voice[k]
    
