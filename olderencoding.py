import matplotlib.pyplot as plt
def pad_signal(time, signal):
    time.append(time[-1])
    signal.append(signal[-1])
    return time, signal
def nrzi_encode(data):
    time, signal = [], []
    t, last = 0, 1
    for bit in data:
        if bit == '1':
            last = 1 - last
        signal += [last, last]
        time += [t, t + 1]
        t += 1
    return pad_signal(time, signal)
def manchester_ieee(data):
    time, signal = [], []
    t = 0
    for bit in data:
        if bit == '0':
            signal += [1, 0]  # high to low for 0
        else:
            signal += [0, 1]  # low to high for 1
        time += [t, t + 0.5, t + 1]
        signal.insert(-1, signal[-2])  # hold before mid
        t += 1
    return pad_signal(time, signal)
def manchester_thomas(data):
    time, signal = [], []
    t = 0
    for bit in data:
        if bit == '1':
            signal += [1, 0]  # high to low for 1
        else:
            signal += [0, 1]  # low to high for 0
        time += [t, t + 0.5, t + 1]
        signal.insert(-1, signal[-2])  # hold before mid
        t += 1
    return pad_signal(time, signal)
def diff_manchester_encode(data, initial=1):
    time, signal = [], []
    t = 0
    last = initial
    for bit in data:
        if bit == '0':
            last = 1 - last  # transition at start for 0
            signal += [last]
            time += [t]
        else:
            signal += [last]  # no transition at start for 1
            time += [t]
        last = 1 - last  # always transition at middle
        signal += [last]
        time += [t + 0.5]
        signal += [last]
        time += [t + 1]
        t += 1
    return pad_signal(time, signal)
def plot_waveform(time, signal, bits, ax, title, color):
    ax.step(time, signal, where='post', linewidth=2, color=color)
    ax.set_ylim(-0.5, 1.5)
    ax.set_xlim(0, len(bits))
    ax.set_yticks([0, 1])
    ax.set_yticklabels(['Low', 'High'])
    ax.set_title(title, fontsize=14)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    # Dotted lines at bit boundaries
    for i in range(1, len(bits)):
        ax.axvline(i, color='gray', linestyle=':', linewidth=1)
    # Remove x-axis ticks and show bits outside plot
    ax.set_xticks([])
    for i, bit in enumerate(bits):
        ax.text(i + 0.5, -0.65, bit, ha='center', va='center', fontsize=12)
def plot_encoding(data):
    fig, axs = plt.subplots(2, 2, figsize=(14, 8), sharex=True, sharey=True)
    encodings = [
        (manchester_ieee, "Manchester (IEEE 802.3)", 'tab:blue'),
        (manchester_thomas, "Manchester (Dr. Thomas)", 'tab:orange'),
        (lambda d: diff_manchester_encode(d, initial=1), "Differential Manchester (Initial=High)", 'tab:green'),
        (nrzi_encode, "NRZI", 'tab:red'),
    ]
    axs = axs.flatten()
    for ax, (encoder, title, color) in zip(axs, encodings):
        time, signal = encoder(data)
        plot_waveform(time, signal, data, ax, title, color)
    plt.tight_layout(rect=[0, 0.05, 1, 1])
    fig.suptitle("Digital Line Encodings", fontsize=16)
    plt.subplots_adjust(hspace=0.3)
    plt.show()
if name == "main":
    binary_input = input("Enter a binary string (e.g., 1011001): ").strip()
    if not all(bit in '01' for bit in binary_input):
        print("Invalid binary input.")
    else:
        plot_encoding(binary_input)