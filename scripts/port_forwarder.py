import socket
import threading
import sys

def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try:
            src.close()
        except Exception:
            pass
        try:
            dst.close()
        except Exception:
            pass

def handle(client_sock):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_sock.connect(("127.0.0.1", 8000))
    except Exception:
        client_sock.close()
        return

    t1 = threading.Thread(target=forward, args=(client_sock, server_sock), daemon=True)
    t2 = threading.Thread(target=forward, args=(server_sock, client_sock), daemon=True)
    t1.start()
    t2.start()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", 80))
    except Exception as e:
        print(f"Failed to bind port 80: {e}")
        sys.exit(1)
    s.listen(128)
    print("Port forwarder listening on 0.0.0.0:80 -> 127.0.0.1:8000")
    while True:
        client, _ = s.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()

if __name__ == "__main__":
    main()
