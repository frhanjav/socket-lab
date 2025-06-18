# standalone_hamming_demo.py
import math
import logging

class HammingCode:
    """
    Hamming Code encoder/decoder for error detection and correction.
    Supports dynamic encoding based on input data length.
    (Copied and slightly adapted from your hamming_utils.py for standalone use)
    """
    
    def __init__(self):
        # For this demo, we'll keep logging minimal to focus on core Hamming output.
        # You can re-enable more verbose logging if needed for debugging the class itself.
        self.logger = logging.getLogger(__name__)
        # Basic config if no handlers exist, to see logs from the class if any are active
        if not self.logger.handlers and not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
            self.logger.setLevel(logging.WARNING) # Suppress INFO/DEBUG from the class for this demo

    def _calculate_parity_bits(self, data_bits):
        if data_bits < 0:
            raise ValueError("Number of data bits cannot be negative.")
        if data_bits == 0:
            return 2 # Consistent with your previous code's handling for m=0
        r = 1
        while (2**r) < (data_bits + r + 1):
            r += 1
        return r
    
    def _string_to_binary(self, text):
        return ''.join(format(ord(char), '08b') for char in text)
    
    def _binary_to_string(self, binary):
        if not binary:
            return ""
        if len(binary) % 8 != 0:
            raise ValueError(f"Binary string length {len(binary)} is not a multiple of 8.")
        chars = []
        for i in range(0, len(binary), 8):
            byte = binary[i:i+8]
            chars.append(chr(int(byte, 2)))
        return ''.join(chars)

    def _is_power_of_2(self, n):
        return n > 0 and (n & (n - 1)) == 0
    
    def _calculate_min_parity_bits(self, total_length):
        """Calculates how many parity bits 'r' are in a code of 'total_length' n."""
        if total_length < 1: return 0
        r = 0
        power_of_2 = 1
        while power_of_2 <= total_length:
            r += 1
            power_of_2 *= 2
        return r

    def encode(self, message):
        data_binary = self._string_to_binary(message)
        data_bits_m = len(data_binary)
        
        # self.logger.info(f"Encoding message: '{message}' (Binary: {data_binary}, m={data_bits_m})")

        if data_bits_m == 0:
            r = self._calculate_parity_bits(0)
            total_length_n = r
            hamming_code_list = ['0'] * total_length_n
            # Parity bits for m=0 are all 0
            encoded = "".join(hamming_code_list)
            # self.logger.info(f"Encoded empty message to: {encoded} (n={total_length_n}, r={r})")
            return encoded

        r = self._calculate_parity_bits(data_bits_m)
        total_length_n = data_bits_m + r
        # self.logger.info(f"Calculated r={r} for m={data_bits_m}, so n={total_length_n}")
        
        hamming_code_list = ['0'] * total_length_n
        data_idx = 0
        
        # Place data bits
        for i_1_indexed in range(1, total_length_n + 1):
            if not self._is_power_of_2(i_1_indexed):
                if data_idx < data_bits_m:
                    hamming_code_list[i_1_indexed - 1] = data_binary[data_idx]
                    data_idx += 1
        
        # Calculate parity bits
        for i_r_idx in range(r):
            parity_pos_1_indexed = 2 ** i_r_idx
            parity_val = 0
            for bit_pos_check_1_indexed in range(1, total_length_n + 1):
                if (bit_pos_check_1_indexed & parity_pos_1_indexed):
                    if bit_pos_check_1_indexed != parity_pos_1_indexed: # Don't XOR with self if it was pre-filled
                        parity_val ^= int(hamming_code_list[bit_pos_check_1_indexed - 1])
            hamming_code_list[parity_pos_1_indexed - 1] = str(parity_val)
            
        encoded = "".join(hamming_code_list)
        # self.logger.info(f"Final encoded data: {encoded}")
        return encoded

    def decode(self, received_encoded_data):
        total_length_n = len(received_encoded_data)
        
        error_info_template = {
            'syndrome': -1, 'error_detected': True, 'error_corrected': False,
            'error_position': None, 'repairable': False, 'message': ""
        }

        if total_length_n == 0:
            error_info_template['message'] = "Empty data received"
            return None, error_info_template

        # Determine r based on total_length n
        r_in_code = self._calculate_min_parity_bits(total_length_n)
        data_bits_m = total_length_n - r_in_code
        
        if data_bits_m < 0:
             error_info_template['message'] = f"Invalid code structure (n={total_length_n}, r_in_code={r_in_code} implies m<0)."
             return None, error_info_template

        r_expected_for_m = self._calculate_parity_bits(data_bits_m)
        if r_in_code != r_expected_for_m:
            error_info_template['message'] = (f"Inconsistent Hamming code: n={total_length_n}. "
                                             f"Found r_in_code={r_in_code} for m={data_bits_m}. "
                                             f"Expected r={r_expected_for_m} for this m.")
            return None, error_info_template
        
        # self.logger.info(f"Decoding data: {received_encoded_data} (n={total_length_n}, m={data_bits_m}, r={r_in_code})")
        
        received_code_list = list(received_encoded_data)
        syndrome = 0
        
        for i_r_idx in range(r_in_code):
            parity_pos_1_indexed = 2 ** i_r_idx
            current_parity_check_sum = 0
            for bit_pos_check_1_indexed in range(1, total_length_n + 1):
                if (bit_pos_check_1_indexed & parity_pos_1_indexed):
                    current_parity_check_sum ^= int(received_code_list[bit_pos_check_1_indexed - 1])
            if current_parity_check_sum != 0:
                syndrome += parity_pos_1_indexed
        
        # self.logger.info(f"Calculated syndrome: {syndrome}")
        
        error_info = {
            'syndrome': syndrome,
            'error_detected': syndrome != 0,
            'error_corrected': False,
            'error_position': None,
            'repairable': True 
        }

        if syndrome != 0:
            if syndrome <= total_length_n:
                idx_0_indexed = syndrome - 1
                received_code_list[idx_0_indexed] = '1' if received_code_list[idx_0_indexed] == '0' else '0'
                error_info['error_corrected'] = True
                error_info['error_position'] = syndrome
                # self.logger.info(f"Error at bit {syndrome} corrected. New code: {''.join(received_code_list)}")
            else:
                error_info['repairable'] = False
                error_info['message'] = f"Syndrome {syndrome} out of bounds for n={total_length_n}. Non-repairable."
                # self.logger.error(error_info['message'])
                return None, error_info
        
        data_bits_extracted = []
        for i_1_indexed in range(1, total_length_n + 1):
            if not self._is_power_of_2(i_1_indexed):
                data_bits_extracted.append(received_code_list[i_1_indexed - 1])
        
        final_data_binary = "".join(data_bits_extracted)
        # self.logger.info(f"Extracted data bits: {final_data_binary}")

        if data_bits_m == 0: # Empty original message
            return "", error_info # Decoded message is an empty string

        try:
            decoded_message = self._binary_to_string(final_data_binary)
            # self.logger.info(f"Successfully decoded message: '{decoded_message}'")
            return decoded_message, error_info
        except ValueError as e:
            # self.logger.error(f"Binary to string conversion failed: {e}")
            error_info['repairable'] = False
            error_info['message'] = str(e)
            return None, error_info

    def simulate_error(self, encoded_data, error_positions_1_indexed):
        """Simulates bit errors. error_positions is a list of 1-indexed positions."""
        data_list = list(encoded_data)
        for pos_1_indexed in error_positions_1_indexed:
            if 1 <= pos_1_indexed <= len(data_list):
                idx_0_indexed = pos_1_indexed - 1
                data_list[idx_0_indexed] = '1' if data_list[idx_0_indexed] == '0' else '0'
            else:
                print(f"Warning: Invalid error position {pos_1_indexed} for data length {len(data_list)}.")
        return ''.join(data_list)

# --- Main demonstration ---
if __name__ == "__main__":
    hc = HammingCode()

    test_messages = ["Test!", "Hi", "A", "", "CS"] # "" for empty string test

    for original_message in test_messages:
        print(f"\n--- Testing with message: '{original_message}' ---")

        # 1. Encode
        data_binary = hc._string_to_binary(original_message)
        m = len(data_binary)
        r = hc._calculate_parity_bits(m)
        n = m + r
        
        print(f"Original Binary : {data_binary if data_binary else '(empty)'} (m={m} data bits)")
        print(f"Parity bits (r) : {r}")
        print(f"Total bits (n=m+r): {n}")
        
        encoded_data = hc.encode(original_message)
        print(f"Encoded Hamming : {encoded_data}")

        # 2. Decode (No Error)
        print("\n  Scenario A: No Error")
        decoded_A, info_A = hc.decode(encoded_data)
        print(f"  Decoded         : '{decoded_A}'")
        print(f"  Error Detected  : {info_A['error_detected']}")

        # 3. Decode (Single Bit Error - Correctable)
        if n > 0: # Only if there's something to corrupt
            print("\n  Scenario B: Single Bit Error")
            error_pos_single = [min(3, n)] # Introduce error at 3rd bit (or last if shorter)
            corrupted_B = hc.simulate_error(encoded_data, error_pos_single)
            print(f"  Corrupted (at {error_pos_single}): {corrupted_B}")
            decoded_B, info_B = hc.decode(corrupted_B)
            print(f"  Decoded         : '{decoded_B}'")
            print(f"  Error Detected  : {info_B['error_detected']}")
            print(f"  Error Corrected : {info_B['error_corrected']}")
            if info_B['error_corrected']:
                print(f"  Corrected at Bit: {info_B['error_position']}")
        else:
            print("\n  Scenario B: Single Bit Error (SKIPPED - no bits to corrupt for empty encoded data)")


        # 4. Decode (Double Bit Error - Likely Uncorrectable by standard Hamming)
        if n >= 2: # Need at least 2 bits for a double error
            print("\n  Scenario C: Double Bit Error")
            error_pos_double = [min(1,n), min(2,n) if n > 1 else 1] # Error at 1st and 2nd bit
            if error_pos_double[0] == error_pos_double[1] and n==1: # avoid same pos if n=1
                 print("  (Skipping double error for n=1 as it's a single bit)")
            else:
                corrupted_C = hc.simulate_error(encoded_data, error_pos_double)
                print(f"  Corrupted (at {error_pos_double}): {corrupted_C}")
                decoded_C, info_C = hc.decode(corrupted_C)
                print(f"  Decoded         : '{decoded_C}' (May be incorrect or None)")
                print(f"  Error Detected  : {info_C['error_detected']}")
                print(f"  Error Corrected : {info_C['error_corrected']}")
                print(f"  Repairable      : {info_C['repairable']}")
                if not info_C['repairable'] and info_C['message']:
                     print(f"  Reason          : {info_C['message']}")
                elif info_C['error_detected'] and not info_C['error_corrected']:
                     print(f"  Syndrome        : {info_C['syndrome']} (Indicates error, but not corrected)")
        else:
            print("\n  Scenario C: Double Bit Error (SKIPPED - not enough bits for double error)")
        print("-" * 40)