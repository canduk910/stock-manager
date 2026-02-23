from dotenv import load_dotenv

load_dotenv()

from stock.cli import stock  # noqa: E402

if __name__ == "__main__":
    stock()
