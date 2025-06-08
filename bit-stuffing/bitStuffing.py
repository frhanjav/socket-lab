def bit_stuff(data, threshold=5):
    stuffed = ""
    count = 0
    stuffed_positions = []
    for bit in data:
        if bit == '1':
            count += 1
            stuffed += bit
            if count == threshold:
                stuffed += '0'
                stuffed_positions.append(len(stuffed) - 1)
                count = 0
        else:
            stuffed += bit
            count = 0
    return stuffed, stuffed_positions


def bit_destuff(stuffed_data, threshold=5):
    destuffed = ""
    count = 0
    i = 0
    while i < len(stuffed_data):
        bit = stuffed_data[i]
        destuffed += bit
        if bit == '1':
            count += 1
            if count == threshold:
                i += 1
                count = 0
        else:
            count = 0
        i += 1
    return destuffed


def mark_stuffed(stuffed_data, positions):
    visual = list(stuffed_data)
    for position in positions:
        visual[position] = '_'  # Replace the stuffed '0' with '_'
    return ''.join(visual)


def main():
    data = input("Enter the binary data: ").strip()
    flag = input("Enter the flag pattern: ").strip()

    max_run = 0
    run = 0
    for bit in flag:
        if bit == '1':
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    threshold = max_run -1
    if threshold < 1:
        threshold = 5  # fallback default

    print(f"\nbit-stuff threshold = {threshold}")

    stuffed_data, positions = bit_stuff(data, threshold)
    transmitted = flag + stuffed_data + flag
    visual_data = mark_stuffed(stuffed_data, positions)

    print("\nStuffed Bits position:")
    print(visual_data)

    print("\nStuffed Data:")
    print(stuffed_data)

    print("\nTransmitted Message:")
    print(transmitted)

    if transmitted.startswith(flag) and transmitted.endswith(flag):
        extracted = transmitted[len(flag):-len(flag)]
    else:
        print("Warning: Flag pattern not found at start and end!")
        extracted = transmitted

    received = bit_destuff(extracted, threshold)
    print("\nReceived Data after De-stuffing:")
    print(received)


if __name__ == '__main__':
    main()
