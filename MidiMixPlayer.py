'''
MidiMixPlayer.py

The VL53_Keyboard consists of 8 VL53L0X sensors which are multiplexed and free running.
The driver returns key values normalised to the range 0 .. 1.0

Single notes or chords can be assigned to each key

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
import audiomixer
import sys

import random # for testing only
import VL53_Keyboard 
import gc
import time
import synthio
from audiocore import WaveFile # for backing tracks
import traceback
import ulab.numpy as np


BACKING_LOOPS=["Music/drum_loop_44100.wav"]
BACKING_VOL=0.1
KEYBOARD_VOL=0.2


def makeChord(midiRoot,octave,major=True):
    A=midiRoot
    B=A+4
    C=A+7
    if not major:
        B=A+3
    # adjust for octave
    # octave 4 is where we find middle C
    # but it is 60/12=5 so I bump the octave by 1
    oct=octave+1
    A=A+12*oct
    B=B+12*oct
    C=C+12*oct
    print(f"Chord {midiRoot} oct:{octave} major:{major} {A},{B},{C}")
    return [A,B,C]

# one per key on the keybord
# using 'natural' notes
MIDI_NOTES=[makeChord(0,4), # "middle C"
            makeChord(2,4),
            makeChord(4,4),
            makeChord(5,4),
            makeChord(7,4),
            makeChord(9,4),
            makeChord(11,4),
            makeChord(12,4),
            ]

SAMPLE_RATE=44100

print("Setting up the synth")

# create sine, tri, saw & square single-cycle waveforms to act as oscillators
SAMPLE_SIZE = 512
SAMPLE_VOLUME = 32000  # 0-32767
#half_period = SAMPLE_SIZE // 2

# wave forms (default is square)
wave_sine = np.array(np.sin(np.linspace(0, 2*np.pi, SAMPLE_SIZE, endpoint=False)) * SAMPLE_VOLUME,dtype=np.int16)
wave_saw = np.linspace(SAMPLE_VOLUME, -SAMPLE_VOLUME, num=SAMPLE_SIZE, dtype=np.int16)
synth = synthio.Synthesizer(sample_rate=SAMPLE_RATE,waveform=wave_sine)

#envelopes
amp_env_slow = synthio.Envelope(attack_time=0.2,sustain_level=1.0,release_time=0.8)
amp_env_fast = synthio.Envelope(attack_time=0.1,sustain_level=0.5,release_time=0.2)

synth.envelope=amp_env_fast
synth.release_all()

# access to the "midi" keyboard (SDA,SCL and RST)
print("Setting up the keyboard")
keyboard=VL53_Keyboard.Keyboard(board.GP2,board.GP3,board.GP4)
keyboard.reset()
NUM_KEYS=keyboard.getNumKeys()

# audio output
try:
    # using the waveshare pico-Audio I2S pins
    print("Setting up I2S")
    audio = audiobusio.I2SOut(board.GP27, board.GP28, board.GP26) 
except Exception as e:
    sys.exit(f"EXCEPTION: Unable to setup I2S, {e}")
    
    
num_mixer_voices=len(BACKING_LOOPS)+1 # synthio all goes through one extra voice

print("num_mixer_voices",num_mixer_voices)
mixer=audiomixer.Mixer(voice_count=num_mixer_voices, sample_rate=SAMPLE_RATE, channel_count=1,bits_per_sample=16, samples_signed=True)
audio.play(mixer) # must start the mixer before adding voices 

# something to hold the wavefiles for the mixer backing loops
backing_loops=[None]*len(BACKING_LOOPS)

def setMixerVoices():
    global loops, mixer,synth
    # add any backing loops
    NUM_LOOPS=len(BACKING_LOOPS)
    if NUM_LOOPS>0:
        print("Setting backing loops")
        for v in range(NUM_LOOPS):
            #print(f"Loading wav file {BACKING_LOOPS[l]}")
            backing_loops[v]=WaveFile(open(BACKING_LOOPS[v],"rb"))
            mixer.voice[v].play(backing_loops[v],loop=True)
            mixer.voice[v].level=BACKING_VOL

    # synthio all through one extra channel
    print(f"Adding synth to mixer")
    mixer.voice[NUM_LOOPS].play(synth)
    mixer.voice[NUM_LOOPS].level=KEYBOARD_VOL

def playKeys():
    # get the distance readings from the keyboard
    # and set the mixer channel levels accordingly
    # the keyboard normalises the key value to the range 0..1.0
    global synth,keyboard
    synth.release_all()
    distances=keyboard.getAllLevels()
    #print("Distances",distances)
    notes=[]
    for d in range(NUM_KEYS):
        #print("NUM_KEYS",NUM_KEYS,"index",d)
        if distances[d]<0.1: # pressed
            note=MIDI_NOTES[d]
            if type(note) is int:
                try:
                    x=notes.index(note)
                except ValueError:
                    notes.append(note)
            elif type(note) is list:
                for n in note:
                    try:
                        x=notes.index(n)
                    except ValueError:
                         notes.append(n)
            
    #if len(notes)>0:
    #    print("Pressing notes",notes)
    synth.press(notes)


# let's rock on

setMixerVoices()

try:
    print("mem_free",gc.mem_free())
    
    # Play voices updating volume levels
    while True:
        playKeys()
        time.sleep(.2) # cannot be faster
        
except Exception as e:
    print ("Player Exception",e)
    traceback.print_exception(e)
