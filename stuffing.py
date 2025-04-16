def bit_stuff(data, flag):
    """
    Perform bit stuffing on binary data.
    
    Args:
        data (str): Binary data as a string of '0's and '1's
        flag (str): Flag pattern as a string of '0's and '1's
        
    Returns:
        str: Bit-stuffed data
        list: Positions where bits were stuffed
    """
    # Find the sequence that triggers stuffing
    # For most protocols, this is five consecutive 1's
    stuff_after = '11111'  # Traditional bit stuffing looks for five 1's
    
    # Initialize result with empty string
    stuffed_data = ""
    stuff_positions = []
    
    # Initialize pattern tracking
    current_pattern = ""
    
    # Process each bit in the data
    for i, bit in enumerate(data):
        # Add the current bit to the result
        stuffed_data += bit
        
        # Update the current pattern
        current_pattern += bit
        if len(current_pattern) > len(stuff_after):
            current_pattern = current_pattern[1:]
        
        # If we have a matching pattern, stuff a bit
        if current_pattern == stuff_after:
            stuffed_data += '0'  # Insert a '0' to prevent flag pattern
            stuff_positions.append(i)
            current_pattern = current_pattern[1:] + '0'  # Update the pattern
    
    return stuffed_data, stuff_positions

def bit_destuff(data, flag):
    """
    Perform bit de-stuffing on received data.
    
    Args:
        data (str): Bit-stuffed data as a string of '0's and '1's
        flag (str): Flag pattern as a string of '0's and '1's
        
    Returns:
        str: Original (de-stuffed) data
        list: Positions where bits were removed
    """
    # Find the sequence that triggers de-stuffing
    stuff_after = '11111'  # Traditional bit stuffing looks for five 1's
    
    # Initialize result with empty string
    destuffed_data = ""
    destuff_positions = []
    
    # Initialize pattern tracking
    current_pattern = ""
    
    i = 0
    while i < len(data):
        bit = data[i]
        destuffed_data += bit
        
        # Update the current pattern
        current_pattern += bit
        if len(current_pattern) > len(stuff_after):
            current_pattern = current_pattern[1:]
        
        # If we have five consecutive 1's followed by a 0, remove the 0
        if current_pattern == stuff_after and i + 1 < len(data) and data[i + 1] == '0':
            # Skip the next bit (the stuffed '0')
            i += 1
            destuff_positions.append(i)
            # Reset the pattern since we've handled this sequence
            current_pattern = ""
        
        i += 1
    
    return destuffed_data, destuff_positions

def frame_data(data, flag):
    """
    Frame data with flags and perform bit stuffing.
    
    Args:
        data (str): Binary data as a string of '0's and '1's
        flag (str): Flag pattern as a string of '0's and '1's
        
    Returns:
        str: Framed and bit-stuffed data
        list: Positions where bits were stuffed
    """
    stuffed_data, stuff_positions = bit_stuff(data, flag)
    return flag + stuffed_data + flag, stuff_positions

def extract_data(framed_data, flag):
    """
    Extract and de-stuff data from a framed message.
    
    Args:
        framed_data (str): Framed and bit-stuffed data
        flag (str): Flag pattern as a string of '0's and '1's
        
    Returns:
        str: Original data
        list: Positions where bits were removed
    """
    # Find the flags
    flag_length = len(flag)
    
    # Extract the data between the flags
    if framed_data.startswith(flag) and framed_data.endswith(flag):
        stuffed_data = framed_data[flag_length:-flag_length]
        return bit_destuff(stuffed_data, flag)
    else:
        return "Error: Frame not properly delimited by flags", []

def main():
    # Get user input
    print("Bit Stuffing and De-stuffing Demonstration")
    print("=========================================")
    
    data = input("Enter binary data (0s and 1s only): ")
    flag = input("Enter flag pattern (0s and 1s only): ")
    
    # Validate inputs
    if not all(bit in '01' for bit in data) or not all(bit in '01' for bit in flag):
        print("Error: Input must contain only 0s and 1s")
        return
    
    if len(flag) < 2:
        print("Error: Flag pattern must be at least 2 bits long")
        return
    
    # Perform bit stuffing and framing
    print("\nOriginal Data:", data)
    
    # Stuff the data
    stuffed_data, stuff_positions = bit_stuff(data, flag)
    print("Stuffed Data:", stuffed_data)
    
    # Frame the data
    framed_data, _ = frame_data(data, flag)
    print("Transmitted Frame:", framed_data)
    
    # Display bit-by-bit analysis of the framing process
    print("\nBit Stuffing Analysis:")
    print(f"Flag Pattern: {flag}")
    
    # Show where bits were stuffed
    if stuff_positions:
        print("\nStuffing Process:")
        for pos in stuff_positions:
            # Calculate position in the original data (0-indexed)
            print(f"Position {pos+1}: '0' inserted after finding five consecutive 1's")
        
        # Visual representation of the stuffing
        print("\nVisual Representation:")
        result = ""
        orig_idx = 0
        
        for i in range(len(stuffed_data)):
            if orig_idx in stuff_positions:
                result += "0̲"  # Underlined 0 to show it was stuffed
                orig_idx += 1
            else:
                if orig_idx < len(data):
                    result += data[orig_idx]
                    orig_idx += 1
        
        print(f"Original with stuffed bits: {result}")
    else:
        print("No bit stuffing needed - five consecutive 1's not found in data")
    
    # Extract and de-stuff the data
    received_data, destuff_positions = extract_data(framed_data, flag)
    print("\nDe-stuffed Data:", received_data)
    
    # Verify the process
    if received_data == data:
        print("Verification: SUCCESS - Original data recovered successfully")
    else:
        print("Verification: FAILED - Original data not recovered correctly")
        print("\nDebug Information:")
        print(f"Original data length: {len(data)}")
        print(f"De-stuffed data length: {len(received_data)}")
        print("First difference at position:", end=" ")
        for i in range(min(len(data), len(received_data))):
            if data[i] != received_data[i]:
                print(i, f"(Original: {data[i]}, De-stuffed: {received_data[i]})")
                break

def detailed_analysis(original, stuffed, flag):
    """Provide a detailed bit-by-bit analysis of the stuffing process"""
    print("\nDetailed Bit-by-Bit Analysis:")
    
    # Track the pattern we're looking for
    pattern = ""
    
    # Track original and stuffed positions
    orig_pos = 0
    stuff_pos = 0
    
    print(f"{'Pos':4} | {'Orig':4} | {'Pattern':7} | {'Action':25} | {'Stuffed':20}")
    print("-" * 70)
    
    while orig_pos < len(original):
        bit = original[orig_pos]
        
        # Update pattern
        pattern += bit
        if len(pattern) > 5:
            pattern = pattern[1:]
        
        print(f"{orig_pos:4} | {bit:4} | {pattern:7} | ", end="")
        
        # Check if we need to stuff a bit
        if pattern == "11111":
            print(f"Stuff '0' after five 1's     | {stuffed[stuff_pos:stuff_pos+6]:20}")
            stuff_pos += 1  # Account for the extra bit
        else:
            print(f"No stuffing needed          | {stuffed[stuff_pos:stuff_pos+5]:20}")
        
        orig_pos += 1
        stuff_pos += 1

if __name__ == "__main__":
    main()