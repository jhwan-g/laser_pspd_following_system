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
    def __init__(self, board_num : int, ul_range):
        self.board_num = board_num
        self.ul_range = ul_range
    
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
        print(ul.to_eng_units(self.board_num, self.ul_range, value))
        try:
            ul.a_out(self.board_num, channel, self.ul_range, value)
        except Exception as e:
            print('write_analog error : ' + e)
    
    def read_multi_analog(self, channel : int, data_num : int) -> tuple:
        return tuple(self.read_analog(channel) for _ in range(data_num))

class DAQData:
    def __init__(self, store_data_num : int):
        self.a_in = [collections.deque(np.zeros(store_data_num)) for i in range(5)]

    def add_data(self, channel_num, data):
        self.a_in[channel_num].popleft()
        self.a_in[channel_num].append(data)

    def add_multiple_data(self, channel_num, datas):
        for i in datas:
            self.a_in[channel_num].popleft()
            self.a_in[channel_num].append(i)

    def get_data(self, channel_num):
        return self.a_in[channel_num]

class LineGraphPlotter:
    def __init__(self, parent):
        self.parent = parent
        self.fig = plt.figure()
        self.ax = plt.subplot()
        self.line = FigureCanvasTkAgg(self.fig, parent)
        self.line.get_tk_widget().pack()

    def plot_data(self, data):
        self.ax.cla()
        self.ax.plot(data)

VOLT0 = 2048
PI = 3.141592653589793238

class System:
    def __init__(self, parent, board_num : int):
        self.parent = parent
        self.board = DAQBoard(board_num, ULRange.BIP5VOLTS)
        self.started = False

        self.start_button = tk.Button(self.parent, text = 'start', command = self.start_clicked)
        self.start_button.pack()
        self.end_button = tk.Button(self.parent, text = 'end', command = self.end_clicked)
        self.end_button.pack()

        self.data = DAQData(1000)
        self.voltage_graph = LineGraphPlotter(tk.Toplevel(self.parent))
        self.main_loop()

    def start_clicked(self): self.started = True
    def end_clicked(self): self.started = False

    def main_loop(self):
        if self.started:
            self.data.add_data(0, self.board.read_analog(0))
        self.voltage_graph.plot_data(self.data.get_data(0))
        self.parent.after(1, self.main_loop)


# def read_and_plot():
#     window = tk.Tk()

#     a_in0 = collections.deque(np.zeros(1000))

#     def analog_plotter(i):
#         for i in range(1000):
#             a_in0.popleft()
#             a_in0.append(board.read_analog(1)[1])

#         ax0.cla()   
#         #ax0.set_ylim(-5, 5)
#         ax0.plot(a_in0)

#     fig0 = plt.figure()
#     ax0 = plt.subplot()
#     line1 = FigureCanvasTkAgg(fig0, window)
#     line1.get_tk_widget().pack()

#     anim = FuncAnimation(fig0, analog_plotter, interval = 20)
#     window.mainloop()

# 

# def degree_to_rad(x):
#     return x * PI / 180

# def sin_gen():
#     x = 0
#     while True:
#         x += 1
#         yield np.sin(degree_to_rad(x))

# def write_analog(f):
#     for i in f():
#         board.write_analog(0, int((i + 1) * 1000 + VOLT0))
#         time.sleep(0.0001)

# write_analog(sin_gen)

if __name__ == '__main__':
    window = tk.Tk()
    System(window, 0)
    window.mainloop()