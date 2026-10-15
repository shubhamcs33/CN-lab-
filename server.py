import socket
from pathlib import Path

HOST = "127.0.0.1"  # Localhost; use the server's LAN IP for another computer
PORT = 5000
FILE_DIR = Path("server_files").resolve()
BUFFER_SIZE = 4096


def handle_client(conn, address):
    print(f"Connected by {address}")

    with conn:
        # Receive a filename terminated by newline (maximum 255 bytes)
        data = bytearray()

        while b"\n" not in data and len(data) <= 255:
            chunk = conn.recv(1)

            if not chunk:
                break

            data.extend(chunk)

        if not data or b"\n" not in data or len(data) > 255:
            conn.sendall(b"ERROR\nInvalid or missing filename.")
            return

        filename = (
            data.split(b"\n", 1)[0]
            .decode("utf-8", errors="replace")
            .strip()
        )

        # Validate filename and prevent directory traversal
        if (
            not filename
            or Path(filename).name != filename
            or filename in {".", ".."}
        ):
            conn.sendall(b"ERROR\nInvalid filename.")
            return

        file_path = (FILE_DIR / filename).resolve()

        if file_path.parent != FILE_DIR:
            conn.sendall(b"ERROR\nInvalid filename.")
            return

        # Check whether the requested file exists
        if not file_path.is_file():
            conn.sendall(
                b"NOT_FOUND\nThe requested file was not found."
            )
            return

        # Inform the client that the file is ready
        conn.sendall(b"OK\n")

        # Send the file in chunks
        with file_path.open("rb") as file:
            while True:
                chunk = file.read(BUFFER_SIZE)

                if not chunk:
                    break

                conn.sendall(chunk)

        print(f"Sent file: {filename}")


def main():
    FILE_DIR.mkdir(parents=True, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        server.bind((HOST, PORT))
        server.listen()

        print(f"Server listening on {HOST}:{PORT}")
        print(f"Serving files from: {FILE_DIR}")

        while True:
            conn, address = server.accept()
            handle_client(conn, address)


if __name__ == "__main__":
    main()