import sys
from secdb import server
from secdb import update


def main():
    print(sys.argv)
    if len(sys.argv) != 2 or sys.argv[1] not in (
        "serve",
        "update-once",
        "update-forever",
    ):
        print("Usage: python3 -m secdb <serve | update-once | update-forever>")
        sys.exit(1)
    match sys.argv[1]:
        case "serve":
            return server.start_server("0.0.0.0", "8000")
        case "update-once":
            return update.once()
        case "update-forever":
            return update.forever()  # TODO: Deprecate


if __name__ == "__main__":
    main()
