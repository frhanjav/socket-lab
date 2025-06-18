import math

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def mod_inverse(e, phi_n):
    try:
        return pow(e, -1, phi_n)  # Python 3.8+
    except (ValueError, TypeError):
        # Extended Euclidean Algorithm fallback
        m0, x0, x1 = phi_n, 0, 1
        temp_e = e
        if phi_n == 1:
            return 0
        while temp_e > 1:
            if m0 == 0:
                return None
            q = temp_e // m0
            m0, temp_e, m0 = m0, m0, temp_e % m0
            x0, x1 = x1 - q * x0, x0
        return x1 + phi_n if x1 < 0 else x1

def is_prime(num):
    if num < 2:
        return False
    for i in range(2, int(math.sqrt(num)) + 1):
        if num % i == 0:
            return False
    return True

def generate_keypair(p, q):
    if not (is_prime(p) and is_prime(q)) or p == q:
        raise ValueError("p and q must be distinct primes")
    
    n = p * q
    phi_n = (p - 1) * (q - 1)
    
    # Try common values for e
    for e in [65537, 17, 7]:
        if e < phi_n and gcd(e, phi_n) == 1:
            break
    else:
        # Find suitable e
        for e in range(3, phi_n, 2):
            if gcd(e, phi_n) == 1:
                break
        else:
            raise ValueError("No suitable e found")
    
    d = mod_inverse(e, phi_n)
    if d is None:
        raise ValueError("Could not compute modular inverse")
    
    return ((e, n), (d, n))

def encrypt(public_key, message):
    e, n = public_key
    return [pow(ord(char), e, n) for char in message]

def decrypt(private_key, cipher_numbers):
    d, n = private_key
    try:
        return "".join(chr(pow(num, d, n)) for num in cipher_numbers)
    except ValueError:
        return None

# Demo
if __name__ == "__main__":
    p, q = 13, 17
    print(f"Primes: p={p}, q={q}")
    
    public_key, private_key = generate_keypair(p, q)
    print(f"Public key: {public_key}")
    print(f"Private key: {private_key}")
    
    message = "Hello RSA!"
    print(f"Original: '{message}'")
    
    encrypted = encrypt(public_key, message)
    print(f"Encrypted: {encrypted}")
    
    decrypted = decrypt(private_key, encrypted)
    print(f"Decrypted: '{decrypted}'")
    
    print("Success!" if message == decrypted else "Failed!")