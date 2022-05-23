from colorsys import yiq_to_rgb
from mcculw import ul
from mcculw.enums import ULRange
from mcculw.ul import ULError

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import collections
import matplotlib.pyplot as plt
import tkinter as tk
import numpy as np
import threading
import time

VOLT0 = 2048
PI = 3.141592653589793238

class DAQBoard:
    def __init__(self, board_num : int, ul_range):
        self.board_num = board_num
        self.ul_range = ul_range
    
    def read_analog(self, channel : int) -> tuple:
        '''
        returns (raw value, eng_units value)
        '''
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
            #write the value to the daq board
            ul.a_out(self.board_num, channel, self.ul_range, value)
        except Exception as e:
            print(e)
    
    def read_multi_analog(self, channel : int, data_num : int) -> tuple:
        return tuple(self.read_analog(channel) for _ in range(data_num))

class PID(object):
    """Implementation of a PID controller.
    This implementation is geared towards discrete time systems,
    where PID is often called PSD (proportional-sum-difference).
    Usage is fairly straight forward. Set the coefficients of
    the three terms to values of your choice and call PID.update
    with constant timesteps.
    """
    
    def __init__(self, integral_len, kp=-100, ki=0, kd=0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.first = True
        self.integral_len = integral_len
        self.errors = collections.deque(np.zeros(self.integral_len))

    def update(self, error):
        """Update the PID controller.
       
        Computes the new control value as                 
            u(t) = kp*err(t) + kd*d/dt(err(t)) + ki*I(e)
        
        where I(e) is the integral of the error up to the current timepoint.
        Args:
            error: Error between set point and measured value
            dt: Time step delta
        Returns:
            Returns the control value u(t)
        """

        if self.first:
            self.lastError = error
            self.first = False

        derr = (error - self.lastError)
        self.errors.append(error)
        self.errors.popleft()

        self.sumError = sum(self.errors) / self.integral_len
        self.lastError = error

        u = self.kp * error + self.kd * derr + self.ki * self.sumError

        return u

class LineGraphPlotter:
    def __init__(self, parent, num):
        self.parent = parent
        self.fig, self.ax = plt.subplots(num, 1)
        self.line = FigureCanvasTkAgg(self.fig, parent)
        self.line._tkcanvas.pack()

    def plot(self, data):
        self.fig.clear()
        plt.plot(data)
        plt.ylim([-0.5,0.5])
        plt.draw()

def volt_to_raw(x : float) -> int:
    return int(VOLT0 + (x * 410) // 3) 


def scan_volt_gen(istep : float, jstep : float, vrange : int):
    i, j = -vrange, -vrange
    while True:
        j = -vrange
        if i >= vrange: i = -vrange
        while True:
            j += jstep
            if j>vrange: break
            yield i, j
        i += istep

def calc_pos(inp1 : float, inp2 : float, inp3 : float, inp4 : float)->tuple:
    # inp1 inp2
    # inp3 inp4
    return inp4 + inp2 - inp3 - inp1, inp1 + inp2 - inp3 - inp4

class System:
    def __init__(self, parent : tk.Tk, board_num : int):
        # board setting
        self.parent = parent
        self.board = DAQBoard(board_num, ULRange.BIP15VOLTS)
        self.started = tk.BooleanVar(value = False)
        self.pid_var = {'x' : {'save_len' : tk.IntVar(value = 10), 'p' : tk.DoubleVar(value = 0.8), 'i' : tk.DoubleVar(value = 0), 'd' : tk.DoubleVar(value = 0.4)}, 
                        'y' : {'save_len' : tk.IntVar(value = 10), 'p' : tk.DoubleVar(value = -0.8), 'i' : tk.DoubleVar(value = 0), 'd' : tk.DoubleVar(value = -0.4)}}
        self.pos = {'x' : tk.DoubleVar(value = 0), 'y' : tk.DoubleVar(value = 0)}
        # self.before_time = time.time()
        
        self.x_volt = 7.5
        self.y_volt = 7.5

        # pid controll
        self.pidx = PID(10, 1, 0, 0)
        self.pidy = PID(10, -1, 0, 0)

        # ** gui **
        self.stat_label = tk.Label(self.parent, textvariable=self.started)
        self.stat_label.pack(fill = tk.X)
        self.start_button = tk.Button(self.parent, text = 'start', command = self.start_clicked)
        self.start_button.pack(fill = tk.X)
        self.end_button = tk.Button(self.parent, text = 'end', command = self.end_clicked)
        self.end_button.pack(fill = tk.X)

        # PID variable controll gui 
        # len -> p -> i -> d 순임
        self.x_label = tk.Label(self.parent, text = 'x')
        self.x_label.pack(fill = tk.X)
        self.x_len = tk.Entry(textvariable=self.pid_var['x']['save_len']); self.x_len.pack()
        self.x_p = tk.Entry(textvariable=self.pid_var['x']['p']); self.x_p.pack()
        self.x_i = tk.Entry(textvariable=self.pid_var['x']['i']); self.x_i.pack()
        self.x_d = tk.Entry(textvariable=self.pid_var['x']['d']); self.x_d.pack()
        self.y_label = tk.Label(self.parent, text = 'y')
        self.y_label.pack(fill = tk.X)
        self.y_len = tk.Entry(textvariable=self.pid_var['y']['save_len']); self.y_len.pack()
        self.y_p = tk.Entry(textvariable=self.pid_var['y']['p']); self.y_p.pack()
        self.y_i = tk.Entry(textvariable=self.pid_var['y']['i']); self.y_i.pack()
        self.y_d = tk.Entry(textvariable=self.pid_var['y']['d']); self.y_d.pack()
        self.apply_button = tk.Button(self.parent, text = 'apply', command = self.pid_var_apply); self.apply_button.pack()

        # pos_print
        self.x_pos_label = tk.Label(self.parent, textvariable = self.pos['x'])
        self.x_pos_label.pack()
        self.y_pos_label = tk.Label(self.parent, textvariable = self.pos['y'])
        self.y_pos_label.pack()

        # x_pos, y_pos graph
        self.toplevel = tk.Toplevel(self.parent)
        self.data = collections.deque(np.zeros(1000))
        self.y_graph = LineGraphPlotter(self.toplevel, 1)
        self.x_graph = LineGraphPlotter(self.toplevel, 2)

        self.gui_loop()
        
        # add thread
        newthread = threading.Thread(target = self.data_loop)
        newthread.start()

    def start_clicked(self): self.started.set(True)
    def end_clicked(self): self.started.set(False)
    def pid_var_apply(self):
        var_temp = self.pid_var
        self.pidx = PID(var_temp['x']['save_len'].get(), var_temp['x']['p'].get(), var_temp['x']['i'].get(),var_temp['x']['d'].get())
        self.pidy = PID(var_temp['y']['save_len'].get(), var_temp['y']['p'].get(), var_temp['y']['i'].get(),var_temp['y']['d'].get())

    def data_loop(self):
        i = 0
        scan_pos = scan_volt_gen(0.5, 0.5, 14)
        

        while True:
            self.ch1, self.ch2, self.ch3, self.ch4 = self.board.read_analog(1)[1], self.board.read_analog(2)[1], self.board.read_analog(3)[1], self.board.read_analog(4)[1]
            self.x, self.y = calc_pos(self.ch1, self.ch2, self.ch3, self.ch4)
            self.pidx.update(self.x)
            self.pidy.update(self.y)
            if self.started.get():      
                pos = next(scan_pos)
                # print('raw', pos, volt_to_raw(pos[0]), volt_to_raw(pos[1]))
                # self.board.write_analog(0, volt_to_raw(pos[0]))
                # self.board.write_analog(1, volt_to_raw(pos[1]))

                # t = time.time()

                self.x_volt += self.pidx.update(self.x)
                self.y_volt += self.pidy.update(self.y)

                if not -15<self.x_volt<15: self.x_volt = 7.5
                if not -15<self.y_volt<15: self.y_volt = 7.5

                print(volt_to_raw(self.x_volt), volt_to_raw(self.y_volt), self.x_volt, self.y_volt)

                self.board.write_analog(1, volt_to_raw(self.x_volt))
                self.board.write_analog(0, volt_to_raw(self.y_volt))
                # time.sleep(0.1)
                # #time.sleep(0.1)

    def gui_loop(self):
        self.x_graph.plot(self.pidx.errors)
        self.y_graph.plot(self.pidy.errors)
        try:
            self.pos['x'].set(self.x); self.pos['y'].set(self.y)
            #print(self.x, self.y, self.x_volt, self.y_volt)
            #print('a', self.ch1, self.ch2, self.ch3, self.ch4)
        except:
            pass
        self.parent.after(500, self.gui_loop)

    

if __name__ == '__main__':
    window = tk.Tk()
    System(window, 0)
    window.mainloop()