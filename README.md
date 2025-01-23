# Pico-Audio-Keyboard

An fun experiment making a keyboard which uses VL53L0X TOF lidar sensors (I2C) as keys and the Waveshare Pico-Audio HAT (I2S).

Using the TOF sensor allows the volume of each note to be controlled based on the distance of my fingers above the sensor.

The CircuitPython audio mixer is used to run the notes on each key continuously and the control loop then modulates the volume of the relevant channel



![IMG_20250123_092952](https://github.com/user-attachments/assets/541f4991-4978-478a-a676-6d996c0d596c)

The keyboard uses a TCA9548 I2C MUX which can provide access to 8 VL53L0X sensors. Hence the test keyboard has only 8 keys arranged to match the finger tips, except thumbs, of my hands.  

# requirements

1 Waveshare Pico-Audio
2 Pico 2 (faster with more memory)
3 8 x VL53L0X sensors (other I2C TOF sensors should work)
4 1 x TCA9548 I2C MUX.
5 Circuitpython 
6 Libraries: adafruit_tca9548 and adafruit_vl53l0x

# circuit

See Schematic.jpg

Note that reduce supply noise VCC (3v3) is decoupled at the MUX with a 1uf ceramic/electrolytic cap. The VL53L0X devices are decaoupled using 0.1uf. The circuit may well run ok without them if the 3V3 from the pico is of good quality.


# Software

# VL53_Keyboard.py

This is the keyboard driver. The keys (VL53L0X sensors) are set into continuous scan mode. Since they are on separate I2C busses they are, effectively, working in parallel.

The driver updates the max/min values seen from the sensors on each pass. The key readings are then normalised into a 0..1.0 range.

A call to getAllLevels() returns a python list with the current, normalised, key levels.

It is up to the caller to determine the acceptable ranges.

# Player.py

This program creates the 8 notes which are assigned to each key. The notes are played continuously through a circuitpython audiomixer and the key values are used to modulate the amplitude of the notes as they are played.

# Possible Extensions

1 add harmonics to the generated sine waves
2 improve the isolation of the keys currently two keys can be 'pressed' with my fat fingers.
3 upto 7x TCA9584 can be daisy chained giving upto 7x8 notes.







