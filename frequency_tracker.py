import os
from datetime import datetime
from tkinter import ttk, messagebox
import pandas as pd
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
import matplotlib

matplotlib.use("TkAgg")

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
# Moving average values
ma = []

start_btn_text = "Start (Space / Enter)"


# Calculates Jurik Moving Average
# Returns the computed JMA as a Pandas Series
def jma(df, _src, _length=13, _phase=0):
    df['lower_band'] = df[_src]
    df['upper_band'] = df[_src]
    df['vola_sum'] = 0.0
    df['avg_vola'] = 0.0
    df['ma1'] = df[_src]
    df['det0'] = 0.0
    df['jma'] = df[_src]
    df['det1'] = 0.0

    avg_len = 65

    for i in range(1, len(df)):
        df.loc[i, 'del2'] = abs(df.loc[i, _src] - df.loc[i - 1, 'lower_band'])
        df.loc[i, 'del1'] = abs(df.loc[i, _src] - df.loc[i - 1, 'upper_band'])

        df.loc[i, 'vola'] = 0 if df.loc[i, 'del1'] == df.loc[i, 'del2'] else max(df.loc[i, 'del1'], df.loc[i, 'del2'])

        df.loc[i, 'vola_sum'] = df.loc[i - 1, 'vola_sum'] + 0.1 * (
                    df.loc[i, 'vola'] - df.loc[i - 10 if i >= 10 else 0, 'vola'])

        y = i + 1

        if y <= avg_len + 1:
            df.loc[i, 'avg_vola'] = df.loc[i - 1, 'avg_vola'] + 2.0 * (
                        df.loc[i, 'vola_sum'] - df.loc[i - 1, 'avg_vola']) / (avg_len + 1)
        else:
            df.loc[i, 'avg_vola'] = df.loc[i - avg_len:i, 'vola_sum'].mean()

        length = 0.5 * (_length - 1)
        len1 = max(np.log(np.sqrt(length)) / np.log(2) + 2, 0)
        pow1 = max(len1 - 2, 0.5)

        df.loc[i, 'r_vola'] = df.loc[i, 'vola'] / df.loc[i, 'avg_vola'] if df.loc[i, 'avg_vola'] > 0 else 0
        df.loc[i, 'r_vola'] = min(max(df.loc[i, 'r_vola'], 1), pow(len1, 1 / pow1))

        pow2 = pow(df.loc[i, 'r_vola'], pow1)
        len2 = np.sqrt(length) * len1
        bet = len2 / (len2 + 1)
        kv = pow(bet, np.sqrt(pow2))

        df.loc[i, 'lower_band'] = df.loc[i, _src] if df.loc[i, 'del2'] < 0 else df.loc[i, _src] - kv * df.loc[i, 'del2']
        df.loc[i, 'upper_band'] = df.loc[i, _src] if df.loc[i, 'del1'] < 0 else df.loc[i, _src] + kv * df.loc[i, 'del1']

        beta = 0.45 * (length - 1) / (0.45 * (length - 1) + 2)
        pr = 0.5 if _phase < -100 else 2.5 if _phase > 100 else _phase / 100 + 1.5
        alpha = pow(beta, pow2)

        df.loc[i, 'ma1'] = (1 - alpha) * df.loc[i, _src] + alpha * df.loc[i - 1, 'ma1']
        df.loc[i, 'det0'] = (df.loc[i, _src] - df.loc[i, 'ma1']) * (1 - beta) + beta * df.loc[i - 1, 'det0']
        ma2 = df.loc[i, 'ma1'] + pr * df.loc[i, 'det0']
        df.loc[i, 'det1'] = (ma2 - df.loc[i - 1, 'jma']) * pow((1 - alpha), 2) + pow(alpha, 2) * df.loc[i - 1, 'det1']
        df.loc[i, 'jma'] = df.loc[i - 1, 'jma'] + df.loc[i, 'det1']

    return df['jma']


# Re-computes frequencies and updates chart axes with latest data
def update_plot():
    """Update the plot with the latest data."""
    global timestamps, frequencies, ma
    # Check if we have at least two data points to calculate frequency
    if len(timestamps) >= 2:
        # Translate and align all timestamps starting from 0
        time_intervals = [timestamps[i] - timestamps[i - 1] for i in range(1, len(timestamps))]
        frequencies = [1 / delta for delta in time_intervals]
        # Filter high values
        # I think 10 times a second is the fastest anyone can tap
        # and anything higher is usually a glitch from the matplotlib ui update lag
        frequencies = [min(f, 10) for f in frequencies]

        # Clear the current plot
        ax.clear()
        ax2.clear()

        # Plot frequency data
        ts = [t - timestamps[0] for t in timestamps[1:]]  # Get it in terms of just seconds elapsed
        ax.plot(ts, frequencies, marker='o', linestyle='-', linewidth=0.5, color='white', markerfacecolor='white',
                label='ƒ (Hz)')

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
        # Get the y-tick locations from the primary y-axis
        primary_ticks = ax.get_yticks()
        # Calculate the 1/f values for the y-tick locations
        secondary_ticks = one_over(primary_ticks)
        # Set the y-tick locations on the secondary y-axis
        secax.set_yticks(secondary_ticks)
        secax.yaxis.set_major_formatter(StrMethodFormatter('{x:.2g}'))

        # Calculate and plot moving average (JMA)
        ma = jma(pd.DataFrame(frequencies, columns=['freq']), 'freq', _length=8, _phase=0)
        if not ma.empty:
            ax.plot(ts, ma, color='r', label=f"MA:  {(float(ma.iloc[-1])):.3f}")

        # Plot average as a horizontal line
        mean = np.mean(frequencies)
        ax.axhline(mean, color='g', linestyle='--', label=f'Avg: {mean:.3f}')

        ax.legend()
        ax.set_ylabel('Frequency (Hz)')
        ax.grid(True)

        # Auto-scale the plot (y-axis)
        ax.relim()
        ax.autoscale_view()

        # Plot bar chart of time intervals on second subplot
        ax2.bar(ts, time_intervals, )
        ax2.set_ylabel('Time Delta (seconds)')
        ax2.set_xlabel('Time (seconds)')

        # Add gridlines to second subplot
        ax2.grid(True)

        # Cursor for the annotations
        mplcursors.cursor(ax, hover=2)
        mplcursors.cursor(ax2, hover=2)

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

    global timestamps, frequencies
    # Clear the data structures
    timestamps = []
    frequencies = []

    # Clear the current plot
    ax.clear()
    ax2.clear()

    # Set the x-axis limits
    ax.set_xlim(left=0)

    # Update the canvas to clear the chart
    root.after(1, canvas.draw_idle())

    start_button.configure(text=start_btn_text)

def undo(event=None):
    try:
        timestamps.pop()
        # todo: not displaying right... sometimes...
        flash_button(start_button)
        flash_button(reset_button)
        root.after(1, update_plot)
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
        f.write(f'moving-average={repr(list(ma))}')
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
