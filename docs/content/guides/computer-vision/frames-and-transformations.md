# Frames and transformations

To say where something is, you need a reference: "2 m from the door, 1 m from the left wall, on the floor". That reference is a **frame**: an origin, the point from which you measure, and three **axes**, the directions you measure along. The numbers, `(2, 1, 0)`, are the point's **coordinates** in that frame. A space with cameras and robots has many frames, the room's, each camera's, each robot's, and the same table corner has different coordinates in each: `(2, 1, 0)` in the room, `(3, -1, -3)` in a camera. Most code that deals with cameras moves points from one frame to another. This guide builds that code with NumPy, in a project that runs on a fresh Ubuntu install, after [Python](../basics/python.md).

!!! info "To learn more"

    - [Rigid transformation](https://en.wikipedia.org/wiki/Rigid_transformation), [rotation matrix](https://en.wikipedia.org/wiki/Rotation_matrix) and [homogeneous coordinates](https://en.wikipedia.org/wiki/Homogeneous_coordinates);
    - [Modern Robotics](https://hades.mech.northwestern.edu/index.php/Modern_Robotics), chapter 3: rigid-body motions, with free book and videos;
    - [tf2 concepts](https://docs.ros.org/en/humble/Concepts/Intermediate/About-Tf2.html): how ROS keeps a tree of frames.

## Setting up

```shell
mkdir frames && cd frames
uv init --bare --python 3.12
uv add numpy
uv add --dev pytest
```

## Axes and angles

The three axes are called x, y and z, and they are perpendicular to each other. Their directions follow the **right-hand rule**: point your right hand's thumb along x and your index finger along y, and your middle finger, bent towards you, points along z. In a room, a common choice is x and y along the floor and z up.

Angles in code are almost always in **radians**, not degrees: a full turn is 2π radians, so 180° is π (about 3.14) and 90° is π/2. NumPy converts: `np.radians(90)` is 1.5708 and `np.degrees(np.pi / 2)` is 90. A rotation by a positive angle about an axis turns counterclockwise, seen from the tip of that axis looking back at the origin.

## Vectors and matrices

A **vector** is a list of numbers, such as a point's coordinates `[x, y, z]`. A **matrix** is a table of numbers, in rows and columns. NumPy holds both as **arrays**. Save as `vectors.py` and run it with `uv run vectors.py`:

```python
import numpy as np

point = np.array([1.0, 2.0, 3.0])              # a vector: x, y, z
offset = np.array([0.5, 0.0, -1.0])
print(point + offset)                          # [1.5 2.  2. ]
print(2 * point)                               # [2. 4. 6.]
print(np.linalg.norm(point - offset))          # the distance between them

M = np.array([[1.0, 0.0, 0.0],
              [0.0, 2.0, 0.0],
              [0.0, 0.0, 3.0]])
print(M @ point)                               # [1. 4. 9.]
print(M[1], M[:, 2], M.shape)                  # a row, a column, the size
print(np.radians(90), np.degrees(np.pi / 2))
```

- Adding vectors adds their numbers one by one; multiplying by a number scales each one. `np.linalg.norm` is a vector's length, so the norm of a difference is the distance between two points: 4.5 here.
- `M @ point` multiplies a matrix by a vector: each number of the result is a row of `M` times the vector, number by number, added up. The first row, `[1, 0, 0]`, gives 1·1 + 0·2 + 0·3 = 1; the second, `[0, 2, 0]`, gives 2·2 = 4; the third gives 3·3 = 9. Multiplying two matrices does the same with each column of the second.
- `M[1]` is a row (counting from 0), `M[:, 2]` a column (`:` means "all rows"), `M.shape` the size, rows by columns.

That is all the algebra this guide needs: everything else is matrices multiplying vectors and other matrices.

## Rotations

A **rotation** turns points about the origin, without stretching them. It is a 3×3 matrix `R`: multiplying a point by it, `R @ p`, gives the turned point. Its columns are where the three axes end up. Rotating 90° about z takes the x axis to where the y axis was:

```python
import numpy as np


def rotation_z(angle: float) -> np.ndarray:
    """Return the 3x3 rotation of `angle` radians about the z axis."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


R = rotation_z(np.radians(90))
print(np.round(R @ [1.0, 0.0, 0.0], 3))                              # [0. 1. 0.]
print(np.allclose(R.T @ R, np.eye(3)), round(np.linalg.det(R), 3))   # True 1.0
```

The matrix uses the cosine and sine of the angle: for a turn about z, x and y change and z stays. Two facts about every rotation are worth remembering, and the last line checks them:

- `R.T`, its **transpose** (rows and columns swapped), is its **inverse**: `R.T @ R` is the identity, the matrix that changes nothing, `np.eye(3)`. So undoing a rotation is just using its transpose.
- Its **determinant**, `np.linalg.det`, is 1: it neither stretches nor mirrors.

`np.allclose` compares arrays allowing for tiny rounding errors, which computers always make with decimals; never compare decimal numbers with `==`.

## Rigid transformations

Moving an object around a room rotates it and then shifts it, a **translation**, without bending it: a **rigid transformation**, `p' = R p + t`, where `t` is the shift. It is convenient to write both as one 4×4 matrix, and each point with a 1 added, `[x, y, z, 1]` (its **homogeneous coordinates**). Then the whole transformation is a single multiplication:

```
⎡ R  t ⎤ ⎡ p ⎤   ⎡ R p + t ⎤
⎣ 0  1 ⎦ ⎣ 1 ⎦ = ⎣    1    ⎦
```

The top-left 3×3 block is the rotation, the last column the translation, and the bottom row is always `0 0 0 1`. Save these functions as `frames.py`; the rest of this guide and the next ones use them:

```python
import numpy as np


def rotation_z(angle: float) -> np.ndarray:
    """Return the 3x3 rotation of `angle` radians about the z axis."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def transform(rotation: np.ndarray, translation: list[float]) -> np.ndarray:
    """Return the 4x4 rigid transformation [R t; 0 1]."""
    matrix = np.eye(4)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = translation
    return matrix


def invert(matrix: np.ndarray) -> np.ndarray:
    """Return the inverse of a rigid transformation: [R^T -R^T t; 0 1]."""
    rotation, translation = matrix[:3, :3], matrix[:3, 3]
    return transform(rotation.T, -rotation.T @ translation)


def apply(matrix: np.ndarray, point: list[float]) -> np.ndarray:
    """Return a 3D point transformed by a 4x4 matrix."""
    return (matrix @ np.append(point, 1.0))[:3]
```

- `transform` starts from the 4×4 identity and writes the rotation into its top-left block, `[:3, :3]` (rows 0 to 2, columns 0 to 2), and the translation into its last column, `[:3, 3]`.
- `invert` undoes a transformation. Undoing "rotate by R, then shift by t" is "shift back by t, then rotate back by `R.T`", which works out to the rotation `R.T` and the translation `-R.T @ t`.
- `apply` adds the 1 to a point, `np.append(point, 1.0)`, multiplies, and drops the 1 again, `[:3]`.

## Naming transformations

The hard part isn't the arithmetic: it is knowing which way a matrix goes. Name every matrix after what it does: **`a_to_b` takes coordinates in frame `a` and gives coordinates in frame `b`**. The same matrix is also the **pose of `a` in `b`**, where `a` is and how it is turned, seen from `b`: its last column is `a`'s origin in `b`'s coordinates, and its rotation's columns are `a`'s axes.

Write the examples from here on in one file, `demo.py`, next to `frames.py`, and run it with `uv run demo.py`. A robot stands at `(2, 1, 0)` in the room, turned 90° to its left. A point 1 m ahead of the robot is, in the room:

```python
import numpy as np

from frames import apply, invert, rotation_z, transform

robot_to_world = transform(rotation_z(np.radians(90)), [2.0, 1.0, 0.0])
print(apply(robot_to_world, [1.0, 0.0, 0.0]).round(3))      # [2. 2. 0.]
```

"Ahead" is the robot's x axis, `[1, 0, 0]` in the robot's frame. The robot is turned 90°, so its x axis points along the room's y: 1 m ahead of `(2, 1, 0)` is `(2, 2, 0)`.

## Composing and inverting

With this naming, transformations chain like their names: `b_to_c @ a_to_b` is `a_to_c`, read right to left (first `a_to_b`, then `b_to_c`). Inverting swaps the names: `invert(a_to_b)` is `b_to_a`.

A camera hangs at `(5, 0, 3)`, turned 180°, so its pose in the room is `camera_to_world`. Where is the robot, seen from the camera?

```python
camera_to_world = transform(rotation_z(np.radians(180)), [5.0, 0.0, 3.0])
world_to_camera = invert(camera_to_world)
robot_to_camera = world_to_camera @ robot_to_world
print(apply(robot_to_camera, [0.0, 0.0, 0.0]).round(3))     # [ 3. -1. -3.]
```

We have `robot_to_world` and need `robot_to_camera`, so we need `world_to_camera` to follow it, which is the inverse of the camera's pose. The inner names meet and cancel, `world_to_camera @ robot_to_world`, which is how you check a product before running it. The robot's origin, `[0, 0, 0]` in its own frame, is 3 m along the camera's x axis, 1 m along its negative y and 3 m below it.

`invert` gives the same as NumPy's general inverse, `np.linalg.inv`, but is exact and faster, because it uses the transpose of the rotation:

```python
print(np.allclose(invert(camera_to_world), np.linalg.inv(camera_to_world)))   # True
```

## Order matters

With numbers, 2 × 3 is 3 × 2. With matrices, the order changes the result:

```python
turn = transform(rotation_z(np.radians(90)), [0.0, 0.0, 0.0])
step = transform(np.eye(3), [1.0, 0.0, 0.0])
print(apply(turn @ step, [0, 0, 0]).round(3))   # [0. 1. 0.]: step, then turn
print(apply(step @ turn, [0, 0, 0]).round(3))   # [1. 0. 0.]: turn, then step
```

Step 1 m forward, then turn 90°, and you end up somewhere else than if you turn first and then step: try it in a room. In `turn @ step`, the right-hand matrix acts first.

## A graph of frames

A space has many frames linked by known transformations: each camera to the room, each robot to the room, a gripper to its robot. Draw them as dots linked by lines and you get a **graph**. The transformation between any two frames is the product along the path between them, inverting each link walked backwards. From a gripper to a camera: `gripper_to_camera = world_to_camera @ robot_to_world @ gripper_to_robot`. Libraries such as tf2, in the robotics framework ROS, keep this graph and do the products for you.

## Testing

Two properties catch most mistakes: undoing a transformation gives the point back, and composing matches applying one after the other. Save them as `test_frames.py` and run `uv run pytest` (see [Python](../basics/python.md#tests)):

```python
import numpy as np

from frames import apply, invert, rotation_z, transform


def test_invert_undoes_a_transformation():
    a_to_b = transform(rotation_z(0.7), [1.0, -2.0, 0.5])
    point = [0.3, 0.2, 0.1]
    assert np.allclose(apply(invert(a_to_b), apply(a_to_b, point)), point)


def test_composition_follows_the_names():
    a_to_b = transform(rotation_z(0.3), [1.0, 0.0, 0.0])
    b_to_c = transform(rotation_z(-1.1), [0.0, 2.0, 0.0])
    point = [0.5, 0.5, 0.5]
    assert np.allclose(apply(b_to_c @ a_to_b, point), apply(b_to_c, apply(a_to_b, point)))
```

## Common mistakes

| Symptom | Likely cause |
|---|---|
| a point lands far from where it should | the inverse of the matrix you needed: check its name, `a_to_b` or `b_to_a` |
| right position, wrong orientation | a product in the wrong order |
| errors of a few hundred meters, or wild rotations | degrees where radians were expected |
| the translation is ignored | the point without its `1`, or `R @ p` without `+ t` |
| `R.T @ R` drifts from the identity after many products | rounding: rebuild the rotation from an angle, or re-orthonormalize it |

## What you learned

- A frame is an origin and three axes; coordinates only mean something in a frame.
- A rotation is a 3×3 matrix whose transpose undoes it; a rigid transformation is a 4×4 matrix `[R t; 0 1]` acting on `[x, y, z, 1]`.
- Name matrices `a_to_b`: they chain like their names and invert by swapping them.
- Matrix products don't commute: the right-hand one acts first.
