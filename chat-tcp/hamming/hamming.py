import random

class HammingCodec:
    """
    Hamming(7,4) encoder/decoder that can correct single-bit errors.
    
    The Hamming(7,4) code takes 4 data bits and adds 3 parity bits to create
    a 7-bit codeword that can detect and correct single-bit errors.
    
    Bit positions (1-indexed):
    - Position 1, 2, 4: Parity bits (p1, p2, p3)
    - Position 3, 5, 6, 7: Data bits (d1, d2, d3, d4)
    
    Layout: [p1, p2, d1, p3, d2, d3, d4]
    """
    
    @staticmethod
    def encode_nibble(data_bits):
        """
        Encode 4 data bits into 7-bit Hamming code.
        
        Args:
            data_bits: List of 4 bits [d1, d2, d3, d4]
            
        Returns:
            List of 7 bits [p1, p2, d1, p3, d2, d3, d4]
        """
        if len(data_bits) != 4:
            raise ValueError("Data must be exactly 4 bits")
        
        d1, d2, d3, d4 = data_bits
        
        # Calculate parity bits
        # p1 covers positions 1,3,5,7 (p1, d1, d2, d4)
        p1 = d1 ^ d2 ^ d4
        
        # p2 covers positions 2,3,6,7 (p2, d1, d3, d4)
        p2 = d1 ^ d3 ^ d4
        
        # p3 covers positions 4,5,6,7 (p3, d2, d3, d4)
        p3 = d2 ^ d3 ^ d4
        
        return [p1, p2, d1, p3, d2, d3, d4]
    
    @staticmethod
    def decode_codeword(codeword):
        """
        Decode 7-bit Hamming code and correct single-bit errors.
        
        Args:
            codeword: List of 7 bits [p1, p2, d1, p3, d2, d3, d4]
            
        Returns:
            Tuple: (corrected_data_bits, error_position)
            - corrected_data_bits: List of 4 corrected data bits
            - error_position: 0 if no error, 1-7 if error at that position
        """
        if len(codeword) != 7:
            raise ValueError("Codeword must be exactly 7 bits")
        
        p1, p2, d1, p3, d2, d3, d4 = codeword
        
        # Calculate syndrome bits
        s1 = p1 ^ d1 ^ d2 ^ d4  # Check parity for positions 1,3,5,7
        s2 = p2 ^ d1 ^ d3 ^ d4  # Check parity for positions 2,3,6,7
        s3 = p3 ^ d2 ^ d3 ^ d4  # Check parity for positions 4,5,6,7
        
        # Error position is given by syndrome (s3,s2,s1)
        error_pos = s3 * 4 + s2 * 2 + s1
        
        # Correct the error if it exists
        corrected = codeword.copy()
        if error_pos != 0:
            corrected[error_pos - 1] ^= 1  # Flip the error bit
        
        # Extract data bits from corrected codeword
        _, _, d1_corr, _, d2_corr, d3_corr, d4_corr = corrected
        
        return [d1_corr, d2_corr, d3_corr, d4_corr], error_pos
    
    @staticmethod
    def encode_bytes(data):
        """
        Encode bytes data using Hamming(7,4) code.
        
        Args:
            data: bytes object
            
        Returns:
            bytes: Encoded data with Hamming codes
        """
        if not data:
            return b''
        
        encoded_bits = []
        
        for byte in data:
            # Split byte into two nibbles (4 bits each)
            high_nibble = [(byte >> i) & 1 for i in range(7, 3, -1)]
            low_nibble = [(byte >> i) & 1 for i in range(3, -1, -1)]
            
            # Encode each nibble
            encoded_high = HammingCodec.encode_nibble(high_nibble)
            encoded_low = HammingCodec.encode_nibble(low_nibble)
            
            encoded_bits.extend(encoded_high)
            encoded_bits.extend(encoded_low)
        
        # Convert bits to bytes (pad to byte boundary if needed)
        result = bytearray()
        for i in range(0, len(encoded_bits), 8):
            byte_bits = encoded_bits[i:i+8]
            if len(byte_bits) < 8:
                byte_bits.extend([0] * (8 - len(byte_bits)))
            
            byte_val = 0
            for j, bit in enumerate(byte_bits):
                byte_val |= bit << (7 - j)
            result.append(byte_val)
        
        return bytes(result)
    
    @staticmethod
    def decode_bytes(encoded_data):
        """
        Decode Hamming-encoded bytes data.
        
        Args:
            encoded_data: bytes object with Hamming-encoded data
            
        Returns:
            Tuple: (decoded_bytes, errors_corrected)
            - decoded_bytes: Original data with errors corrected
            - errors_corrected: List of error positions that were corrected
        """
        if not encoded_data:
            return b'', []
        
        # Convert bytes to bits
        all_bits = []
        for byte in encoded_data:
            for i in range(7, -1, -1):
                all_bits.append((byte >> i) & 1)
        
        # Decode in groups of 14 bits (two 7-bit codewords per original byte)
        decoded_bytes = bytearray()
        errors_corrected = []
        
        for i in range(0, len(all_bits), 14):
            if i + 13 >= len(all_bits):
                break  # Skip incomplete groups
            
            # Extract two codewords
            codeword1 = all_bits[i:i+7]
            codeword2 = all_bits[i+7:i+14]
            
            # Decode both codewords
            data1, error1 = HammingCodec.decode_codeword(codeword1)
            data2, error2 = HammingCodec.decode_codeword(codeword2)
            
            if error1:
                errors_corrected.append(f"Bit {i + error1}")
            if error2:
                errors_corrected.append(f"Bit {i + 7 + error2}")
            
            # Combine nibbles back into byte
            byte_val = 0
            for j, bit in enumerate(data1):
                byte_val |= bit << (7 - j)
            for j, bit in enumerate(data2):
                byte_val |= bit << (3 - j)
            
            decoded_bytes.append(byte_val)
        
        return bytes(decoded_bytes), errors_corrected
    
    @staticmethod
    def introduce_random_error(data):
        """
        Introduce a single random bit error in the data.
        
        Args:
            data: bytes object
            
        Returns:
            bytes: Data with one bit flipped
        """
        if not data:
            return data
        
        data_array = bytearray(data)
        
        # Choose random byte and bit position
        byte_pos = random.randint(0, len(data_array) - 1)
        bit_pos = random.randint(0, 7)
        
        # Flip the bit
        data_array[byte_pos] ^= (1 << bit_pos)
        
        print(f"[SERVER] Introduced error at byte {byte_pos}, bit {bit_pos}")
        
        return bytes(data_array)


def test_hamming_codec():
    """Test the Hamming codec with various inputs."""
    print("Testing Hamming Codec:")
    print("=" * 50)
    
    # Test 1: Single nibble
    print("Test 1: Single nibble [1,0,1,1]")
    data = [1, 0, 1, 1]
    encoded = HammingCodec.encode_nibble(data)
    print(f"Encoded: {encoded}")
    
    # Introduce error
    corrupted = encoded.copy()
    corrupted[2] ^= 1  # Flip bit at position 3
    print(f"Corrupted: {corrupted}")
    
    decoded, error_pos = HammingCodec.decode_codeword(corrupted)
    print(f"Decoded: {decoded}, Error at position: {error_pos}")
    print()
    
    # Test 2: String encoding
    print("Test 2: String 'Hello'")
    test_str = "Hello"
    original_bytes = test_str.encode('utf-8')
    print(f"Original: {original_bytes}")
    
    encoded_bytes = HammingCodec.encode_bytes(original_bytes)
    print(f"Encoded length: {len(encoded_bytes)} bytes (from {len(original_bytes)})")
    
    # Introduce error
    corrupted_bytes = HammingCodec.introduce_random_error(encoded_bytes)
    
    decoded_bytes, errors = HammingCodec.decode_bytes(corrupted_bytes)
    print(f"Decoded: {decoded_bytes}")
    print(f"Errors corrected: {errors}")
    print(f"Match original: {decoded_bytes == original_bytes}")
    print()


if __name__ == "__main__":
    test_hamming_codec()