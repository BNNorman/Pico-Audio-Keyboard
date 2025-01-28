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

HARMONICS=[1,2] # a list of harmonics to add e.g. [1,2,3,4] or [1,3,5]
LOOPS=["Music/loop2.wav"] # add all the loop you want here
LOOP_VOL=0.2

# access to the keyboard (SDA,SCL and RST)

keyboard=VL53_Keyboard.Keyboard(board.GP2,board.GP3,board.GP4)
keyboard.reset()

# audio output
try:
    # using the waveshare pico-Audio I2S pins
    audio = audiobusio.I2SOut(board.GP27, board.GP28, board.GP26) 
except Exception as e:
    exit(f"EXCEPTION: Unable to setup I2S, {e}")
    
mixer=audiomixer.Mixer(voice_count=keyboard.getNumKeys()+len(LOOPS), sample_rate=8000, channel_count=1,bits_per_sample=16, samples_signed=True)

def midiNoteFreq(note):
    # calculate freq of a midi note number
    # matches https://newt.phys.unsw.edu.au/jw/notes.html
    # midi keyboard starts at A0 (Note=21)
    # 1 octave = 12 steps/notes
    # frequency of A4 (common value is 440Hz)
    a = 440 
    return (a / 32) * (2 ** ((note - 9) / 12))
    
def makeSinewave(freq,vol):
    length = int(8000/freq)
    sine_wave = array.array("h", [0] * length)

    #print("length",length)
    
    for i in range(length):
        sine_wave[i] = int((math.sin(math.pi * 2 * i / length)) * vol * (2 ** 15 - 1))

    return sine_wave,length
    
def makeHarmonicTone(midiNote,vol=1.0):
    # create a 1 cycle note which will be played continuously
    base_freq=midiNoteFreq(midiNote)
    print("makeHArmonicTone Tone",midiNote,"=",base_freq)
    
    base_wave,base_len=makeSinewave(base_freq,1.0)
    
    # add the harmonics
    for h in HARMONICS:
        harmonic_wave,harmonic_len=makeSinewave(base_freq*(h+1),1.0)

        # merge the harmonic into the base_wave
        for p in range(base_len):

            try:
                # use average
                base_wave[p]=int((base_wave[p]+harmonic_wave[p % harmonic_len])//2)
            except Exception as e:
                print(f"Exception {e} base {base_wave[p]} harm {harmonic_wave[p % harmonic_len]}")
                
    #print("BASE WAVE AFTER",type(base_wave))
                
    print("Type final base_wave",base_wave)
    
    return audiocore.RawSample(base_wave)
    
    
    
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


octaveNotes=[None]*keyboard.getNumKeys()
loops=[None]*len(LOOPS)

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
        if len(HARMONICS)>0:
            octaveNotes[k]=makeHarmonicTone(midiNote+12*octave,1)
        else:
            octaveNotes[k]=makeTone(midiNote+12*octave,1)

def getLoops():
    global loops
    for l in range(len(LOOPS)):
        loops[l]=WaveFile(open(LOOPS[l],"rb"))
        

last_keys=[]
count=0
def setKeyLevels():
    # get the distance readings from the keyboard
    # and set the mixer channel levels accordingly
    # the keyboard normalises the key value to the range 0..1.0
    global last_keys,count
    distances=keyboard.getAllLevels()
    if distances!=last_keys:
        last_keys=distances
        print(f"{count} ",distances)
        count+=1
    for k in range(keyboard.getNumKeys()):
        # key values are return in normalise values 0..1.0
        # typical values will be 0..0.01
        # we need to remap them to range 0 .. 1.0 for controlling volume
        mixer.voice[k].level=MAX_DIST-min(distances[k],MAX_DIST)

# let's rock on

setMidiOctave(3) # A3..G3, configures all 8 keys
getLoops()
audio.play(mixer) # always playing we just adjust the volume of each note



if not mixer.playing:
    print("Starting Mixer")
    
    # only modulate the key volumes not the loops
    for k in range(keyboard.getNumKeys()):
        mixer.voice[k].play(octaveNotes[k],loop=True)
        mixer.voice[k].level=0
    for l in range(len(loops)):
        k=keyboard.getNumKeys()+l
        mixer.voice[k].play(loops[l],loop=True)
        mixer.voice[k].level=LOOP_VOL

try:
    print("mem_free",gc.mem_free())
    
    # Play voices updating volume levels
    while True:
        setKeyLevels()
except Exception as e:
    print("Player Exception",e)
    for k in range(keyboard.getNumKeys()):
        # silence the mixer
        mixer.voice[k].level=0
    
