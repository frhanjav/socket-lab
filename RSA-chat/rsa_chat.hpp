#ifndef RSA_CHAT_HPP
#define RSA_CHAT_HPP

#include <vector>
#include <string>
#include <cmath>
#include <sstream> // For serialization/deserialization
#include <iterator> // For stream iterators
#include <algorithm> // For std::copy
#include <cstdio> // For fprintf (used in original)
#include <cctype> // For isprint (used in original LogCryptoData)


// Use the standard C++ namespace for convenience in this header
// Re-evaluating "using namespace std;" - it's generally bad practice in headers.
// For this specific, small project header, it might be acceptable, but I'll qualify std::
// where it's simple to do so.

// --- RSA Core Functions ---

long long modexp(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = (result * base) % mod;
        base = (base * base) % mod;
        exp >>= 1;
    }
    return result;
}

std::vector<long long> encrypt(const std::string &msg, const std::vector<long long> &pub_key) {
    std::vector<long long> out;
    if (pub_key.size() < 2) return out; 
    for (unsigned char ch : msg) {
        out.push_back(modexp(ch, pub_key[0], pub_key[1]));
    }
    return out;
}

std::string decrypt(const std::vector<long long> &cipher, const std::vector<long long> &priv_key) {
    std::string out;
    if (priv_key.size() < 2) return ""; 
    try {
        for (long long c : cipher) {
            long long decrypted_val = modexp(c, priv_key[0], priv_key[1]);
            if (decrypted_val < 0 || decrypted_val > 255) {
                // fprintf(stderr, "Decryption resulted in invalid char value: %lld\n", decrypted_val);
                out.push_back('?'); 
            } else {
                out.push_back(static_cast<char>(decrypted_val));
            }
        }
    } catch (const std::exception& e) {
        fprintf(stderr, "Decryption exception: %s\n", e.what());
        return ""; 
    }
    return out;
}

// --- Serialization / Deserialization ---

std::string serialize_ciphertext(const std::vector<long long>& cipher) {
    std::ostringstream oss;
    if (!cipher.empty()) {
        std::copy(cipher.begin(), cipher.end() - 1, std::ostream_iterator<long long>(oss, " "));
        oss << cipher.back();
    }
    return oss.str();
}

std::vector<long long> deserialize_ciphertext(const std::string& serialized_str) {
    std::vector<long long> cipher;
    if (serialized_str.empty()) {
        return cipher;
    }
    std::istringstream iss(serialized_str);
    long long num;
    while (iss >> num) {
        cipher.push_back(num);
    }
    if (iss.fail() && !iss.eof()) {
        fprintf(stderr, "Deserialization error: Invalid format in string '%.50s...'\n", serialized_str.c_str());
        // cipher.clear(); // Optionally clear
    }
    return cipher;
}

#endif // RSA_CHAT_HPP