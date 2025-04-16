def binary_to_decimal_ip(binary_ip):
    try:
        octets = binary_ip.split(".")
        if len(octets) != 4:
            raise ValueError("Binary IP should have 4 octets.")
        
        # Check if each octet has exactly 8 bits
        for octet in octets:
            if len(octet) != 8 or not all(bit in '01' for bit in octet):
                raise ValueError(f"Each octet must be exactly 8 binary digits (0s and 1s)")
                
        decimal_octets = [str(int(octet, 2)) for octet in octets]
        return ".".join(decimal_octets)
    except ValueError as e:
        print(f"Invalid binary IP address: {e}")
        return None

def get_ip_class_by_bits(first_octet):
    # First octet must be int
    if first_octet >> 7 == 0:  # 0xxxxxxx
        return "A"
    elif first_octet >> 6 == 0b10:  # 10xxxxxx
        return "B"
    elif first_octet >> 5 == 0b110:  # 110xxxxx
        return "C"
    elif first_octet >> 4 == 0b1110:  # 1110xxxx
        return "D"
    elif first_octet >> 4 == 0b1111:  # 1111xxxx
        return "E"
    else:
        return "Unknown"

def get_ip_class_by_range(first_octet):
    if 0 <= first_octet <= 127:
        return "A"
    elif 128 <= first_octet <= 191:
        return "B"
    elif 192 <= first_octet <= 223:
        return "C"
    elif 224 <= first_octet <= 239:
        return "D"
    elif 240 <= first_octet <= 255:
        return "E"
    else:
        return "Unknown"

def main():
    ip_input = input("Enter IP address (in decimal e.g. 192.168.0.1 or binary e.g. 11000000.10101000.00000000.00000001): ")
    
    # Check if input appears to be binary
    if all(c in "01." for c in ip_input) and len(ip_input.split(".")) == 4:
        print("\nInput detected as binary IP.")
        decimal_ip = binary_to_decimal_ip(ip_input)
        if not decimal_ip:
            return
    else:
        print("\nInput detected as decimal IP.")
        decimal_ip = ip_input
    
    try:
        octets = list(map(int, decimal_ip.split(".")))
        if len(octets) != 4 or not all(0 <= o <= 255 for o in octets):
            raise ValueError("Invalid IP address format.")
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    first_octet = octets[0]
    
    # Convert decimal IP to binary representation for display
    binary_representation = '.'.join([format(octet, '08b') for octet in octets])
    
    print(f"\nDecimal IP: {decimal_ip}")
    print(f"Binary IP: {binary_representation}")
    print(f"Class (by bit pattern): {get_ip_class_by_bits(first_octet)}")
    print(f"Class (by decimal range): {get_ip_class_by_range(first_octet)}")

if __name__ == "__main__":
    main()