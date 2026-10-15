import socket

HOST = "127.0.0.1"  # Must match the server host
PORT = 5000
BUFFER_SIZE = 4096


def main():
    filename = input("Enter the filename to request: ").strip()

    if not filename or "\n" in filename:
        print("Please enter a valid filename.")
        return

    try:
        with socket.create_connection(
            (HOST, PORT), timeout=10
        ) as client:
            client.sendall(filename.encode("utf-8") + b"\n")

            # Read the status line
            status = bytearray()

            while not status.endswith(b"\n"):
                chunk = client.recv(1)

                if not chunk:
                    print(
                        "Connection closed before status was received."
                    )
                    return

                status.extend(chunk)

            status_text = status.decode(
                "utf-8", errors="replace"
            ).strip()

            if status_text != "OK":
                message = bytearray()

                while True:
                    chunk = client.recv(BUFFER_SIZE)

                    if not chunk:
                        break

                    message.extend(chunk)

                print(
                    status_text + ": "
                    + message.decode("utf-8", errors="replace")
                )
                return

            # Receive file bytes until the server closes the connection
            contents = bytearray()

            while True:
                chunk = client.recv(BUFFER_SIZE)

                if not chunk:
                    break

                contents.extend(chunk)

            print(
                f"\nReceived {len(contents)} bytes from {filename}:"
            )
            print(contents.decode("utf-8", errors="replace"))

    except (OSError, TimeoutError) as exc:
        print(f"Could not communicate with the server: {exc}")


if __name__ == "__main__":
    main()