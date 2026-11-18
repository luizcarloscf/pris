# Python

A **program** is a list of instructions for the computer, written in a **programming language**. Python is one of the easiest to start with and one of the most used, in science, robotics and computer vision. This guide installs it, teaches the parts of the language the other guides use, and then organizes a small program as a real project, with its tests. It assumes you have done [The terminal](terminal.md).

!!! info "To learn more"

    - [The Python tutorial](https://docs.python.org/3/tutorial/): the language, from the official documentation, at your own pace;
    - [uv](https://docs.astral.sh/uv/getting-started/): the tool this guide uses to install Python and its packages;
    - [NumPy for absolute beginners](https://numpy.org/doc/stable/user/absolute_beginners.html): arrays and matrices;
    - [Getting started with pytest](https://docs.pytest.org/en/stable/getting-started.html) and [mypy](https://mypy.readthedocs.io/en/stable/getting_started.html): tests and type checks.

## Installing

Ubuntu comes with a Python of its own, `python3`, which parts of Ubuntu itself use. Leave it alone: if you install packages into it with `pip`, it refuses with `externally-managed-environment`, on purpose, so you can't break the system by accident.

Instead, install [uv](https://docs.astral.sh/uv/getting-started/installation/). It installs whichever Python you ask for, for you only, and keeps each project's packages apart, so that two projects needing different versions of a package never get in each other's way.

```shell
sudo apt update
sudo apt install -y curl git
curl -LsSf https://astral.sh/uv/install.sh | sh     # download and run uv's installer
source $HOME/.local/bin/env                          # let this terminal find uv (or open a new one)
uv python install 3.12                               # install Python 3.12
```

The third line downloads a script with `curl` and passes it, with `|`, to `sh`, which runs it. That is a common way to install tools; only do it with addresses you trust, such as a project's official site.

## Talking to Python

Start Python **interactively**: it waits for a line of Python, runs it and prints the result.

```shell
uv run --no-project --python 3.12 python
```

```
>>> 2 + 3
5
>>> 7 / 2
3.5
>>> 2 ** 10
1024
```

`>>>` is Python's prompt, as `$` is the terminal's. Type `exit()` or press ++ctrl+d++ to leave. It is handy to try things out; real programs are saved in files, as next.

## A first program

Make a folder for the guide and, in an editor, save this as `basics.py` in it:

```python
# Values and variables
name = "lab"
temperature = 22.5
readings = 3
print(name, temperature, readings)
print(type(name), type(temperature), type(readings))
print(f"{name} is at {temperature} degrees after {readings} readings")

# Lists: an ordered sequence
values = [21.0, 22.5, 23.1]
values.append(22.0)
print(values[0], values[-1], len(values))

# Dictionaries: names to values
room = {"name": "lab", "temperature": 22.5}
room["humidity"] = 55
print(room["temperature"], room)

# Decisions and repetition
for value in values:
    if value > 22.0:
        print(value, "is warm")
    else:
        print(value, "is fine")


# Functions
def average(numbers):
    """Return the mean of a list of numbers."""
    return sum(numbers) / len(numbers)


print(round(average(values), 2))
```

Run it from that folder:

```shell
uv run --no-project --python 3.12 python basics.py
```

```
lab 22.5 3
<class 'str'> <class 'float'> <class 'int'>
lab is at 22.5 degrees after 3 readings
21.0 22.0 4
22.5 {'name': 'lab', 'temperature': 22.5, 'humidity': 55}
21.0 is fine
22.5 is warm
23.1 is warm
22.0 is fine
22.15
```

Line by line, this is most of what the guides' programs do:

- **Variables.** `name = "lab"` stores a **value** under a name, to use it later. `=` means "store", not "equals".
- **Types.** Every value has a type: `str`, a **string** of text, in quotes; `float`, a number with a decimal point; `int`, a whole number. `type(...)` tells which. Types matter: `"22.5" + "1"` is the text `"22.51"`, while `float("22.5") + 1` is the number `23.5`.
- **`print`** shows values. An **f-string**, `f"... {name} ..."`, puts values inside a text.
- **Lists**, `[...]`, keep values in order. `values[0]` is the first (counting starts at 0), `values[-1]` the last, `len(values)` how many; `values.append(22.0)` adds one at the end.
- **Dictionaries**, `{...}`, look values up by a name, the **key**: `room["temperature"]`.
- **`for value in values:`** repeats the indented lines below it once per value. **`if ...:`** runs its lines only when the condition is true, **`else:`** otherwise.
- **Indentation**, the spaces at the start of a line, is part of the language: it says which lines belong to the `for`, the `if` or the function. Use 4 spaces.
- **Functions.** `def average(numbers):` defines a reusable piece of code that takes **arguments** and **returns** a result. The text in `"""` under it, its **docstring**, says what it does.
- **Comments**, after `#`, are notes for people; Python ignores them.

## Reading errors

When something goes wrong, Python stops and prints a **traceback**. Save `values = [1, 2]` and `print(values[5])` in a file and run it:

```
Traceback (most recent call last):
  File "broken.py", line 2, in <module>
    print(values[5])
          ~~~~~~^^^
IndexError: list index out of range
```

Read it from the bottom: the last line is what went wrong, an `IndexError`, asking for position 5 of a list of 2; the lines above say where, file and line number. Most errors are solved by reading that last line carefully.

## A project

A program that grows, or that uses packages written by others, becomes a **project**: a folder with a `pyproject.toml` file that names it and lists what it needs. A **package** is code someone published for others to use, such as NumPy, for numbers and matrices.

```shell
mkdir hello && cd hello
uv init --bare --python 3.12       # writes pyproject.toml
uv add numpy                       # a package the code needs
uv add --dev pytest mypy           # tools only needed while developing
```

Now the folder has:

| File | What it is |
|---|---|
| `pyproject.toml` | the project: its name, version, Python version, the packages it needs |
| `uv.lock` | the exact version of every package installed, so everyone gets the same |
| `.venv/` | the **virtual environment**: a Python and the project's packages, apart from the rest of the computer |

You never touch `.venv`: `uv run` runs any command inside it, as in `uv run python`. If you share the project, with git for instance, share `pyproject.toml` and `uv.lock`, never `.venv`: `uv sync` rebuilds it from them on any computer.

## A module

A file of Python code that other files can use is a **module**. Save this as `geometry.py`, in the project:

```python
from dataclasses import dataclass

import numpy as np


@dataclass
class Point:
    x: float
    y: float
    z: float


def translate(point: Point, offset: list[float]) -> Point:
    """Return the point moved by `offset`, using a 4x4 transformation matrix.

    Args:
        point: the point to move.
        offset: how much to move it along x, y and z.

    Returns:
        The moved point.
    """
    matrix = np.eye(4)
    matrix[:3, 3] = offset
    x, y, z, _ = matrix @ np.array([point.x, point.y, point.z, 1.0])
    return Point(float(x), float(y), float(z))


if __name__ == "__main__":
    print(translate(Point(1.0, 2.0, 0.0), [0.0, 0.0, 3.0]))
```

```shell
uv run geometry.py                 # Point(x=1.0, y=2.0, z=3.0)
```

It uses a few more things:

- **`import`** brings in a module: `import numpy as np` makes NumPy available as `np`; `from dataclasses import dataclass` takes one name from a module.
- **A class** describes a new type of value. `@dataclass` writes the boring parts for you: `Point(1.0, 2.0, 0.0)` builds one, `point.x` reads a field, and printing it shows its fields.
- **Type hints**, as in `point: Point` and `-> Point`, say what a function takes and returns. Python doesn't check them when it runs; they document the code, and mypy, below, checks them.
- **NumPy.** `np.eye(4)` is a 4×4 matrix with ones on its diagonal, the identity; `matrix[:3, 3]` is the first three rows of its last column; `@` multiplies matrices. The [Frames and transformations](../computer-vision/frames-and-transformations.md) guide explains why a 4×4 matrix moves a point written as `[x, y, z, 1]`.
- **`if __name__ == "__main__":`** runs the lines below it only when the file is run itself, not when another file imports it.

## Tests

A **test** is a small program that checks that another one gives the right answers, so you notice at once when a change breaks something. With **pytest**, a test is a function whose name starts with `test_` and checks results with `assert`, which stops with an error if its condition is false. Save as `test_geometry.py`:

```python
from geometry import Point, translate


def test_translate_moves_along_z():
    assert translate(Point(1.0, 2.0, 0.0), [0.0, 0.0, 3.0]) == Point(1.0, 2.0, 3.0)
```

```shell
uv run pytest                      # 1 passed
```

pytest finds every `test_*.py` file and runs every `test_*` function in it. Change `3.0` to `4.0` in the test and run it again to see what a failure looks like. Run the tests before you change something, and again after.

## Type checks

```shell
uv run mypy geometry.py            # Success: no issues found in 1 source file
```

**mypy** reads the type hints and reports calls that don't match them, such as `translate("a", 3)`, before the program ever runs.

## What you learned

- Install Python with uv, never into Ubuntu's own Python.
- Values have types; lists, dictionaries, `for`, `if` and functions are most of a program.
- Read a traceback from its last line.
- A project has a `pyproject.toml`, a `uv.lock` and a `.venv`; `uv add` adds packages and `uv run` runs anything inside it.
- pytest runs tests; mypy checks type hints.
