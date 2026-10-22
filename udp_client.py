import json
import socket
import uuid
from pathlib import Path

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5001
TIMEOUT = 1.0
RETRIES = 5
MAX_PACKET = 2048


def send_request(sock, message, request_id):
    for _ in range(RETRIES):
        sock.sendto(
            json.dumps(message).encode("utf-8"),
            (SERVER_HOST, SERVER_PORT)
        )

        try:
            while True:
                packet, _ = sock.recvfrom(MAX_PACKET)

                if b"\n" in packet:
                    header_bytes, payload = packet.split(b"\n", 1)

                    try:
                        header = json.loads(
                            header_bytes.decode("utf-8")
                        )
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue

                    if header.get("id") == request_id:
                        return header, payload

                else:
                    try:
                        header = json.loads(packet.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue

                    if (
                        header.get("id") == request_id
                        or header.get("status") == "ERROR"
                    ):
                        return header, b""

        except socket.timeout:
            pass

    raise TimeoutError(
        "No response from server after several attempts."
    )


def main():
    filename = input("Enter the filename to request: ").strip()

    if (
        not filename
        or "/" in filename
        or "\\" in filename
        or filename in {".", ".."}
    ):
        print("Enter a simple filename without a directory path.")
        return

    request_id = str(uuid.uuid4())
    output_path = Path("received_" + Path(filename).name)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        client.settimeout(TIMEOUT)

        try:
            header, _ = send_request(
                client,
                {
                    "action": "get",
                    "id": request_id,
                    "filename": filename
                },
                request_id
            )

            if header.get("status") != "OK":
                print(
                    header.get("status", "ERROR")
                    + ": "
                    + header.get("message", "Request failed")
                )
                return

            size = header["size"]
            chunk_count = header["chunks"]
            pieces = []

            for index in range(chunk_count):
                chunk_header, payload = send_request(
                    client,
                    {
                        "action": "chunk",
                        "id": request_id,
                        "filename": filename,
                        "index": index
                    },
                    request_id
                )

                if (
                    chunk_header.get("status") != "CHUNK"
                    or chunk_header.get("index") != index
                ):
                    print("Invalid chunk response.")
                    return

                pieces.append(payload)

            content = b"".join(pieces)

            if len(content) != size:
                print(
                    "File size verification failed; "
                    "data may be incomplete."
                )
                return

            output_path.write_bytes(content)

            print(f"File received successfully: {output_path}")
            print(f"Bytes received: {len(content)}")

            try:
                print("\nFile contents:\n")
                print(content.decode("utf-8"))
            except UnicodeDecodeError:
                print(
                    "Binary file saved; "
                    "contents are not displayed as text."
                )

        except (
            OSError,
            TimeoutError,
            KeyError,
            TypeError
        ) as exc:
            print(f"File request failed: {exc}")


if __name__ == "__main__":
    main()