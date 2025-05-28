#ifndef RSA_CHAT_HPP
#define RSA_CHAT_HPP

#include <vector>
#include <string>
#include <cmath>
#include <sstream> // For serialization/deserialization
#include <iterator> // For stream iterators
#include <algorithm> // For std::copy

// Use the standard C++ namespace for convenience in this header
using namespace std;

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

vector<long long> encrypt(const string &msg, const vector<long long> &pub_key) {
    vector<long long> out;
    // Ensure key vector is valid
    if (pub_key.size() < 2) return out; // Return empty on bad key
    for (unsigned char ch : msg) {
        out.push_back(modexp(ch, pub_key[0], pub_key[1]));
    }
    return out;
}

string decrypt(const vector<long long> &cipher, const vector<long long> &priv_key) {
    string out;
    // Ensure key vector is valid
    if (priv_key.size() < 2) return ""; // Return empty on bad key
    try {
        for (long long c : cipher) {
            long long decrypted_val = modexp(c, priv_key[0], priv_key[1]);
            // Basic check if decrypted value is within reasonable char range
            if (decrypted_val < 0 || decrypted_val > 255) {
                 // Handle error - perhaps return partial string or throw exception
                 // For simplicity, we might just append a '?' or skip
                 // fprintf(stderr, "Decryption resulted in invalid char value: %lld\n", decrypted_val);
                 out.push_back('?'); // Indicate decryption issue
            } else {
                 out.push_back(static_cast<char>(decrypted_val));
            }
        }
    } catch (const std::exception& e) {
        // Catch potential exceptions during conversion or operations
        fprintf(stderr, "Decryption exception: %s\n", e.what());
        return ""; // Return empty string on error
    }
    return out;
}

// --- Serialization / Deserialization ---

// Convert vector<long long> to a space-separated string
string serialize_ciphertext(const vector<long long>& cipher) {
    ostringstream oss;
    if (!cipher.empty()) {
        // Copy all but the last element to avoid trailing space
        copy(cipher.begin(), cipher.end() - 1, ostream_iterator<long long>(oss, " "));
        // Add the last element
        oss << cipher.back();
    }
    return oss.str();
}

// Convert a space-separated string back to vector<long long>
vector<long long> deserialize_ciphertext(const string& serialized_str) {
    vector<long long> cipher;
    // Handle empty input string gracefully
    if (serialized_str.empty()) {
        return cipher;
    }
    istringstream iss(serialized_str);
    long long num;
    while (iss >> num) {
        cipher.push_back(num);
    }
     // Check if the entire string was consumed successfully.
     // If iss.fail() is true but not iss.eof(), it means there was non-numeric data.
    if (iss.fail() && !iss.eof()) {
        fprintf(stderr, "Deserialization error: Invalid format in string '%s'\n", serialized_str.c_str());
        // Optionally clear the vector or handle the error differently
        // cipher.clear();
    }
    return cipher;
}

#endif // RSA_CHAT_HPP