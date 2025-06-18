import math

class HammingCode:
    def _parity_bits_needed(self, data_bits):
        if data_bits == 0: return 2
        r = 1
        while (2**r) < (data_bits + r + 1):
            r += 1
        return r
    
    def _text_to_bits(self, text):
        return ''.join(format(ord(char), '08b') for char in text)
    
    def _bits_to_text(self, bits):
        if not bits or len(bits) % 8 != 0: return ""
        return ''.join(chr(int(bits[i:i+8], 2)) for i in range(0, len(bits), 8))
    
    def encode(self, message):
        data_bits = self._text_to_bits(message)
        m = len(data_bits)
        r = self._parity_bits_needed(m)
        n = m + r
        
        if m == 0: return '0' * r
        
        # Create code array
        code = ['0'] * n
        
        # Place data bits (skip power-of-2 positions)
        data_idx = 0
        for pos in range(1, n + 1):
            if not (pos & (pos - 1) == 0):  # not a power of 2
                code[pos - 1] = data_bits[data_idx]
                data_idx += 1
        
        # Calculate parity bits
        for i in range(r):
            parity_pos = 2**i
            parity = 0
            for check_pos in range(1, n + 1):
                if (check_pos & parity_pos) and check_pos != parity_pos:
                    parity ^= int(code[check_pos - 1])
            code[parity_pos - 1] = str(parity)
        
        return ''.join(code)
    
    def decode(self, received_code):
        n = len(received_code)
        if n == 0: return "", "No data"
        
        # Calculate number of parity bits
        r = 0
        temp = 1
        while temp <= n:
            r += 1
            temp *= 2
        
        # Calculate syndrome
        syndrome = 0
        for i in range(r):
            parity_pos = 2**i
            if parity_pos > n: break
            
            parity = 0
            for check_pos in range(1, n + 1):
                if check_pos & parity_pos:
                    parity ^= int(received_code[check_pos - 1])
            
            if parity != 0:
                syndrome += parity_pos
        
        # Make a copy to potentially correct
        corrected = list(received_code)
        error_msg = "No error detected"
        
        if syndrome > 0:
            if syndrome <= n:
                # Correct the error
                corrected[syndrome - 1] = '1' if corrected[syndrome - 1] == '0' else '0'
                error_msg = f"Error at position {syndrome} - CORRECTED"
            else:
                error_msg = f"Error detected but cannot correct (syndrome={syndrome})"
        
        # Extract data bits
        data_bits = []
        for pos in range(1, n + 1):
            if not (pos & (pos - 1) == 0):  # not a power of 2
                data_bits.append(corrected[pos - 1])
        
        decoded_text = self._bits_to_text(''.join(data_bits))
        return decoded_text, error_msg
    
    def introduce_error(self, code, position):
        """Flip bit at given position (1-indexed)"""
        if 1 <= position <= len(code):
            code_list = list(code)
            i = position - 1
            code_list[i] = '1' if code_list[i] == '0' else '0'
            return ''.join(code_list)
        return code

# Demo
if __name__ == "__main__":
    hc = HammingCode()
    
    for msg in ["Hi", "A"]:
        print(f"\n{'='*50}")
        print(f"TESTING MESSAGE: '{msg}'")
        print(f"{'='*50}")
        
        # Show the binary representation
        bits = hc._text_to_bits(msg)
        print(f"Message as binary: {bits} ({len(bits)} bits)")
        
        # Encode
        encoded = hc.encode(msg)
        print(f"Hamming encoded:   {encoded} ({len(encoded)} bits)")
        
        # Decode without errors
        decoded, status = hc.decode(encoded)
        print(f"\nDecoding original: '{decoded}' - {status}")
        
        # Introduce error at position 3 and decode
        if len(encoded) >= 3:
            corrupted = hc.introduce_error(encoded, 3)
            print(f"Corrupted code:    {corrupted} (flipped bit 3)")
            decoded_fixed, status = hc.decode(corrupted)
            print(f"After correction:  '{decoded_fixed}' - {status}")
        
        # Show what happens with 2 errors (uncorrectable)
        if len(encoded) >= 5:
            double_error = hc.introduce_error(encoded, 2)
            double_error = hc.introduce_error(double_error, 4)
            print(f"With 2 errors:     {double_error} (flipped bits 2,4)")
            decoded_bad, status = hc.decode(double_error)
            print(f"Decode attempt:    '{decoded_bad}' - {status}")