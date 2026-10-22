import json
import socket
from pathlib import Path

HOST = "127.0.0.1"  # Use the server's LAN IP for another computer
PORT = 5001
FILE_DIR = Path("server_files").resolve()
CHUNK_SIZE = 1024
MAX_PACKET = 2048


def send_json(sock, message, address):
    sock.sendto(
        json.dumps(message).encode("utf-8"),
        address
    )


def main():
    FILE_DIR.mkdir(parents=True, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind((HOST, PORT))

        print(f"UDP server listening on {HOST}:{PORT}")
        print(f"Serving files from: {FILE_DIR}")

        while True:
            packet, address = server.recvfrom(MAX_PACKET)

            try:
                request = json.loads(packet.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                send_json(
                    server,
                    {"status": "ERROR", "message": "Invalid request"},
                    address
                )
                continue

            action = request.get("action")
            req_id = request.get("id")
            filename = request.get("filename", "")

            if not isinstance(req_id, str):
                send_json(
                    server,
                    {"status": "ERROR", "message": "Invalid request ID"},
                    address
                )
                continue

            if (
                not isinstance(filename, str)
                or not filename
                or Path(filename).name != filename
                or filename in {".", ".."}
            ):
                send_json(
                    server,
                    {
                        "id": req_id,
                        "status": "ERROR",
                        "message": "Invalid filename"
                    },
                    address
                )
                continue

            path = (FILE_DIR / filename).resolve()

            if path.parent != FILE_DIR:
                send_json(
                    server,
                    {
                        "id": req_id,
                        "status": "ERROR",
                        "message": "Invalid filename"
                    },
                    address
                )
                continue

            if action == "get":
                if not path.is_file():
                    send_json(
                        server,
                        {
                            "id": req_id,
                            "status": "NOT_FOUND",
                            "message": "Requested file was not found"
                        },
                        address
                    )
                    continue

                size = path.stat().st_size
                chunks = (size + CHUNK_SIZE - 1) // CHUNK_SIZE

                send_json(
                    server,
                    {
                        "id": req_id,
                        "status": "OK",
                        "filename": filename,
                        "size": size,
                        "chunks": chunks
                    },
                    address
                )

            elif action == "chunk":
                index = request.get("index")

                if (
                    not isinstance(index, int)
                    or isinstance(index, bool)
                    or index < 0
                    or not path.is_file()
                ):
                    send_json(
                        server,
                        {
                            "id": req_id,
                            "status": "ERROR",
                            "message": "Invalid chunk request or missing file"
                        },
                        address
                    )
                    continue

                with path.open("rb") as f:
                    f.seek(index * CHUNK_SIZE)
                    payload = f.read(CHUNK_SIZE)

                header = json.dumps(
                    {
                        "id": req_id,
                        "status": "CHUNK",
                        "index": index
                    }
                ).encode("utf-8")

                server.sendto(header + b"\n" + payload, address)

            else:
                send_json(
                    server,
                    {
                        "id": req_id,
                        "status": "ERROR",
                        "message": "Unknown action"
                    },
                    address
                )


if __name__ == "__main__":
    main()