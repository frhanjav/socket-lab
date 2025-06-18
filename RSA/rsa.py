import math

# --- Helper Functions ---
def gcd(a, b):
    """Compute the greatest common divisor of a and b."""
    while b:
        a, b = b, a % b
    return a

def mod_inverse(e_orig, phi_n_orig): # Renamed parameters for clarity inside the function
    """Compute the modular multiplicative inverse of e modulo phi_n.
       Returns d such that (d * e) % phi_n == 1.
       Requires Python 3.8+ for the third argument to pow().
       For older versions, you'd implement the Extended Euclidean Algorithm.
    """
    e = e_orig      # Work with copies if you might modify them
    phi_n = phi_n_orig # Work with copies

    try:
        # Python 3.8+ modular inverse
        return pow(e, -1, phi_n)
    except ValueError:
        # Fallback or error if e and phi_n are not coprime
        print(f"Error: {e} and {phi_n} are not coprime. No modular inverse exists (pow(-1) method).")
        return None
    except TypeError: # For older Python versions that don't support pow(e,-1,phi_n)
        print(f"Note: pow({e}, -1, {phi_n}) requires Python 3.8+. Implementing Extended Euclidean Algorithm for inverse.")
        # Extended Euclidean Algorithm for modular inverse
        # Based on a standard implementation
        
        # We need to ensure we use the original values for the final check and potential error message.
        # The algorithm itself modifies its local copies of e and phi_n (or m0).
        
        m0, x0, x1 = phi_n, 0, 1 # Here phi_n is phi_n_orig
        temp_e = e               # Here e is e_orig

        if phi_n == 1: # phi_n_orig == 1
            return 0 # Should not happen with proper phi_n (which is (p-1)*(q-1))

        while temp_e > 1:
            if m0 == 0: # Avoid division by zero if temp_e doesn't reduce phi_n to 0
                print(f"Error: {e_orig} and {phi_n_orig} are not coprime (Euclidean Algorithm path). m0 became 0.")
                return None
            q = temp_e // m0
            m, temp_e, m0 = m0, m0, temp_e % m0 # Standard Euclidean step
            x0, x1 = x1 - q * x0, x0
        
        # Make x1 positive if it's negative
        if x1 < 0:
            x1 += phi_n_orig # Use the original phi_n for this adjustment
        
        # Final check if the computed inverse is correct
        if (e_orig * x1) % phi_n_orig != 1:
             print(f"Error: {e_orig} and {phi_n_orig} are not coprime or Euc. Alg. failed. No modular inverse exists. (Check: ({e_orig}*{x1})%{phi_n_orig} = {(e_orig * x1) % phi_n_orig})")
             return None
        return x1


# --- RSA Core Functions ---
def generate_keypair(p, q):
    """
    Generate an RSA public/private key pair.
    p and q: Two distinct prime numbers.
    """
    if not (is_prime(p) and is_prime(q)):
        raise ValueError("Both numbers must be prime.")
    elif p == q:
        raise ValueError("p and q must be distinct.")

    n = p * q
    phi_n = (p - 1) * (q - 1)  # Euler's totient function

    # Choose e such that 1 < e < phi_n and gcd(e, phi_n) = 1
    # Common choices for e are 3, 17, 65537
    e = 65537 # A common public exponent
    if e >= phi_n or gcd(e, phi_n) != 1:
        # Fallback if 65537 is not suitable (e.g., for very small p, q)
        e = 17 
        if e >= phi_n or gcd(e, phi_n) != 1:
            e = 7
            if e >= phi_n or gcd(e, phi_n) != 1:
                 # Try to find a suitable e
                for potential_e in range(3, phi_n, 2): # Check odd numbers
                    if gcd(potential_e, phi_n) == 1:
                        e = potential_e
                        break
                else: # No suitable e found
                    raise ValueError("Could not find a suitable 'e' coprime to phi_n.")


    # Compute d, the modular multiplicative inverse of e modulo phi_n
    # d * e = 1 (mod phi_n)
    d = mod_inverse(e, phi_n)
    if d is None:
        raise ValueError("Could not compute modular inverse 'd'. 'e' and 'phi_n' might not be coprime.")

    # Public key is (e, n)
    # Private key is (d, n)
    return ((e, n), (d, n))

def is_prime(num):
    """Check if a number is prime."""
    if num < 2:
        return False
    for i in range(2, int(math.sqrt(num)) + 1):
        if num % i == 0:
            return False
    return True

def encrypt(public_key, plaintext_message):
    """
    Encrypt a plaintext message using the public key.
    RSA encrypts numbers, so we convert characters to their ordinal values.
    """
    e, n = public_key
    # Convert each character to its ASCII/Unicode ordinal value, then encrypt
    # c = m^e mod n
    cipher_numbers = [pow(ord(char), e, n) for char in plaintext_message]
    return cipher_numbers

def decrypt(private_key, cipher_numbers):
    """
    Decrypt a list of cipher numbers using the private key.
    """
    d, n = private_key
    # Convert each encrypted number back to a character
    # m = c^d mod n
    try:
        decrypted_chars = [chr(pow(num, d, n)) for num in cipher_numbers]
        return "".join(decrypted_chars)
    except ValueError as ve:
        # This can happen if a decrypted number is outside the valid range for chr()
        print(f"Decryption error (likely resulting number out of chr() range): {ve}")
        print("This might indicate an issue with the key, or the ciphertext was not generated by this key.")
        return None

# --- Main Demonstration ---
if __name__ == "__main__":
    print("--- RSA Implementation Demonstration ---")

    # Step 1: Choose two distinct prime numbers (small for demonstration)
    p = 13
    q = 17
    # For a more robust test with larger numbers (still small for RSA):
    # p = 61
    # q = 53
    print(f"\n1. Chosen prime numbers:\np = {p}\nq = {q}")

    # Step 2: Generate Public and Private Keys
    try:
        public_key, private_key = generate_keypair(p, q)
        print("\n2. Key Generation:")
        print(f"   Public Key (e, n):  {public_key}")
        print(f"   Private Key (d, n): {private_key}")

        # (Intermediate calculations for clarity - not part of the keys themselves)
        n_calc = p * q
        phi_n_calc = (p - 1) * (q - 1)
        print(f"   Calculated n = p * q = {n_calc}")
        print(f"   Calculated φ(n) = (p-1)*(q-1) = {phi_n_calc}")
        print(f"   Chosen e = {public_key[0]}")
        print(f"   Calculated d = {private_key[0]} such that (d * e) % φ(n) == 1")
        if private_key[0] is not None:
             print(f"   Verification: ({private_key[0]} * {public_key[0]}) % {phi_n_calc} = {(private_key[0] * public_key[0]) % phi_n_calc}")


        # Step 3: Define a message to encrypt
        message = "Hello RSA!"
        print(f"\n3. Original Message: '{message}'")

        # Step 4: Encrypt the message
        print("\n4. Encryption Process:")
        encrypted_msg_numbers = encrypt(public_key, message)
        print(f"   Encrypted as numbers: {encrypted_msg_numbers}")
        # Note: In a real system, these numbers might be further encoded (e.g., to Base64) for transmission.

        # Step 5: Decrypt the message
        print("\n5. Decryption Process:")
        if encrypted_msg_numbers:
            decrypted_msg = decrypt(private_key, encrypted_msg_numbers)
            if decrypted_msg is not None:
                print(f"   Decrypted Message: '{decrypted_msg}'")

                # Step 6: Verify
                print("\n6. Verification:")
                if message == decrypted_msg:
                    print("   Success! Original message matches decrypted message.")
                else:
                    print("   Failure! Original message does NOT match decrypted message.")
            else:
                print("   Decryption failed to produce a valid string.")
        else:
            print("   Encryption did not produce any numbers to decrypt.")

    except ValueError as e:
        print(f"\nAn error occurred: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

    print("\n--- End of Demonstration ---")
    print("\nImportant Note: This is a simplified 'textbook' RSA implementation.")
    print("For real-world security, it requires features like proper padding schemes (e.g., OAEP),")
    print("larger prime numbers (e.g., 2048 bits for n), and secure random prime generation.")