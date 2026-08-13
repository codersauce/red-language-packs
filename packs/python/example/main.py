from __future__ import annotations

import asyncio
from dataclasses import dataclass

# A typed constant used by the runtime and stub examples.
DEFAULT_GREETING = "Hello"


@dataclass(slots=True)
class Greeter:
    prefix: str = DEFAULT_GREETING

    def greet(self, name: str = "Red") -> str:
        """Return a friendly, typed greeting."""
        message = f"{self.prefix}, {name}!\n"
        print(message, end="")
        return message


async def main() -> None:
    greeter = Greeter()
    await asyncio.sleep(0)
    greeter.greet()


if __name__ == "__main__":
    asyncio.run(main())
