#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char determineClassByDecimal(int firstOctet) {
    if (firstOctet >= 1 && firstOctet <= 126) {
        return 'A';
    } else if (firstOctet >= 128 && firstOctet <= 191) {
        return 'B';
    } else if (firstOctet >= 192 && firstOctet <= 223) {
        return 'C';
    } else if (firstOctet >= 224 && firstOctet <= 239) {
        return 'D';
    } else if (firstOctet >= 240 && firstOctet <= 255) {
        return 'E';
    } else {
        return 'X';  // Invalid
    }
}

// Function to determine class using bitwise pattern matching
char determineClassByBitwise(int firstOctet) {
    if ((firstOctet & 0x80) == 0) {  // 0xxxxxxx
        return 'A';
    } else if ((firstOctet & 0xC0) == 0x80) {  // 10xxxxxx
        return 'B';
    } else if ((firstOctet & 0xE0) == 0xC0) {  // 110xxxxx
        return 'C';
    } else if ((firstOctet & 0xF0) == 0xE0) {  // 1110xxxx
        return 'D';
    } else if ((firstOctet & 0xF8) == 0xF0) {  // 11110xxx
        return 'E';
    } else {
        return 'X';  // Invalid
    }
}

// Function to convert binary string to decimal
int binaryToDecimal(const char *binary) {
    int decimal = 0;
    for (int i = 0; binary[i] != '\0'; i++) {
        decimal = decimal * 2 + (binary[i] - '0');
    }
    return decimal;
}

int main() {
    char input[100];
    int firstOctet;
    int isBinary = 0;

    printf(
        "Enter the IP address (binary or decimal, e.g., 192.168.1.1 or "
        "11000000.10101000.00000001.00000001): ");
    scanf("%s", input);

    // Check if input is binary
    if (strchr(input, '.') != NULL) {
        // Split the input by '.' and extract the first octet
        char *token = strtok(input, ".");
        if (strspn(token, "01") == strlen(token)) {
            isBinary = 1;
            firstOctet = binaryToDecimal(token);
        } else {
            firstOctet = atoi(token);
        }
    } else {
        printf("Invalid IP address format.\n");
        return 1;
    }

    if (firstOctet < 0 || firstOctet > 255) {
        printf("Invalid IP address input.\n");
        return 1;
    }

    char classByDecimal = determineClassByDecimal(firstOctet);
    char classByBitwise = determineClassByBitwise(firstOctet);

    printf("\nInput Format: %s\n", isBinary ? "Binary" : "Decimal");
    printf("First Octet: %d\n", firstOctet);
    printf("Class (Decimal Range): %c\n", classByDecimal);
    printf("Class (Bitwise Matching): %c\n", classByBitwise);

    return 0;
}