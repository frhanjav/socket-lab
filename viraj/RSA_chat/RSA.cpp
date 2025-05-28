#include <cmath>
#include <iostream>
#include <vector>

using namespace std;

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
    for (unsigned char ch : msg) {
        out.push_back(modexp(ch, pub_key[0], pub_key[1]));
    }
    return out;
}

string decrypt(const vector<long long> &cipher,
               const vector<long long> &priv_key) {
    string out;
    for (long long c : cipher) {
        out.push_back(char(modexp(c, priv_key[0], priv_key[1])));
    }
    return out;
}

int main() {
    auto pub  = vector<long long>{5, 323};
    auto priv = vector<long long>{173, 323};

    auto cipher = encrypt("B", pub);
    cout << "Encrypted: \n";
    for (auto c : cipher) cout << ' ' << c;
    cout << endl;
    for (auto c : cipher) cout << ' ' << (char)c;

    cout << "\nDecrypted: " << decrypt(cipher, priv) << endl;

    // cout << (modexp(32, 173, 323));
}
