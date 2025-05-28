import matplotlib.pyplot as plt

def plot_signal(signals_list):
    # Each signal in signals_list should be a dict with {label, data, timescale}
    plt.figure(figsize=(12, 6))
    
    # Track maximum x value for proper axis scaling
    max_x = 0
    
    # Track vertical position for each signal
    vertical_position = 0
    
    for i, signal in enumerate(signals_list):
        label = signal['label']
        data = signal['data']
        time_scale = signal['timescale']
        
        # Create x values for plotting
        if isinstance(data[0], str):  # Original binary data
            x = range(len(data) * time_scale)
            # Create y values for original data
            y = []
            for bit in data:
                y.extend([int(bit)] * time_scale)
        else:  # Encoded data
            x = range(len(data))
            y = data
        
        # Update max_x
        max_x = max(max_x, len(x))
        
        # Plot the signal
        plt.step(x, [y_val + vertical_position for y_val in y], 
                label=label, where='post', linestyle='-' if i > 0 else '--')
        
        # Move down for the next signal
        vertical_position -= 2
    
    # Add labels and legend
    plt.xlabel("Time")
    plt.ylabel("Signal")
    plt.title("Line Encoding Comparison")
    plt.legend(loc="upper right")

    # Add grid lines every 2 units
    plt.xticks(range(0, max_x + 1, 2))  # Changed from 4 to 2
    plt.grid(True, which='both', axis='x', linestyle='--', linewidth=0.5)
    
    # Adjust y-axis limits to fit all signals
    plt.ylim(vertical_position + 0.5, 1.5)
    
    # Display the plot
    plt.show()

def manchester(data: str):
    # 0 -> high to low
    # 1 -> low to high
    out_arr = []
    for bit in list(data):
        if bit == "0":
            out_arr.append(1)
            out_arr.append(0)
        elif bit == "1":
            out_arr.append(0)
            out_arr.append(1)
    return out_arr, 2

def diff_manchester(data: str):
    # 0 -> pulse (starting from high) to same (high -> pulse
    #  -> ret high)
    # 1 -> pulse to opposite polarity (high -> pulse -> ret low)
    # Transition at start if 0
    # no transition at start if 1
    out_arr = []
    current_state = 1
    
    for bit in data:
        if bit == '0':
            current_state = 1 - current_state  # Invert at the beginning of the bit
            out_arr.append(current_state)  # Transition at the beginning
            current_state = 1 - current_state  # Invert at the beginning of the bit
            out_arr.append(current_state)  # No mid-bit transition

        elif bit == '1':
            out_arr.append(current_state)  # No transition at the beginning
            current_state = 1 - current_state  # Transition at the middle
            out_arr.append(current_state)  # Mid-bit transition
    
    return out_arr, 2

def NRZ_I(data: str):
    # start foorm high
    # if 1 -> switch state
    # if 0 -> state remains same
    out_arr = []
    current_state = 1
    
    for bit in data:
        if bit == '0':
            out_arr.extend([current_state, current_state])
        elif bit == '1':
            current_state = 1 - current_state
            out_arr.extend([current_state, current_state])

    return out_arr, 2

def main():
    # Get user input for bit stream
    data = input("Enter bit stream (only 0s and 1s): ")
    
    # Validate input to ensure it contains only 0s and 1s
    if not all(bit in '01' for bit in data):
        print("Error: Input should contain only 0s and 1s")
        return
    
    # Generate encoded data
    encoded_data_manchester, _ = manchester(data)
    encoded_data_diff_manchester, _ = diff_manchester(data)
    encoded_data_nrz_i, _ = NRZ_I(data)

    # Plot both original and encoded data
    plot_signal([{"label": "Original", "data": data, "timescale": 2},
                 {"label": "Manchester", "data": encoded_data_manchester, "timescale": 1}, 
                 {"label": "Differential Manchester", "data": encoded_data_diff_manchester, "timescale": 1}, 
                 {"label": "NRZ-I", "data": encoded_data_nrz_i, "timescale": 1}])

if __name__ == "__main__":
    main()
