from mcculw import ul
from mcculw.enums import ULRange
from mcculw.ul import ULError
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
            return 0, 0

    def write_analog(self, channel : int, value : int):
        #print(ul.to_eng_units(self.board_num, self.ul_range, value))
        try:
            ul.a_out(self.board_num, channel, self.ul_range, value)
        except Exception as e:
            print('write_analog error : ' + e)
    
    def read_multi_analog(self, channel : int, data_num : int) -> tuple:
        return tuple(self.read_analog(channel) for _ in range(data_num))

class LineGraphPlotter:
    def __init__(self, parent):
        self.parent = parent
        self.fig, self.ax = plt.subplots(1, 1)
        self.line = FigureCanvasTkAgg(self.fig, parent)
        self.line._tkcanvas.pack()

    def plot(self, data):
        self.fig.clear()
        plt.plot(data)
        plt.draw()
  

VOLT0 = 2048
PI = 3.141592653589793238

import threading

class System:
    def __init__(self, parent : tk.Tk, board_num : int):
        self.parent = parent
        self.board = DAQBoard(board_num, ULRange.BIP5VOLTS)
        self.started = tk.BooleanVar(value = False)

        self.stat_label = tk.Label(self.parent, textvariable=self.started)
        self.stat_label.pack(fill = tk.X)
        self.start_button = tk.Button(self.parent, text = 'start', command = self.start_clicked)
        self.start_button.pack(fill = tk.X)
        self.end_button = tk.Button(self.parent, text = 'end', command = self.end_clicked)
        self.end_button.pack(fill = tk.X)

        self.data = collections.deque(np.zeros(1000))
        self.voltage_graph = LineGraphPlotter(tk.Toplevel(self.parent))
        self.gui_loop()
        
        newthread = threading.Thread(target = self.data_loop)
        newthread.start()

    def start_clicked(self): self.started.set(True)
    def end_clicked(self): self.started.set(False)

    def data_loop(self):
        while True:
            if self.started.get():        
                temp, volt = self.board.read_analog(0)
                self.data.append(volt)
                self.data.popleft()
                self.board.write_analog(0, temp)


    def gui_loop(self):
        self.voltage_graph.plot(self.data)
        self.parent.after(500, self.gui_loop)


if __name__ == '__main__':
    window = tk.Tk()
    System(window, 0)
    window.mainloop()