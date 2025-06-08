# hamming_utils_corrected.py
import math
import logging

class HammingCode:
    """
    Hamming Code encoder/decoder for error detection and correction.
    Supports dynamic encoding based on input data length.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO)
    
    def _calculate_parity_bits(self, data_bits):
        """Calculate minimum number of parity bits r required for m data bits (2^r >= m + r + 1)."""
        if data_bits < 0:
            raise ValueError("Number of data bits cannot be negative.")
        if data_bits == 0:
            return 2
        r = 1
        while (2**r) < (data_bits + r + 1):
            r += 1
        return r
    
    def _string_to_binary(self, text):
        """Convert string to binary representation (each char as 8 bits)."""
        return ''.join(format(ord(char), '08b') for char in text)
    
    def _binary_to_string(self, binary):
        """Convert binary representation back to string."""
        if len(binary) % 8 != 0:
            self.logger.error(f"Cannot convert binary to string: length {len(binary)} is not a multiple of 8.")
            raise ValueError(f"Cannot convert binary to string: length {len(binary)} is not a multiple of 8.")
        chars = []
        for i in range(0, len(binary), 8):
            byte = binary[i:i+8]
            chars.append(chr(int(byte, 2)))
        return ''.join(chars)
    
    def _is_plausible_hamming_length(self, n_bits):
        """Checks if n_bits could be a valid Hamming code length."""
        if n_bits <= 0:
            return False
        r_present = self._calculate_min_parity_bits(n_bits)
        m_present = n_bits - r_present
        if m_present < 0:
            return False
        if m_present == 0:
            r_required_for_zero = self._calculate_parity_bits(0)
            return r_present == r_required_for_zero
        r_required = self._calculate_parity_bits(m_present)
        return r_present == r_required

    def encode(self, message):
        """
        Encode a string message using Hamming code.
        Returns Hamming encoded binary string (no additional padding).
        """
        self.logger.info("=" * 60)
        self.logger.info("HAMMING ENCODING PROCESS")
        self.logger.info("=" * 60)
        
        data_binary = self._string_to_binary(message)
        data_bits = len(data_binary)
        
        self.logger.info(f"Original message: '{message}'")
        self.logger.info(f"Message in binary: {data_binary} (length: {data_bits})")
        
        if data_bits == 0:
            r = self._calculate_parity_bits(0)
            total_length = r
            hamming_code = ['0'] * total_length
            # Calculate parity bits for empty data
            for i_r in range(r):
                parity_pos = 2 ** i_r
                parity_val = 0
                for bit_pos_check in range(1, total_length + 1):
                    if bit_pos_check & parity_pos:
                        if bit_pos_check != parity_pos:
                            parity_val ^= int(hamming_code[bit_pos_check - 1])
                hamming_code[parity_pos - 1] = str(parity_val)
            encoded = "".join(hamming_code)
            self.logger.info(f"Final Hamming encoded binary: {encoded}")
            return encoded

        r = self._calculate_parity_bits(data_bits)
        self.logger.info(f"Minimum parity bits required (r): {r}")
        
        total_length = data_bits + r
        self.logger.info(f"Total length of Hamming code (n = m+r): {total_length}")
        
        hamming_code = ['0'] * total_length
        data_idx = 0
        parity_positions_list = []
        data_positions_list = []

        for i in range(1, total_length + 1):
            if self._is_power_of_2(i):
                parity_positions_list.append(i)
            else:
                hamming_code[i - 1] = data_binary[data_idx]
                data_idx += 1
                data_positions_list.append(i)

        self.logger.info(f"Parity bit positions (1-indexed): {parity_positions_list}")
        self.logger.info(f"Data bit positions (1-indexed): {data_positions_list}")
        
        # Calculate parity bits
        for i_r in range(r):
            parity_pos = 2 ** i_r
            parity_val = 0
            for bit_pos_check in range(1, total_length + 1):
                if bit_pos_check & parity_pos:
                    if bit_pos_check != parity_pos:
                        parity_val ^= int(hamming_code[bit_pos_check - 1])
            hamming_code[parity_pos - 1] = str(parity_val)
            self.logger.info(f"Calculated Parity P{parity_pos} (at index {parity_pos - 1}): {parity_val}")

        encoded = "".join(hamming_code)
        self.logger.info(f"Final Hamming encoded binary: {encoded}")
        self.logger.info("Encoding completed successfully!")
        self.logger.info("=" * 60)
        return encoded
    
    def decode(self, received_encoded_data):
        """
        Decode Hamming encoded binary data with error detection and correction.
        Returns (decoded_message, error_info).
        """
        self.logger.info("=" * 60)
        self.logger.info("HAMMING DECODING PROCESS")
        self.logger.info("=" * 60)
        
        received_encoded_data = received_encoded_data.strip()
        self.logger.info(f"Received raw data: '{received_encoded_data}' (length: {len(received_encoded_data)})")
        
        total_length = len(received_encoded_data)
        if total_length == 0:
            self.logger.error("Cannot decode empty data.")
            return None, {
                'syndrome': -1,
                'error_detected': True,
                'error_corrected': False,
                'error_position': None,
                'repairable': False,
                'message': "Empty data"
            }

        if not self._is_plausible_hamming_length(total_length):
            self.logger.error(f"Length {total_length} is not a plausible Hamming code length.")
            return None, {
                'syndrome': -1,
                'error_detected': True,
                'error_corrected': False,
                'error_position': None,
                'repairable': False,
                'message': f"Length {total_length} not plausible Hamming."
            }

        r = self._calculate_min_parity_bits(total_length)
        self.logger.info(f"Calculated parity bits present (r) for length {total_length}: {r}")
        
        received_code_list = list(received_encoded_data)
        syndrome = 0
        
        for i_r in range(r):
            parity_pos_val = 2 ** i_r
            current_parity_check_sum = 0
            for bit_pos_check in range(1, total_length + 1):
                if bit_pos_check & parity_pos_val:
                    current_parity_check_sum ^= int(received_code_list[bit_pos_check - 1])
            if current_parity_check_sum != 0:
                syndrome += parity_pos_val
            self.logger.info(f"Parity check for P{parity_pos_val}: sum = {current_parity_check_sum}. Syndrome bit p{i_r} = {current_parity_check_sum}")
        
        self.logger.info(f"Calculated syndrome: {syndrome}")
        
        error_info = {
            'syndrome': syndrome,
            'error_detected': syndrome != 0,
            'error_corrected': False,
            'error_position': None,
            'repairable': True
        }

        if syndrome != 0:
            if syndrome <= total_length:
                idx = syndrome - 1
                original_bit = received_code_list[idx]
                received_code_list[idx] = '1' if original_bit == '0' else '0'
                corrected_bit = received_code_list[idx]
                error_info['error_corrected'] = True
                error_info['error_position'] = syndrome
                self.logger.info(f"Error detected at bit position {syndrome}. Corrected '{original_bit}' to '{corrected_bit}'.")
                self.logger.info(f"Corrected data block: {''.join(received_code_list)}")
            else:
                error_info['repairable'] = False
                self.logger.error(f"Syndrome {syndrome} is out of bounds for data length {total_length}. Non-repairable error.")
                return None, error_info
        else:
            self.logger.info("No errors detected (syndrome is 0).")

        # Extract data bits
        data_bits_extracted = []
        for i in range(1, total_length + 1):
            if not self._is_power_of_2(i):
                data_bits_extracted.append(received_code_list[i - 1])
        
        final_data_binary = "".join(data_bits_extracted)
        self.logger.info(f"Extracted data bits: {final_data_binary} (length: {len(final_data_binary)})")
        
        try:
            decoded_message = self._binary_to_string(final_data_binary)
            self.logger.info(f"Successfully decoded message: '{decoded_message}'")
            return decoded_message, error_info
        except ValueError as e:
            self.logger.error(f"Failed to convert extracted binary to string: {e}")
            error_info['repairable'] = False
            error_info['message'] = str(e)
            return None, error_info
        finally:
            self.logger.info("Decoding process finished.")
            self.logger.info("=" * 60)

    def _calculate_min_parity_bits(self, total_length):
        """Calculate how many parity bits r are present in a code of total_length n. (number of powers of 2 <= n)"""
        if total_length < 1:
            return 0
        r = 0
        power_of_2 = 1
        while power_of_2 <= total_length:
            r += 1
            power_of_2 *= 2
        return r

    def _is_power_of_2(self, n):
        """Check if number is power of 2."""
        return n > 0 and (n & (n - 1)) == 0

    def simulate_error(self, encoded_data, error_positions):
        """
        Simulate bit errors for testing purposes.
        """
        self.logger.info("=" * 40)
        self.logger.info("SIMULATING BIT ERRORS")
        self.logger.info("=" * 40)
        data_list = list(encoded_data)
        self.logger.info(f"Original data for error simulation: {encoded_data} (length {len(encoded_data)})")
        for pos in error_positions:
            if 1 <= pos <= len(data_list):
                idx = pos - 1
                original_bit = data_list[idx]
                data_list[idx] = '1' if data_list[idx] == '0' else '0'
                new_bit = data_list[idx]
                self.logger.info(f"Flipped bit at position {pos}: '{original_bit}' -> '{new_bit}'")
            else:
                self.logger.warning(f"Invalid error position {pos} - Skipped.")
        corrupted_data = ''.join(data_list)
        self.logger.info(f"Corrupted data: {corrupted_data}")
        self.logger.info("Error simulation completed")
        self.logger.info("=" * 40)
        return corrupted_data