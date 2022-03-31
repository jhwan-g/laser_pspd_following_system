from matplotlib.backend_bases import FigureManagerBase
from mcculw import ul
from mcculw.enums import ULRange
from mcculw.ul import ULError
from time import sleep
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
import matplotlib.pyplot as plt
import tkinter as tk
import numpy as np
import time

class DAQBoard:
    def __init__(self, board_num = 0):
        self.board_num = board_num
        self.ul_range = ULRange.BIP5VOLTS
    
    def read_analog(self, channel : int) -> tuple:
        try:
            #Get a value from the device
            value = ul.a_in(self.board_num, channel, self.ul_range)
            # Conver the raw value to engineering units
            eng_units_value = ul.to_eng_units(self.board_num, self.ul_range, value)
            return value, eng_units_value
        except ULError as e:
            # Display the error
            print("read_analog error : A UL error occurred. Code: " + str(e.errorcode)
                + " Message: " + e.message)

    def write_analog(self, channel : int, value : int):
        #print(ul.to_eng_units(self.board_num, self.ul_range, value))
        try:
            ul.a_out(self.board_num, channel, self.ul_range, value)
        except Exception as e:
            print('write_analog error : ' + e)

board = DAQBoard(0)

def read_and_plot():
    window = tk.Tk()

    a_in0 = collections.deque(np.zeros(1000))

    def analog_plotter(i):
        for i in range(1000):
            a_in0.popleft()
            a_in0.append(board.read_analog(1)[1])

        ax0.cla()   
        #ax0.set_ylim(-5, 5)
        ax0.plot(a_in0)

    fig0 = plt.figure()
    ax0 = plt.subplot()
    line1 = FigureCanvasTkAgg(fig0, window)
    line1.get_tk_widget().pack()

    anim = FuncAnimation(fig0, analog_plotter, interval = 20)
    window.mainloop()

VOLT0 = 2048

def degree_to_rad(x):
    PI = 3.141592653589793238
    return x * PI / 180

def sin_gen():
    x = 0
    while True:
        x += 1
        yield np.sin(degree_to_rad(x))

def write_analog(f):
    for i in f():
        board.write_analog(0, int((i + 1) * 1000 + VOLT0))
        time.sleep(0.0001)

write_analog(sin_gen)
