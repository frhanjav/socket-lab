import matplotlib.pyplot as plt

def nrzi_encode(data):
    time, signal = [], []
    t, last = 0, 0  # Starting with low level
    for bit in data:
        if bit == '1':
            last = 1 - last  # Invert signal on '1'
        time.append(t)
        signal.append(last)
        t += 1
    
    # Add final point to extend to full width
    time.append(t)
    signal.append(signal[-1])
    return time, signal

def manchester_ieee(data):
    time, signal = [], []
    t = 0
    for bit in data:
        if bit == '0':
            # For IEEE, '0' is represented by high-to-low transition
            signal.extend([1, 0])
        else:
            # For IEEE, '1' is represented by low-to-high transition
            signal.extend([0, 1])
        time.extend([t, t + 0.5])
        t += 1
    
    # Add final point to extend to full width
    time.append(t)
    signal.append(signal[-1])
    return time, signal

def manchester_thomas(data):
    time, signal = [], []
    t = 0
    for bit in data:
        if bit == '0':
            # For Thomas, '0' is represented by low-to-high transition
            signal.extend([0, 1])
        else:
            # For Thomas, '1' is represented by high-to-low transition
            signal.extend([1, 0])
        time.extend([t, t + 0.5])
        t += 1
    
    # Add final point to extend to full width
    time.append(t)
    signal.append(signal[-1])
    return time, signal

def diff_manchester_encode(data):
    time, signal = [], []
    t = 0
    last = 1  # Start with high
    
    for bit in data:
        if bit == '0':
            # For '0', invert from previous end level (transition)
            signal.extend([1-last, last])
            last = last  # End with same level we started with
        else:
            # For '1', continue with same level (no transition)
            signal.extend([last, 1-last])
            last = 1-last  # End with opposite level
        
        time.extend([t, t + 0.5])
        t += 1
    
    # Add final point to extend to full width
    time.append(t)
    signal.append(signal[-1])
    return time, signal

def plot_waveform(time, signal, bits, ax, title, color):
    ax.step(time, signal, where='post', linewidth=2, color=color)
    ax.set_ylim(-0.5, 1.5)
    ax.set_xlim(0, len(bits))
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['Low', 'High'])
    ax.set_title(title, fontsize=14)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Dotted lines at bit boundaries
    for i in range(1, len(bits)+1):  # +1 to include the final boundary
        ax.axvline(i, color='gray', linestyle=':', linewidth=1)
    
    # Add dotted lines at mid-bit points (lighter)
    for i in range(len(bits)):
        ax.axvline(i + 0.5, color='lightgray', linestyle=':', linewidth=0.5)
    
    # Remove x-axis ticks and show bits outside plot
    ax.set_xticks([])
    for i, bit in enumerate(bits):
        ax.text(i + 0.5, -0.3, bit, ha='center', va='center', fontsize=12)

def plot_encoding(data):
    fig, axs = plt.subplots(2, 2, figsize=(14, 8), sharex=True, sharey=True)
    encodings = [
        (manchester_ieee, "Manchester (IEEE 802.3)", 'tab:blue'),
        (manchester_thomas, "Manchester (G.E. Thomas)", 'tab:orange'),
        (diff_manchester_encode, "Differential Manchester", 'tab:green'),
        (nrzi_encode, "NRZI", 'tab:red'),
    ]
    axs = axs.flatten()
    for ax, (encoder, title, color) in zip(axs, encodings):
        time, signal = encoder(data)
        plot_waveform(time, signal, data, ax, title, color)
    
    plt.tight_layout()
    fig.suptitle("Digital Line Encodings", fontsize=16)
    plt.subplots_adjust(top=0.92)
    plt.show()

if __name__ == "__main__":
    binary_input = input("Enter a binary string (e.g., 1011001): ").strip()
    if not all(bit in '01' for bit in binary_input):
        print("Invalid binary input.")
    else:
        plot_encoding(binary_input)