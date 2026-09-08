from src.application.bootstrap import build_application


def main():
    runner = build_application()
    return runner.run_once()


if __name__ == "__main__":
    main()
