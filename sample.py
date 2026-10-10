"""Sample Python Script
Demonstrates basic Python features: functions, type hints, loops, and entry point.
"""

from datetime import datetime


def greet(name: str) -> str:
    """Return a personalized greeting."""
    return f"Hello, {name}!"


def calculate_squares(numbers: list[int]) -> dict[int, int]:
    """Calculate the square of each number in the list."""
    return {num: num**2 for num in numbers}


def main() -> None:
    # Basic output
    user_name = "World"
    print(greet(user_name))
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Working with lists and dictionaries
    numbers = [1, 2, 3, 4, 5]
    squares = calculate_squares(numbers)

    print("Number squares:")
    for num, sq in squares.items():
        print(f"  {num}^2 = {sq}")


if __name__ == "__main__":
    main()
