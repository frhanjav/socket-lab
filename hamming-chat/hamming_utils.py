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
        # Configure basic logging if no handlers are already set up for this logger
        # This allows it to work standalone or integrate with client/server logging
        if not self.logger.handlers and not logging.getLogger().handlers:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def _calculate_parity_bits(self, data_bits):
        """Calculate minimum number of parity bits r required for m data bits (2^r >= m + r + 1)."""
        if data_bits < 0:
            raise ValueError("Number of data bits cannot be negative.")
        if data_bits == 0: # Special case for empty string, needs parity bits to detect it's "empty" not "corrupted"
            return 2 # e.g., (7,4) code can handle m=0. 2^2 >= 0+2+1 (4 >= 3). (3,1) might work too.
                     # For consistency, let's use a minimal r. If r=1, 2^1 < 0+1+1.
                     # Using r=2 implies n=2 for m=0. Parity bits P1, P2.
        r = 1
        while (2**r) < (data_bits + r + 1):
            r += 1
        return r
    
    def _string_to_binary(self, text):
        """Convert string to binary representation (each char as 8 bits)."""
        return ''.join(format(ord(char), '08b') for char in text)
    
    def _binary_to_string(self, binary):
        """Convert binary representation back to string."""
        if not binary: # Handle empty binary string case
            return ""
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
        # Try to determine r from n. For a (n,k) code, n = k+r.
        # We need to find an r such that n - r = k (data bits) and 2^r >= (n-r) + r + 1 = n + 1.
        # This means we iterate r values and see if n == k+r fits.
        # A simpler way: count how many parity bits would be in a code of length n.
        r_present = 0
        temp_n = n_bits
        p_val = 1
        while p_val <= temp_n:
            r_present += 1
            p_val *= 2
        
        m_present = n_bits - r_present
        if m_present < 0: # Should not happen if r_present is calculated correctly
            return False
        
        # Now check if this r_present is correct for m_present data bits
        r_required_for_m_present = self._calculate_parity_bits(m_present)
        return r_present == r_required_for_m_present

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
        
        if data_bits == 0: # Handle empty message
            r = self._calculate_parity_bits(0) # Get r for m=0
            total_length = r # n = r since m=0
            hamming_code = ['0'] * total_length 
            # Parity bits for m=0 are all 0 if we consider data bits to be 0.
            # P1 checks positions 1,3,5... P2 checks 2,3,6,7...
            # Since there are no data bits, all parity calculations result in 0.
            # (e.g. for r=2, n=2, P1=0, P2=0. code = "00")
            encoded = "".join(hamming_code) # Should be all '0's for the parity bits
            self.logger.info(f"Encoding empty message. r={r}, total_length={total_length}")
            self.logger.info(f"Final Hamming encoded binary for empty message: {encoded}")
            return encoded

        r = self._calculate_parity_bits(data_bits)
        self.logger.info(f"Minimum parity bits required (r): {r}")
        
        total_length = data_bits + r
        self.logger.info(f"Total length of Hamming code (n = m+r): {total_length}")
        
        hamming_code = ['0'] * total_length # Initialize with placeholders
        data_idx = 0
        parity_positions_list = []
        data_positions_list = []

        # Place data bits
        for i in range(1, total_length + 1):
            if self._is_power_of_2(i):
                parity_positions_list.append(i)
            else:
                if data_idx < data_bits:
                    hamming_code[i - 1] = data_binary[data_idx]
                    data_idx += 1
                    data_positions_list.append(i)
                else: # Should not happen if r is calculated correctly
                    self.logger.error("Ran out of data bits while expecting more data positions.")
                    # This indicates an issue, possibly with m=0 handling or r calculation
                    # For now, fill with '0' or raise error
                    hamming_code[i-1] = 'X' # Mark unexpected state


        self.logger.info(f"Parity bit positions (1-indexed): {parity_positions_list}")
        self.logger.info(f"Data bit positions (1-indexed): {data_positions_list}")
        self.logger.debug(f"Hamming code after placing data bits: {''.join(hamming_code)}")
        
        # Calculate parity bits
        for i_r_idx in range(r): # Iterate 0 to r-1
            parity_pos_1_indexed = 2 ** i_r_idx # Parity bit P1, P2, P4, P8... (position is 2^i_r_idx)
            parity_val = 0
            for bit_pos_check_1_indexed in range(1, total_length + 1):
                # If current bit_pos_check_1_indexed should be checked by this parity_pos_1_indexed
                if (bit_pos_check_1_indexed & parity_pos_1_indexed):
                    # And it's not the parity bit itself (we sum data bits it covers)
                    if bit_pos_check_1_indexed != parity_pos_1_indexed:
                        parity_val ^= int(hamming_code[bit_pos_check_1_indexed - 1])
            
            hamming_code[parity_pos_1_indexed - 1] = str(parity_val)
            self.logger.info(f"Calculated Parity P{parity_pos_1_indexed} (at index {parity_pos_1_indexed - 1}): {parity_val}")

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
        
        error_info_template = {
            'syndrome': -1, 'error_detected': True, 'error_corrected': False,
            'error_position': None, 'repairable': False, 'message': ""
        }

        if total_length == 0: # Should not happen if server sends valid Hamming codes
            self.logger.error("Cannot decode empty data.")
            error_info_template['message'] = "Empty data received"
            return None, error_info_template

        # Determine r based on total_length n. This is the number of parity bits *expected* in the code.
        r = self._calculate_min_parity_bits(total_length)
        # Determine m (data bits) based on this r.
        m = total_length - r
        
        # Now, check if this m and r are consistent:
        # The r we found must be the r required for m data bits.
        if m < 0: # More parity bits than total bits, impossible
            self.logger.error(f"Invalid Hamming code structure: n={total_length}, calculated r={r} implies m<0.")
            error_info_template['message'] = f"Invalid code structure (n={total_length}, r={r})."
            return None, error_info_template

        r_expected_for_m = self._calculate_parity_bits(m)
        if r != r_expected_for_m:
            self.logger.error(f"Inconsistent Hamming code: n={total_length}. Found r={r} for m={m}. Expected r={r_expected_for_m} for this m.")
            error_info_template['message'] = f"Inconsistent code structure (n={total_length}, m={m}, r={r}, expected_r={r_expected_for_m})."
            return None, error_info_template
        
        self.logger.info(f"Decoding code of length n={total_length}, expecting m={m} data bits and r={r} parity bits.")
        
        received_code_list = list(received_encoded_data)
        syndrome = 0
        
        # Calculate syndrome
        for i_r_idx in range(r): # Iterate 0 to r-1 for P1, P2, P4...
            parity_pos_1_indexed = 2 ** i_r_idx
            current_parity_check_sum = 0
            for bit_pos_check_1_indexed in range(1, total_length + 1):
                if (bit_pos_check_1_indexed & parity_pos_1_indexed): # If this bit position is checked by current parity bit
                    current_parity_check_sum ^= int(received_code_list[bit_pos_check_1_indexed - 1])
            
            if current_parity_check_sum != 0:
                syndrome += parity_pos_1_indexed # Add the parity bit's "value" (2^i_r_idx) to syndrome
            self.logger.info(f"Parity check for P{parity_pos_1_indexed}: sum = {current_parity_check_sum}. Syndrome bit p{i_r_idx} = {current_parity_check_sum}")
        
        self.logger.info(f"Calculated syndrome: {syndrome}")
        
        error_info = {
            'syndrome': syndrome,
            'error_detected': syndrome != 0,
            'error_corrected': False,
            'error_position': None,
            'repairable': True # Assume repairable unless a condition makes it not
        }

        if syndrome != 0: # Error detected
            if syndrome <= total_length: # Syndrome points to a valid bit position
                idx_0_indexed = syndrome - 1
                original_bit = received_code_list[idx_0_indexed]
                received_code_list[idx_0_indexed] = '1' if original_bit == '0' else '0'
                corrected_bit = received_code_list[idx_0_indexed]
                error_info['error_corrected'] = True
                error_info['error_position'] = syndrome # 1-indexed
                self.logger.info(f"Error detected at bit position {syndrome}. Corrected '{original_bit}' to '{corrected_bit}'.")
                self.logger.info(f"Corrected data block: {''.join(received_code_list)}")
            else: # Syndrome is out of bounds, indicates multiple errors or uncorrectable error
                error_info['repairable'] = False
                error_info['message'] = f"Syndrome {syndrome} out of bounds for data length {total_length}. Non-repairable error."
                self.logger.error(error_info['message'])
                return None, error_info
        else: # No errors detected
            self.logger.info("No errors detected (syndrome is 0).")

        # Extract data bits
        data_bits_extracted = []
        for i_1_indexed in range(1, total_length + 1):
            if not self._is_power_of_2(i_1_indexed):
                data_bits_extracted.append(received_code_list[i_1_indexed - 1])
        
        final_data_binary = "".join(data_bits_extracted)
        self.logger.info(f"Extracted data bits: {final_data_binary} (length: {len(final_data_binary)})")
        
        # Handle case where m=0, which means final_data_binary should be empty
        if m == 0:
            if not final_data_binary:
                self.logger.info("Successfully decoded to an empty message (m=0).")
                return "", error_info # Decoded message is an empty string
            else:
                # This state should ideally not be reached if logic is correct
                self.logger.error(f"Expected m=0 (empty data) but extracted '{final_data_binary}'.")
                error_info['repairable'] = False
                error_info['message'] = "Inconsistency: Expected empty data but found some."
                return None, error_info

        try:
            decoded_message = self._binary_to_string(final_data_binary)
            self.logger.info(f"Successfully decoded message: '{decoded_message}'")
            return decoded_message, error_info
        except ValueError as e:
            self.logger.error(f"Failed to convert extracted binary to string: {e}")
            error_info['repairable'] = False # If conversion fails, data is not usable
            error_info['message'] = str(e)
            return None, error_info
        finally:
            self.logger.info("Decoding process finished.")
            self.logger.info("=" * 60)

    def _calculate_min_parity_bits(self, total_length):
        """Calculate how many parity bits r are present in a code of total_length n. (number of powers of 2 <= n)"""
        if total_length < 1:
            return 0 # No bits, no parity bits
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
        `error_positions` is a list of 1-indexed positions.
        """
        self.logger.info("=" * 40)
        self.logger.info("SIMULATING BIT ERRORS")
        self.logger.info("=" * 40)
        data_list = list(encoded_data)
        self.logger.info(f"Original data for error simulation: {encoded_data} (length {len(encoded_data)})")
        for pos in error_positions:
            if 1 <= pos <= len(data_list):
                idx = pos - 1 # Convert to 0-indexed
                original_bit = data_list[idx]
                data_list[idx] = '1' if data_list[idx] == '0' else '0'
                new_bit = data_list[idx]
                self.logger.info(f"Flipped bit at position {pos} (index {idx}): '{original_bit}' -> '{new_bit}'")
            else:
                self.logger.warning(f"Invalid error position {pos} - Skipped. Max pos: {len(data_list)}")
        corrupted_data = ''.join(data_list)
        self.logger.info(f"Corrupted data: {corrupted_data}")
        self.logger.info("Error simulation completed")
        self.logger.info("=" * 40)
        return corrupted_data