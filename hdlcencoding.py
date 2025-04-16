# For HDLC frames - inserting a '0' after five consecutive '1's

def bit_stuff(data, flag):
    """
    Perform bit stuffing on binary data.
    
    Args:
        data (str): Binary data as a string of '0's and '1's
        flag (str): Flag pattern as a string of '0's and '1's
        
    Returns:
        str: Bit-stuffed data
    """
    # Determine the pattern to look for (all bits of the flag except the last one)
    stuff_pattern = flag[:-1]
    
    # Initialize result with empty string
    stuffed_data = ""
    
    # Initialize pattern tracking
    current_match = ""
    
    # Process each bit in the data
    for bit in data:
        # Add the current bit to the result
        stuffed_data += bit
        
        # Update the current match pattern
        current_match += bit
        if len(current_match) > len(stuff_pattern):
            current_match = current_match[1:]
        
        # If we have a matching pattern, stuff a bit
        if current_match == stuff_pattern and bit == flag[-1]:
            stuffed_data += '0'  # Insert a '0' to prevent flag pattern
            current_match = current_match[1:] + '0'  # Update the current match
    
    return stuffed_data

def bit_destuff(data, flag):
    """
    Perform bit de-stuffing on received data.
    
    Args:
        data (str): Bit-stuffed data as a string of '0's and '1's
        flag (str): Flag pattern as a string of '0's and '1's
        
    Returns:
        str: Original (de-stuffed) data
    """
    # Determine the pattern to look for (all bits of the flag except the last one)
    stuff_pattern = flag[:-1]
    
    # Initialize result with empty string
    destuffed_data = ""
    
    # Initialize pattern tracking
    current_match = ""
    i = 0
    
    # Process each bit in the data
    while i < len(data):
        bit = data[i]
        destuffed_data += bit
        
        # Update the current match pattern
        current_match += bit
        if len(current_match) > len(stuff_pattern):
            current_match = current_match[1:]
        
        # If we have a matching pattern plus the last bit of the flag
        if current_match == stuff_pattern and bit == flag[-1]:
            # Skip the next bit (which was stuffed)
            if i + 1 < len(data):
                i += 1
                current_match = current_match[1:] + data[i]
        
        i += 1
    
    return destuffed_data

def frame_data(data, flag):
    """
    Frame data with flags and perform bit stuffing.
    
    Args:
        data (str): Binary data as a string of '0's and '1's
        flag (str): Flag pattern as a string of '0's and '1's
        
    Returns:
        str: Framed and bit-stuffed data
    """
    stuffed_data = bit_stuff(data, flag)
    return flag + stuffed_data + flag

def extract_data(framed_data, flag):
    """
    Extract and de-stuff data from a framed message.
    
    Args:
        framed_data (str): Framed and bit-stuffed data
        flag (str): Flag pattern as a string of '0's and '1's
        
    Returns:
        str: Original data
    """
    # Find the flags
    flag_length = len(flag)
    
    # Extract the data between the flags
    if framed_data.startswith(flag) and framed_data.endswith(flag):
        stuffed_data = framed_data[flag_length:-flag_length]
        return bit_destuff(stuffed_data, flag)
    else:
        return "Error: Frame not properly delimited by flags"

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
    stuffed_data = bit_stuff(data, flag)
    print("Stuffed Data:", stuffed_data)
    
    # Frame the data
    framed_data = frame_data(data, flag)
    print("Transmitted Frame:", framed_data)
    
    # Display bit-by-bit analysis of the framing process
    print("\nBit Stuffing Analysis:")
    print(f"Flag Pattern: {flag}")
    
    # Show the stuffing process
    print("\nStuffing Process:")
    current_match = ""
    analysis = ""
    
    for i, bit in enumerate(data):
        current_match += bit
        if len(current_match) > len(flag) - 1:
            current_match = current_match[1:]
        
        if current_match == flag[:-1] and bit == flag[-1]:
            analysis += f"Position {i}: Inserted '0' after bit '{bit}' to prevent flag pattern\n"
    
    if analysis:
        print(analysis)
    else:
        print("No bit stuffing needed - flag pattern not found in data")
    
    # Extract and de-stuff the data
    received_data = extract_data(framed_data, flag)
    print("\nDe-stuffed Data:", received_data)
    
    # Verify the process
    if received_data == data:
        print("Verification: SUCCESS - Original data recovered successfully")
    else:
        print("Verification: FAILED - Original data not recovered correctly")

if __name__ == "__main__":
    main()