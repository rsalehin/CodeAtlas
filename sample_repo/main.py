"""Main entry point for the CodeAtlas calculator demo."""

from calculator import add, subtract, multiply, divide
from utils import Logger, Config

def main():
    logger = Logger()
    config = Config()
    logger.log("Calculator started")

    a, b = 10, 5
    logger.log(f"add({a}, {b}) = {add(a, b)}")
    logger.log(f"subtract({a}, {b}) = {subtract(a, b)}")
    logger.log(f"multiply({a}, {b}) = {multiply(a, b)}")
    logger.log(f"divide({a}, {b}) = {divide(a, b)}")

if __name__ == "__main__":
    main()
