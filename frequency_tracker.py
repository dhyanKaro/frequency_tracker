import matplotlib

matplotlib.use("TkAgg")
import os
from datetime import datetime
from tkinter import ttk, messagebox
from PIL import ImageGrab
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.gridspec import GridSpec
from time import time
import numpy as np
import mplcursors
import customtkinter
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter

import matplotlib.style as mplstyle
mplstyle.use('fast')

from JMA import JMA

# Define color palette and theme constants (Darcula theme)
background_color = '#282a36'
text_color = '#f8f8f2'
grid_color = '#44475a'
line_color = '#1C5489'
markerfacecolor = '#ff79c6'

# Update the default parameters
plt.rcParams.update({
    'figure.facecolor': background_color,
    'axes.facecolor': background_color,
    'text.color': text_color,
    'axes.labelcolor': text_color,
    'xtick.color': text_color,
    'ytick.color': text_color,
    'axes.edgecolor': line_color,
    'grid.color': grid_color,
    'lines.markerfacecolor': markerfacecolor,
})
customtkinter.set_default_color_theme("dark-blue")

# Stores time stamp for each tap
timestamps = []
# Computed tap frequencies
frequencies = []
# Moving average
ma: JMA = None

start_btn_text = "Start (Space / Enter)"

# Re-computes frequencies and updates chart axes with latest data
def update_plot():
    """Update the plot with the latest data."""
    global timestamps, frequencies, ma
    # Check if we have at least two data points to calculate frequency
    if len(timestamps) < 2: return

    # Translate and align all timestamps starting from 0
    time_intervals = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
    frequencies = [1 / delta for delta in time_intervals]
    # Filter high values
    #   I think 10 times a second is the fastest anyone can tap
    #   and anything higher is usually a glitch from the matplotlib ui update lag
    frequencies = [min(f, 10) for f in frequencies]

    # Plot frequency data
    ts = [t - timestamps[0] for t in timestamps[1:]]  # Get it in terms of just seconds elapsed
    line1.set_data(ts, frequencies)

    # Calculate and plot moving average (JMA)
    if ma is None:
        ma = JMA(frequencies[0], _length=8, _phase=0)
    else:
        ma.update(frequencies[-1])
    ma_get_series = ma.get_series()
    line2.set_data(ts, ma_get_series)
    line2.set_label(f"MA:  {(float(ma_get_series[-1])):.3f}")

    # Plot average as a horizontal line
    mean = np.mean(frequencies)
    line3.set_ydata(mean)
    line3.set_label(f'Avg: {mean:.3f}')
    line3.set_alpha(1)

    ax.legend()
    ax.set_ylabel('Frequency (Hz)')
    ax.grid(True)

    # Auto-scale the plot (y-axis)
    ax.relim()
    ax.autoscale_view()

    # Update the secondary y-axis
    primary_ticks = ax.get_yticks()
    # Calculate the 1/f values for the y-tick locations
    secondary_ticks = one_over(primary_ticks)
    # Set the y-tick locations on the secondary y-axis
    secax.set_yticks(secondary_ticks)
    secax.yaxis.set_major_formatter(StrMethodFormatter('{x:.2g}'))

    # Plot bar chart of time intervals on second subplot
    global bar1
    bar1.remove()
    bar1 = ax2.bar(ts, time_intervals, color=line_color)
    ax2.set_ylabel('Time Delta (seconds)')
    ax2.set_xlabel('Time (seconds)')

    # Add gridlines to second subplot
    ax2.grid(True)

    ax.relim()
    ax.autoscale_view()
    ax.set_xlim(0, max(ts) * 1.05)
    # Update the canvas
    canvas.draw_idle()


def flash_button(btn):
    # Flash the button white
    btn.configure(fg_color="white")
    btn.after(100, lambda: btn.configure(fg_color=original_fg_color))


# Function to handle button click
def button_click(event=None):
    flash_button(start_button)

    start_button.configure(text="Click (or Space / Enter)")
    # Record the time when the button is pressed
    timestamps.append(time())

    # Update the plot with the new data
    root.after(1, update_plot)


# Function to handle reset button click
def reset_chart(event=None):
    flash_button(reset_button)

    global timestamps, frequencies, bar1, ma
    # Clear the data structures
    timestamps = []
    frequencies = []
    ma = None

    # Clear the current plot
    # Remove data from the lines and bars
    line1.set_data([], [])
    line2.set_data([], [])
    line3.set_alpha(0)
    bar1.remove()
    bar1 = ax2.bar([], [])

    # Set the x-axis limits
    ax.set_xlim(left=0)

    # Update the canvas to clear the chart
    root.after(1, canvas.draw_idle())

    start_button.configure(text=start_btn_text)


def undo(event=None):
    try:
        timestamps.pop()
        ma.pop()
        # todo: button flash not displaying right... sometimes...
        flash_button(start_button)
        flash_button(reset_button)
    except IndexError:
        print('List is empty')


def save_plot(event=None):
    if not timestamps:
        messagebox.showerror('Save Error', 'There\'s nothing to save')
        return

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    if not os.path.exists('frequency_saves'):
        os.mkdir('frequency_saves')

    save_dir = os.path.join('frequency_saves', timestamp)
    os.mkdir(save_dir)

    # Take screenshot of full plot
    x = root.winfo_rootx() + plot_frame.winfo_x()
    y = root.winfo_rooty() + plot_frame.winfo_y()
    x1 = x + plot_frame.winfo_width()
    y1 = y + plot_frame.winfo_height()
    ImageGrab.grab().crop((x, y, x1, y1)).save(os.path.join(save_dir, 'plot.png'))

    # Save data to text file
    with open(os.path.join(save_dir, 'data.txt'), 'w') as f:
        f.write(f'timestamps={repr(timestamps)}')
        f.write('\n\n')
        f.write(f'frequencies={repr(frequencies)}')
        f.write('\n\n')
        if ma:
            f.write(f'moving-average={repr(list(ma.get_series()))}')
            f.write('\n\n')
        f.write(f'Average={str(np.mean(frequencies))}')

    messagebox.showinfo("Plot Saved", f"The plot has been saved to: {os.path.abspath(save_dir)}")


# Create the main window
root = customtkinter.CTk()
root.title("Frequency Tracker")

# Create a Frame for the plot
plot_frame = ttk.Frame(root)
plot_frame.grid(row=0, column=0, sticky='nsew')
root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)

# Create a Figure for the plot with two subplots sharing the x-axis
width = 10
fig = Figure(figsize=(width, width / 1.618))
gs = GridSpec(nrows=2, ncols=1, figure=fig, height_ratios=[1.618, 1])

ax = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1], sharex=ax)

ax.set_title("Frequency Tracker")
ax.set_xlim(left=0)
ax.grid(True)
fig.tight_layout(rect=[0.02, 0, 0.965, 1])
fig.subplots_adjust(hspace=0)

# Create line objects
line1, = ax.plot([], [], marker='o', linestyle='-', linewidth=0.5, color='white', markerfacecolor='white',
                 label='ƒ (Hz)')
line2, = ax.plot([], [], color='r', label="MA")
line3 = ax.axhline(y=0, color='g', linestyle='--', label='Avg')
line3.set_alpha(0)
bar1 = ax2.bar([], [])

# Cursor for the annotations
mplcursors.cursor(ax, hover=2)
mplcursors.cursor(ax2, hover=2)


# Secondary axis
def one_over(x):
    """Vectorized 1/x, treating x==0 manually"""
    x = np.array(x, float)
    near_zero = np.isclose(x, 0)
    x[near_zero] = np.inf
    x[~near_zero] = 1 / x[~near_zero]
    return x


inverse = one_over  # the function "1/x" is its own inverse
secax = ax.secondary_yaxis('right', functions=(one_over, inverse))
secax.set_ylabel('Period (s)')

# Create a canvas to display the plot
canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.get_tk_widget().pack(side="top", fill='both', expand=True)
canvas.draw()

# Create a new frame to hold the buttons
button_frame = customtkinter.CTkFrame(root)
button_frame.grid(row=3, column=0, sticky='nsew', pady=14)

# Tap button
start_button = customtkinter.CTkButton(button_frame, text=start_btn_text, command=button_click, height=40, )
original_fg_color = start_button.cget("fg_color")
start_button.grid(row=0, column=1, sticky='nsew', padx=10)
start_button.focus_set()

# Reset button
reset_button = customtkinter.CTkButton(button_frame, text="Reset", command=reset_chart)
reset_button.grid(row=0, column=0, sticky='nsew', padx=10)

# save button
save_button = customtkinter.CTkButton(button_frame, text="💾", width=3, command=save_plot)  # What's a floppy?
save_button.grid(row=0, column=2, sticky='nsew', padx=10)

# Update column weights for button frame
button_frame.columnconfigure(2, weight=82)

# Configure the column weights of the button frame to make the buttons fill the area
button_frame.columnconfigure(0, weight=618)
button_frame.columnconfigure(1, weight=1618)

# Key binds
root.bind('<Return>', button_click)
root.bind('<space>', lambda e: button_click() if not start_button.focus_get() == start_button else None)
root.bind('<BackSpace>', reset_chart)
root.bind('<Delete>', reset_chart)
root.bind('<Button-2>', reset_chart)
root.bind('<Button-3>', undo)
root.bind('<Escape>', lambda e: messagebox.showinfo("Message", "There is no escape."))

# Start the GUI main loop
root.mainloop()
