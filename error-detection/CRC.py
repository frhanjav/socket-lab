import random

def xor(a: str, b: str) -> str:
    """Perform XOR between two binary strings a and b of equal length."""
    return ''.join('0' if x == y else '1' for x, y in zip(a, b))


def compute_crc(data: str, poly: str) -> str:
    """Compute CRC remainder for given data string and generator polynomial, with step logging."""
    poly_len = len(poly)
    # Append zeros
    padded = data + '0' * (poly_len - 1)
    div = padded[:poly_len]

    for i in range(poly_len, len(padded) + 1):
        print(f"Div: {div}")
        # Choose divisor
        if div[0] == '1':
            div = xor(div, poly)
        else:
            div = xor(div, '0' * poly_len)
        # Shift in next bit
        if i < len(padded):
            div = div[1:] + padded[i]
        else:
            div = div[1:]
    print(f"Final remainder: {div}")
    return div


def flip_random_bit(bitstring: str) -> tuple[str, int]:
    """Flip a random bit in the given bitstring and return new string and index."""
    pos = random.randrange(len(bitstring))
    flipped = list(bitstring)
    flipped[pos] = '1' if bitstring[pos] == '0' else '0'
    return ''.join(flipped), pos


def main():
    data = input("\nEnter binary data: ").strip()
    poly = input("Enter generator polynomial (binary): ").strip()

    # Compute CRC with logging
    crc = compute_crc(data, poly)
    transmitted = data + crc
    print(f"\nComputed CRC: {crc}")
    print(f"Transmitted frame: {transmitted}\n")

    # Ask whether to inject error
    choice = input("Inject error? (y/n): ").strip().lower()
    if choice == 'y':
        frame, pos = flip_random_bit(transmitted)
        print(f"Error injected at position {pos}: {frame}\n")
    else:
        frame = transmitted
        print("No error injected.\n")

    # Check at receiver with logging
    print("Checking received frame:")
    recv_remainder = compute_crc(frame, poly)
    print(f"\nRemainder at receiver: {recv_remainder}")
    if set(recv_remainder) == {'0'}:
        print("No error detected.")
    else:
        print("Error detected in received frame!")

if __name__ == "__main__":
    main()
