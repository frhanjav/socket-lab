// tcp_client.c
// gcc TCP_client_WIN.c -o client.exe -lws2_32; .\client.exe
#include <stdio.h>
#include <winsock2.h>

#pragma comment(lib, "ws2_32.lib")  // Link with ws2_32.lib

int main() {
    WSADATA wsa;
    SOCKET sock;
    struct sockaddr_in server;
    char buffer[1024] = {0};

    // Initialize Winsock
    WSAStartup(MAKEWORD(2, 2), &wsa);

    // Create socket
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == INVALID_SOCKET) {
        printf("Socket failed: %d\n", WSAGetLastError());
        return 1;
    }

    server.sin_addr.s_addr = inet_addr("127.0.0.1");
    server.sin_family = AF_INET;
    server.sin_port = htons(8888);

    // Connect to server
    if (connect(sock, (struct sockaddr*)&server, sizeof(server)) < 0) {
        printf("Connect failed: %d\n", WSAGetLastError());
        return 1;
    }

    printf("Connected to server.\n");

    // Allocate memory for the message
    char* msg = (char*)malloc(1024 * sizeof(char));
    if (msg == NULL) {
        printf("Memory allocation failed\n");
        closesocket(sock);
        WSACleanup();
        return 1;
    }
    
    printf("Enter a message: ");
    fgets(msg, 1024, stdin);
    
    // Remove the trailing newline character if it exists
    size_t len = strlen(msg);
    if (len > 0 && msg[len-1] == '\n') {
        msg[len-1] = '\0';
    }

    // char *message = "Hello Server!";
    // send(sock, message, strlen(message), 0);
    send(sock, msg, strlen(msg), 0);

    // Receive data
    int recv_len = recv(sock, buffer, sizeof(buffer), 0);
    if (recv_len == SOCKET_ERROR) {
        printf("recv failed: %d\n", WSAGetLastError());
    } else {
        buffer[recv_len] = '\0';
        printf("Received: %s\n", buffer);
    }

    closesocket(sock);
    WSACleanup();
    return 0;
}
