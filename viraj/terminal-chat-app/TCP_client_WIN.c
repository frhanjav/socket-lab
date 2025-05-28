// filepath: terminal-chat-app/client/TCP_client_WIN.c
// tcp_client.c
// gcc TCP_client_WIN.c -o client.exe -lws2_32; .\client.exe
#include <process.h>  // For _beginthreadex
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <winsock2.h>

#pragma comment(lib, "ws2_32.lib")  // Link with ws2_32.lib

// Structure for thread arguments
typedef struct {
    SOCKET sock;
    int running;
} ThreadArgs;

// Receiver thread function to handle incoming messages
unsigned __stdcall receiverThread(void* param) {
    ThreadArgs* args = (ThreadArgs*)param;
    SOCKET sock = args->sock;
    char buffer[1024];
    int recv_len;

    while (args->running) {
        // Receive data
        recv_len = recv(sock, buffer, sizeof(buffer) - 1, 0);

        if (recv_len > 0) {
            // Null-terminate the message and print it
            buffer[recv_len] = '\0';
            printf("\nReceived from server: %s\n> ", buffer);
            fflush(stdout);  // Ensure the prompt is displayed
        } else if (recv_len == 0) {
            // Server closed the connection
            printf("\nServer disconnected.\n");
            args->running = 0;
            break;
        } else {
            // Error occurred
            if (args->running) {
                printf("\nrecv failed: %d\n", WSAGetLastError());
                args->running = 0;
                break;
            }
        }
    }

    printf("Receiver thread exiting.\n");
    return 0;
}

int main() {
    WSADATA wsa;
    SOCKET sock;
    struct sockaddr_in server;
    char buffer[1024] = {0};
    char ip[16];
    int port;
    char user_id[50];
    ThreadArgs thread_args;
    HANDLE h_thread;
    unsigned thread_id;

    // Prompt for server IP address and port
    printf("Enter server IP address: ");
    fgets(ip, sizeof(ip), stdin);
    ip[strcspn(ip, "\n")] = 0;  // Remove newline character

    printf("Enter server port: ");
    scanf("%d", &port);
    getchar();  // Consume newline character left by scanf

    // Validate user ID (non-empty)
    do {
        printf("Enter your user id: ");
        fgets(user_id, sizeof(user_id), stdin);
        user_id[strcspn(user_id, "\n")] = 0;  // Remove newline character

        if (strlen(user_id) == 0) {
            printf("User ID cannot be empty. Please try again.\n");
        }
    } while (strlen(user_id) == 0);

    // Initialize Winsock
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        printf("WSAStartup failed: %d\n", WSAGetLastError());
        return 1;
    }

    // Create socket
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == INVALID_SOCKET) {
        printf("Socket failed: %d\n", WSAGetLastError());
        WSACleanup();
        return 1;
    }

    server.sin_addr.s_addr = inet_addr(ip);
    server.sin_family = AF_INET;
    server.sin_port = htons(port);

    // Connect to server
    printf("Connecting to %s:%d as %s...\n", ip, port, user_id);
    if (connect(sock, (struct sockaddr*)&server, sizeof(server)) < 0) {
        printf("Connect failed: %d\n", WSAGetLastError());
        closesocket(sock);
        WSACleanup();
        return 1;
    }

    printf("Connected to server.\n");

    // send user id
    send(sock, user_id, strlen(user_id), 0);

    // Create receiver thread
    thread_args.sock = sock;
    thread_args.running = 1;

    h_thread = (HANDLE)_beginthreadex(NULL, 0, receiverThread, &thread_args, 0,
                                      &thread_id);
    if (h_thread == 0) {
        printf("Thread creation failed: %d\n", GetLastError());
        closesocket(sock);
        WSACleanup();
        return 1;
    }

    printf(
        "Type 'exit' to disconnect, 'users' to list connected users, or "
        "'userID/message' to send a direct message.\n");

    // Main messaging loop
    while (thread_args.running) {
        printf("> ");
        if (fgets(buffer, sizeof(buffer), stdin) == NULL) {
            printf("Input error\n");
            break;
        }

        // Remove the trailing newline character
        size_t len = strlen(buffer);
        if (len > 0 && buffer[len - 1] == '\n') {
            buffer[len - 1] = '\0';
            len--;
        }

        // Check for exit command
        if (strcmp(buffer, "exit") == 0) {
            send(sock, buffer, strlen(buffer), 0);
            break;
        }

        // Send message to server if not empty
        if (len > 0) {
            send(sock, buffer, strlen(buffer), 0);
        }
    }

    // Wait for receiver thread to finish (with timeout)
    thread_args.running = 0;
    WaitForSingleObject(h_thread, 1000);
    CloseHandle(h_thread);

    // Clean up
    closesocket(sock);
    WSACleanup();
    printf("Disconnected from server.\n");
    return 0;
}