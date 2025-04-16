import random
import sys

class ErrorDetectionSimulator:
    def __init__(self):
        self.data = None
        self.block_size = None
        self.checksum_result = None
        self.crc_result = None
        self.polynomial = None
        self.transmitted_data = None
        self.error_position = None
        
    def get_user_input(self):
        print("\n=== ERROR DETECTION SIMULATOR ===\n")
        
        # Get data from user
        self.data = input("Enter the data to transmit (binary string): ")
        # Validate binary input
        if not all(bit in '01' for bit in self.data):
            print("Error: Data must be a binary string (only 0s and 1s)")
            sys.exit(1)
            
        # Get algorithm choice
        print("\nSelect error detection algorithm:")
        print("1. Checksum")
        print("2. Cyclic Redundancy Check (CRC)")
        algorithm = input("Enter your choice (1/2): ")
        
        if algorithm == '1':
            self.run_checksum_simulation()
        elif algorithm == '2':
            self.run_crc_simulation()
        else:
            print("Invalid choice. Exiting.")
            sys.exit(1)
    
    def run_checksum_simulation(self):
        # Get block size
        self.block_size = int(input("\nEnter block size for checksum calculation: "))
        if self.block_size <= 0 or self.block_size > len(self.data):
            print(f"Error: Block size must be between 1 and {len(self.data)}")
            sys.exit(1)
            
        # Calculate checksum
        print("\n=== SENDER SIDE ===")
        print(f"Original data: {self.data}")
        
        self.checksum_result = self.calculate_checksum(self.data, self.block_size)
        print(f"Calculated checksum: {self.checksum_result}")
        
        # Prepare data for transmission
        self.transmitted_data = self.data + self.checksum_result
        print(f"Data to be transmitted: {self.transmitted_data}")
        
        # Simulate transmission with error
        self.simulate_transmission_error()
        
        # Receiver verification
        print("\n=== RECEIVER SIDE ===")
        print(f"Received data: {self.transmitted_data}")
        
        # Verification
        received_data = self.transmitted_data[:-len(self.checksum_result)]
        received_checksum = self.transmitted_data[-len(self.checksum_result):]
        
        print(f"Extracted data: {received_data}")
        print(f"Extracted checksum: {received_checksum}")
        
        # Calculate checksum again for verification
        verification_checksum = self.calculate_checksum(received_data, self.block_size)
        print(f"Recalculated checksum: {verification_checksum}")
        
        if verification_checksum == received_checksum:
            print("\nResult: No error detected (checksum matches)")
        else:
            print("\nResult: Error detected! (checksum mismatch)")
            if self.error_position is not None:
                print(f"Error was introduced at position {self.error_position}")
    
    def run_crc_simulation(self):
        # Get polynomial
        self.polynomial = input("\nEnter CRC polynomial in binary (e.g., 1101): ")
        if not all(bit in '01' for bit in self.polynomial) or self.polynomial[0] != '1':
            print("Error: Polynomial must be a binary string starting with 1")
            sys.exit(1)
            
        # Calculate CRC
        print("\n=== SENDER SIDE ===")
        print(f"Original data: {self.data}")
        print(f"Generator polynomial: {self.polynomial}")
        
        self.crc_result = self.calculate_crc(self.data, self.polynomial)
        print(f"Calculated CRC: {self.crc_result}")
        
        # Prepare data for transmission
        self.transmitted_data = self.data + self.crc_result
        print(f"Data to be transmitted: {self.transmitted_data}")
        
        # Simulate transmission with error
        self.simulate_transmission_error()
        
        # Receiver verification
        print("\n=== RECEIVER SIDE ===")
        print(f"Received data: {self.transmitted_data}")
        
        # CRC verification
        remainder = self.crc_division(self.transmitted_data, self.polynomial)
        print(f"CRC verification remainder: {remainder}")
        
        if int(remainder, 2) == 0:
            print("\nResult: No error detected (remainder is zero)")
        else:
            print("\nResult: Error detected! (non-zero remainder)")
            if self.error_position is not None:
                print(f"Error was introduced at position {self.error_position}")
            
    def calculate_checksum(self, data, block_size):
        # Pad data if needed
        padded_data = data
        if len(data) % block_size != 0:
            padded_data = data + '0' * (block_size - (len(data) % block_size))
            
        # Divide data into blocks
        blocks = [padded_data[i:i+block_size] for i in range(0, len(padded_data), block_size)]
        
        print(f"Data after padding: {padded_data}")
        print(f"Data divided into {len(blocks)} blocks of size {block_size}:")
        for i, block in enumerate(blocks):
            print(f"  Block {i+1}: {block}")
        
        # Calculate sum
        total = 0
        for block in blocks:
            total += int(block, 2)
            
        # Convert to binary and take 1's complement
        binary_sum = bin(total)[2:]  # Remove '0b' prefix
        
        # Ensure the binary sum has the same length as block_size
        if len(binary_sum) > block_size:
            # Keep only the least significant bits
            binary_sum = binary_sum[-block_size:]
        elif len(binary_sum) < block_size:
            # Pad with zeros
            binary_sum = '0' * (block_size - len(binary_sum)) + binary_sum
            
        print(f"Binary sum: {binary_sum}")
        
        # Calculate 1's complement
        ones_complement = ''.join('1' if bit == '0' else '0' for bit in binary_sum)
        print(f"1's complement (checksum): {ones_complement}")
        
        return ones_complement
        
    def calculate_crc(self, data, polynomial):
        # Append zeros to the data (equal to degree of polynomial - 1)
        augmented_data = data + '0' * (len(polynomial) - 1)
        print(f"Data with appended zeros: {augmented_data}")
        
        # Perform CRC division
        remainder = self.crc_division(augmented_data, polynomial)
        print(f"CRC calculation remainder: {remainder}")
        
        return remainder
        
    def crc_division(self, dividend, divisor):
        # CRC division using XOR
        remainder = dividend[:len(divisor)]
        
        steps = []
        current_position = len(divisor)
        
        while current_position <= len(dividend):
            # If the first bit is '1', XOR with the divisor
            if remainder[0] == '1':
                xor_result = ''.join('1' if remainder[i] != divisor[i] else '0' for i in range(len(divisor)))
                remainder = xor_result[1:] + (dividend[current_position] if current_position < len(dividend) else '0')
                step = f"XOR with {divisor}: {xor_result}, new remainder: {remainder}"
            else:
                # If the first bit is '0', XOR with zeros (essentially just shift)
                remainder = remainder[1:] + (dividend[current_position] if current_position < len(dividend) else '0')
                step = f"Shift (first bit is 0): new remainder: {remainder}"
            
            steps.append(step)
            current_position += 1
            
        # Print first few and last few steps if there are many
        if len(steps) > 10:
            for i in range(3):
                print(f"  Step {i+1}: {steps[i]}")
            print("  ...")
            for i in range(3):
                print(f"  Step {len(steps)-3+i+1}: {steps[len(steps)-3+i]}")
        else:
            for i, step in enumerate(steps):
                print(f"  Step {i+1}: {step}")
                
        return remainder
        
    def simulate_transmission_error(self):
        # Ask if user wants to introduce an error
        introduce_error = input("\nDo you want to introduce an error in transmission? (y/n): ")
        
        if introduce_error.lower() == 'y':
            # Get error position or generate random
            error_type = input("Select error introduction method:\n1. Specify position\n2. Random position\nEnter choice (1/2): ")
            
            if error_type == '1':
                pos = int(input(f"Enter bit position to flip (0-{len(self.transmitted_data)-1}): "))
                if pos < 0 or pos >= len(self.transmitted_data):
                    print(f"Error: Position must be between 0 and {len(self.transmitted_data)-1}")
                    sys.exit(1)
                self.error_position = pos
            else:
                self.error_position = random.randint(0, len(self.transmitted_data) - 1)
                
            # Flip the bit at the selected position
            bit_list = list(self.transmitted_data)
            bit_list[self.error_position] = '1' if bit_list[self.error_position] == '0' else '0'
            self.transmitted_data = ''.join(bit_list)
            
            print(f"Error introduced at position {self.error_position}: bit flipped")
        else:
            print("No errors introduced in transmission")
            self.error_position = None

# Run the simulator
if __name__ == "__main__":
    simulator = ErrorDetectionSimulator()
    simulator.get_user_input()
    
    # Ask if the user wants to run again
    while True:
        again = input("\nDo you want to run another simulation? (y/n): ")
        if again.lower() != 'y':
            break
        simulator = ErrorDetectionSimulator()
        simulator.get_user_input()
    
    print("\nThank you for using the Error Detection Simulator!")