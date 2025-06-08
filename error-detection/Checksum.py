from math import ceil
import random

def checksum(data: str, num_blocks: int) -> tuple[str, str, int]:
    length = len(data)
    if num_blocks < 1:
        raise ValueError("num_blocks must be at least 1")

    original_num_blocks = num_blocks # Store for accurate block_size calculation for receiver
    if num_blocks > length:
        # Option A: treat each bit as a block
        block_size = 1
        num_blocks = length # effective number of blocks becomes length
    else:
        block_size = ceil(length / num_blocks)

    print(f"\n--- Sender Side (Calculating Checksum) ---")
    print(f"Original data length: {length}, num_blocks: {original_num_blocks}, calculated block_size: {block_size}")

    blocks = []
    padded_data_str = ""
    for i in range(0, length, block_size):
        block = data[i:i + block_size]
        # pad with zeros to full block_size
        if len(block) < block_size:
            block += '0' * (block_size - len(block))
        print(f"Data block {len(blocks)}: {block}")
        blocks.append(block)
        padded_data_str += block


    total = 0
    for block_val_str in blocks:
        total += int(block_val_str, 2)

    # binary representation of the sum (no '0b' prefix)
    sum_bits_initial = bin(total)[2:]
    print(f"Initial sum of data blocks (binary): {sum_bits_initial} (decimal: {total})")

    # Handle carry wraparound in 1's complement arithmetic
    mask = (1 << block_size) - 1  # mask for block_size bits (e.g., 0b111 for block_size 3)

    temp_sum = total
    while temp_sum > mask:  # while there's a carry beyond block_size bits
        carry = temp_sum >> block_size  # extract carry bits
        temp_sum = (temp_sum & mask) + carry  # add carry back to lower bits
        print(f"  After carry wraparound: sum = {bin(temp_sum)[2:]} (decimal: {temp_sum})")
    
    # one's-complement checksum
    chk_val = (~temp_sum) & mask
    checksum_bits = bin(chk_val)[2:].zfill(block_size)

    # concatenate data blocks and checksum for transmission
    # Important: use the padded blocks for tx_data
    tx_data = padded_data_str + checksum_bits
    print(f"Calculated checksum: {checksum_bits}")
    print(f"Data to be transmitted (padded data + checksum): {tx_data}")
    return tx_data, checksum_bits, block_size


def verify_checksum(received_data: str, block_size: int) -> bool:
    print(f"\n--- Receiver Side (Verifying Checksum) ---")
    print(f"Received data (possibly corrupted): {received_data}")
    print(f"Using block_size: {block_size}")

    if len(received_data) % block_size != 0:
        print("Error: Received data length is not a multiple of block size. Cannot verify.")
        return False # Or raise an error

    received_blocks_str = []
    for i in range(0, len(received_data), block_size):
        received_blocks_str.append(received_data[i:i + block_size])
    
    print("Received blocks (including checksum as last block):")
    for i, block_s in enumerate(received_blocks_str):
        print(f"  Block {i}: {block_s}")

    total_at_receiver = 0
    for block_val_str in received_blocks_str:
        total_at_receiver += int(block_val_str, 2)
    
    sum_bits_initial_receiver = bin(total_at_receiver)[2:]
    print(f"Initial sum of received blocks (binary): {sum_bits_initial_receiver} (decimal: {total_at_receiver})")

    mask = (1 << block_size) - 1

    temp_sum_receiver = total_at_receiver
    while temp_sum_receiver > mask:
        carry = temp_sum_receiver >> block_size
        temp_sum_receiver = (temp_sum_receiver & mask) + carry
        print(f"  After carry wraparound: sum = {bin(temp_sum_receiver)[2:]} (decimal: {temp_sum_receiver})")
    
    final_sum_receiver_str = bin(temp_sum_receiver)[2:].zfill(block_size)
    print(f"Final sum at receiver (after 1s complement addition): {final_sum_receiver_str}")

    # If the sum is all 1s (equal to mask), then no error is detected
    if temp_sum_receiver == mask:
        print("Verification sum is all 1s. No error detected by checksum.")
        return True
    else:
        print(f"Verification sum is NOT all 1s ({final_sum_receiver_str}). Error detected by checksum!")
        return False

if __name__ == "__main__":
    data = input("Enter binary data: ").strip()
    while not all(c in '01' for c in data) or not data:
        print("Invalid input. Please enter a non-empty binary string (0s and 1s only).")
        data = input("Enter binary data: ").strip()

    num_blocks_input_str = input(f"Enter number of blocks (1 to {len(data)}): ")
    while True:
        try:
            num_blocks = int(num_blocks_input_str)
            if 1 <= num_blocks: # Allow num_blocks > len(data) as per original logic
                break
            else:
                print(f"Number of blocks must be at least 1.")
        except ValueError:
            print("Invalid number. Please enter an integer.")
        num_blocks_input_str = input(f"Enter number of blocks (1 to {len(data)}): ")

    # --- Sender Side ---
    tx_data, original_checksum, block_size_used = checksum(data, num_blocks)
    print('-' * 35)
    print("Original Checksum:", original_checksum)
    print("Transmitted Data (Data + Checksum):", tx_data)
    print('-' * 35)

    # --- Error Injection ---
    data_at_receiver = tx_data
    error_injected = False
    inject_choice = input("Inject a single-bit error? (y/n): ").strip().lower()
    if inject_choice == 'y':
        if not tx_data:
            print("Cannot inject error into empty transmitted data.")
        else:
            error_pos = random.randint(0, len(tx_data) - 1)
            original_bit = tx_data[error_pos]
            flipped_bit = '1' if original_bit == '0' else '0'
            
            data_list = list(tx_data)
            data_list[error_pos] = flipped_bit
            data_at_receiver = "".join(data_list)
            error_injected = True
            
            print(f"\n--- Error Injection ---")
            print(f"Original transmitted data: {tx_data}")
            print(f"Injecting error at position {error_pos} (0-indexed).")
            print(f"Bit at pos {error_pos} changed from '{original_bit}' to '{flipped_bit}'.")
            print(f"Data at receiver (corrupted): {data_at_receiver}")
            print('-' * 35)
    else:
        print("\nNo error injected.")
        print(f"Data at receiver (uncorrupted): {data_at_receiver}")
        print('-' * 35)


    # --- Receiver Side ---
    is_data_valid = verify_checksum(data_at_receiver, block_size_used)
    print('-' * 35)

    if error_injected:
        if not is_data_valid: # Error was injected AND checksum detected it
            print("Result: SUCCESS! The injected error WAS DETECTED by the checksum.")
        else: # Error was injected BUT checksum FAILED to detect it (should be rare for single bit error)
            print("Result: FAILURE! The injected error WAS NOT DETECTED by the checksum.")
    else:
        if is_data_valid: # No error injected AND checksum confirmed no error
            print("Result: Data received without errors (as expected, no error was injected).")
        else: # No error injected BUT checksum THINKS there is an error (indicates a bug in checksum logic)
            print("Result: ALARM! No error was injected, but the checksum detected an error. Check logic!")
    print('-' * 35)