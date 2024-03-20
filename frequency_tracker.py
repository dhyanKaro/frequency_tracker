import matplotlib
matplotlib.use("TkAgg")
matplotlib.rcParams['axes.linewidth'] = 1
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
from matplotlib.ticker import FuncFormatter
import matplotlib.style as mplstyle

mplstyle.use('fast')

from JMA import JMA

# Define color palette and theme constants (Darcula theme)
background_color = '#282a36'
text_color = '#f8f8f2'
grid_color = '#44475a'
line_color = '#1C5489'
markerfacecolor = '#ff79c6'
orange = '#FFB86C'
cyan = '#8BE9FD'

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
# max frequency limit
max_frequency = 5
# min frequency limit
min_frequency = 0.025
# Moving average
ma: JMA = None
ma_length = 8

start_btn_text = "Start (Space / Enter)"


# Re-computes frequencies and updates chart axes with latest data
def update_plot(new_point=True):
    """Update the plot with the latest data."""
    global timestamps, frequencies, ma
    # Check if we have at least two data points to calculate frequency
    if len(timestamps) < 2: return

    # Translate and align all timestamps starting from 0
    time_intervals = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
    frequencies = [1 / delta for delta in time_intervals]
    # Filter out frequencies lower than min_frequency and higher than max_frequency
    frequencies = [max(min(f, max_frequency), min_frequency) for f in frequencies]

    # Plot frequency data
    ts = [t - timestamps[0] for t in timestamps[1:]]  # Get it in terms of just seconds elapsed
    line1.set_data(ts, frequencies)

    # Calculate and plot moving average (JMA)
    if new_point:  # Only add to the moving-average values if this is a normal update (not undo)
        if ma is None:
            ma = JMA(frequencies[0], _length=ma_length, _phase=0)  # Use the updated ma_length
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

    ax1.legend()

    # Plot bar chart of time intervals on second subplot
    global bar1
    bar1.remove()
    bar1 = ax2.bar(ts, time_intervals, color=line_color)
    ax2.set_ylabel('Time Delta (seconds)')
    ax2.set_xlabel('Time (seconds)')

    # Rescale
    ax1.set_xlim(0, max(ts) * 1.05)
    ax1.set_ylim(min(frequencies) * 0.95, max(frequencies) * 1.05)

    # todo: get the tick labels and locators less messed up... matplotlib...
    # Tick labels format
    ax1.yaxis.set_major_formatter(formatter)
    ax1.yaxis.set_minor_formatter(formatter)
    sec_ax.yaxis.set_major_formatter(formatter)
    sec_ax.yaxis.set_minor_formatter(formatter)

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
    timestamps.append(time())  # Record the time when the button is pressed
    update_plot()


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

    ax1.set_xlim(left=0)

    ax2.relim()
    ax2.autoscale_view()

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
        root.after(1, update_plot(new_point=False))
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

def open_settings_dialog():
    def save_settings(ma_length_entry_value, max_freq_entry_value, min_freq_entry_value):
        global ma_length, max_frequency, min_frequency
        try:
            ma_length = int(ma_length_entry_value)
            max_freq_entry_value = float(max_freq_entry_value)
            min_freq_entry_value = float(min_freq_entry_value)
            # Update the JMA instance
            if ma is not None:
                ma._length = ma_length
            # Update the global variable for max frequency
            max_frequency = max_freq_entry_value
            min_frequency = min_freq_entry_value
            settings_window.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values.")

    global ma_length, max_frequency, min_frequency

    settings_window = customtkinter.CTkToplevel(root)
    settings_window.title("Settings")

    # MA Length
    ma_length_label = customtkinter.CTkLabel(settings_window, text="MA Length:")
    ma_length_label.grid(row=0, column=0, padx=10, pady=10)
    ma_length_entry = customtkinter.CTkEntry(settings_window)
    ma_length_entry.grid(row=0, column=1, padx=10, pady=10)
    ma_length_entry.insert(0, str(ma_length))  # Default/current value

    # Max Frequency
    max_freq_label = customtkinter.CTkLabel(settings_window, text="Max Frequency (Hz):")
    max_freq_label.grid(row=1, column=0, padx=10, pady=10)
    max_freq_entry = customtkinter.CTkEntry(settings_window)
    max_freq_entry.grid(row=1, column=1, padx=10, pady=10)
    max_freq_entry.insert(0, max_frequency)

    # Min Frequency
    min_freq_label = customtkinter.CTkLabel(settings_window, text="Min Frequency (Hz):")
    min_freq_label.grid(row=2, column=0, padx=10, pady=10)
    min_freq_entry = customtkinter.CTkEntry(settings_window)
    min_freq_entry.grid(row=2, column=1, padx=10, pady=10)
    min_freq_entry.insert(0, str(min_frequency))  # Default/current value

    # Save Button
    save_settings_btn = customtkinter.CTkButton(settings_window, text="Save",
        command=lambda: save_settings(ma_length_entry.get(), max_freq_entry.get(), min_freq_entry.get()))
    save_settings_btn.grid(row=3, column=0, columnspan=2, pady=10)

    settings_window.grab_set()  # Modal window


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

ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1], sharex=ax1)

ax1.set_ylabel('Frequency (Hz)')
ax1.set_xlim(left=0)
ax1.grid(True)
ax2.grid(True)
plt.setp(ax1.get_xticklabels(), visible=False)
ax1.set_yscale('log')
# Layout
fig.tight_layout(rect=[0.02, 0, 0.965, 1])
fig.subplots_adjust(hspace=0)

# Create line objects
line1, = ax1.plot([], [], marker='o', linestyle='-', linewidth=0.5, color='white', markerfacecolor='white',
                  label='ƒ (Hz)')
line2, = ax1.plot([], [], color='r', label="MA")
line3 = ax1.axhline(y=0, color='g', linestyle='--', label='Avg')
line3.set_alpha(0)
bar1 = ax2.bar([], [])

# Cursor for the annotations
mplcursors.cursor(ax1, hover=2)  # todo: custom annotation text
mplcursors.cursor(ax2, hover=2)


# Secondary y-axis
def one_over(x):
    """Vectorized 1/x, treating x==0 manually"""
    x = np.array(x, float)
    near_zero = np.isclose(x, 0)
    x[near_zero] = np.inf
    x[~near_zero] = 1 / x[~near_zero]
    return x


inverse = one_over  # the function "1/x" is its own inverse
sec_ax = ax1.secondary_yaxis('right', functions=(one_over, inverse))
sec_ax.set_ylabel('Period (s)')
sec_ax.set_yticks(one_over(ax1.get_yticks()))

# Ticks and labels
formatter = FuncFormatter(lambda x, _: '' if x <= 0 else f'{round(x) if abs(x - round(x)) < 1e-10 else x:.10g}')
ax1.yaxis.set_major_formatter(formatter)
sec_ax.yaxis.set_major_formatter(formatter)

# Frequency bands
try:
    from freq_bands import get_freq_bands
    for band in get_freq_bands(fd_range=(-7, 2)):
        ax1.axhspan(band['lower_limit_1'], band['upper_limit_1'], facecolor=orange, alpha=0.20)
except: ...

# GUI Setup
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

# Settings button
settings_button = customtkinter.CTkButton(button_frame, text="⚙️", width=3, command=open_settings_dialog)
settings_button.grid(row=0, column=3, sticky='nsew', padx=10)

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
