import sys
from paintdry import server


def main():
    print(sys.argv)
    if len(sys.argv) != 2 or sys.argv[1] not in (
        "serve",
    ):
        print("Usage: python3 -m paintdry <serve>")
        sys.exit(1)
    match sys.argv[1]:
        case "serve":
            return server.start_server("0.0.0.0", "8000")


if __name__ == "__main__":
    main()
