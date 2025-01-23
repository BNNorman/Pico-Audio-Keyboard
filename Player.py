'''
Player.py
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
GP 4 RST

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

MAX_DIST=0.01
SCALE=0.5/MAX_DIST

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

def midiNoteFreq(note):
    # calculate freq of a midi note number
    # matches https://newt.phys.unsw.edu.au/jw/notes.html
    # midi keyboard starts at A0 (Note=21)
    # 1 octave = 12 steps/notes
    # frequency of A4 (common value is 440Hz)
    a = 440 
    return (a / 32) * (2 ** ((note - 9) / 12))
    

def makeTone(midiNote,vol=1.0):
    # create a 1 cycle note which will be played continuously
    freq=midiNoteFreq(midiNote)
    print("makeTone",midiNote,freq)
    
    tone_volume = vol  # Increase this to increase the volume of the tone.
    length = int(8000/freq)
    sine_wave = array.array("h", [0] * length)

    print("length",length)
    
    for i in range(length):
        sine_wave[i] = int((math.sin(math.pi * 2 * i / length)) * tone_volume * (2 ** 15 - 1))

    return audiocore.RawSample(sine_wave)


octaveNote=[None]*keyboard.getNumKeys()

def setMidiOctave(octave):
    # set the mixer channels to required octave frequencies
    # octave 0 starts at midiNote 21 (A0)
    # octave 4 starts at midiNote 69 (= 21+4*12)
    # add the frequencies to the mixer
    global octaveNotes
    
    # first octave minus 4 black keys i.e. Ax Bx Cx Dx Ex Fx Gx Ax+1
    baseNotes=[21,23,24,26,28,29,31,33]
    print("Setting up Octave ",octave)
    
    # set the frequencies
    for k in range(keyboard.getNumKeys()):
        midiNote=baseNotes[k]
        octaveNote[k]=makeTone(midiNote+12*octave)

    
def setKeyLevels():
    # get the distance readings from the keyboard
    # and set the mixer channel levels accordingly
    distances=keyboard.getAllLevels()
    
    for k in range(keyboard.getNumKeys()):
        # key values are return in normalise values 0..1.0
        # typical values will be 0..0.01
        mixer.voice[k].level=SCALE*(MAX_DIST-min(distances[k],MAX_DIST))

# let's rock on

setMidiOctave(3) # A4..G5, configures all 10 keys
audio.play(mixer) # always playing we just adjust the volume of each note

print("mem_free",gc.mem_free())

if not mixer.playing:
    print("Starting Mixer")
    #time.sleep(5)
    for k in range(keyboard.getNumKeys()):
        mixer.voice[k].play(octaveNote[k],loop=True)
        mixer.voice[k].level=0

try:
    # Play voices updating volume levels
    while True:
        setKeyLevels()
except Exception as e:
    print("Exception",e)
    for k in range(keyboard.getNumKeys()):
        # silence the mixer
        mixer.voice[k].level=0
    
