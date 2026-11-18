# Camera model and calibration

A camera turns the 3D world into a flat image. To measure anything with it, where an object is or how big, you need to know exactly how it does that: which point of the world lands on which pixel. The **pinhole model** describes it with a few numbers. Some are inside the camera, the **intrinsics**: how strong the lens is and where its center falls on the image. Others are where the camera is, the **extrinsics**. **Calibration** finds them, from photos of a pattern whose size you know. This guide builds both with NumPy and OpenCV, a library of computer vision, on a fresh Ubuntu install. It follows [Frames and transformations](frames-and-transformations.md), whose `frames.py` it reuses.

!!! info "To learn more"

    - [Pinhole camera model](https://en.wikipedia.org/wiki/Pinhole_camera_model) and [Perspective-n-Point](https://en.wikipedia.org/wiki/Perspective-n-Point);
    - [Camera calibration with OpenCV](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html): the tutorial this guide follows, and the [calib3d reference](https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html);
    - [Computer Vision: Algorithms and Applications](https://szeliski.org/Book/), by Richard Szeliski, chapter 2 (image formation) and 11 (calibration), free online.

## Setting up

In the folder of the previous guide, with its `frames.py`:

```shell
uv add numpy opencv-python-headless
```

`opencv-python-headless` is OpenCV without its windows: everything here writes image files instead of showing them, which also works on computers without a screen.

## Images and pixels

A digital image is a grid of **pixels**, small squares each with one color, or one brightness for a gray image. An image 1280 pixels wide and 720 high is 1280 × 720. A pixel's position is two numbers: `u`, counted from the left edge towards the right, and `v`, from the top edge downwards. The top-left pixel is `(0, 0)`. Positions can have decimals too: `(640.5, 360.2)` is a point inside a pixel, which careful measurements need.

## The camera frame

A camera has its own frame (see [Frames and transformations](frames-and-transformations.md)), with its origin at the center of the lens. OpenCV's convention, used everywhere in computer vision:

- **z points forward**, out of the lens, towards what the camera sees: a point in front of the camera has a positive z, its distance along the view;
- **x points to the right** of the image;
- **y points down**, like the image's `v`.

## Intrinsics

In a pinhole camera, light from a point goes in a straight line through one hole, the center of the lens, and hits the sensor behind it. Things twice as far look half as big, so where a point lands depends on its sideways position divided by its distance: `X / Z` and `Y / Z`. Then the camera scales that into pixels and shifts it to the image's center:

```
u = fx · X / Z + cx          ⎡ fx  0  cx ⎤
v = fy · Y / Z + cy      K = ⎢  0 fy  cy ⎥
                             ⎣  0  0   1 ⎦
```

- `fx` and `fy` are the **focal length**, in pixels: how many pixels a point moves for each unit of `X / Z`. A larger focal length is a zoom: a narrower view, bigger objects. They are usually nearly equal.
- `(cx, cy)` is the **principal point**, where the lens' axis meets the image, near its center.
- The five numbers make the **camera matrix** `K`. Multiplying `K` by a point `[X, Y, Z]` gives `[fx·X + cx·Z, fy·Y + cy·Z, Z]`; dividing the first two by the third gives exactly `u` and `v`.

Save as `project.py` and run it with `uv run project.py`:

```python
import cv2
import numpy as np

K = np.array([[800.0, 0.0, 640.0],
              [0.0, 800.0, 360.0],
              [0.0, 0.0, 1.0]])               # a 1280 x 720 camera
point = np.array([0.1, -0.05, 2.0])          # in the camera frame, in meters

u, v, w = K @ point
print(u / w, v / w)                          # 680.0 340.0

pixels, _ = cv2.projectPoints(point.reshape(1, 3), np.zeros(3), np.zeros(3), K, None)
print(pixels.ravel())                        # [680. 340.]
```

A point 2 m in front of the camera, 10 cm to the right and 5 cm up (negative y, since y points down), lands 40 pixels right of the center and 20 pixels above it. **Projecting** a point is turning it into its pixel. OpenCV's `cv2.projectPoints` does it too, for many points at once: its second and third arguments are a rotation and a translation, from the points' frame to the camera's, here zero because the point is already in the camera's frame; its last argument is the distortion, next.

## Distortion

Real lenses aren't perfect pinholes: they bend straight lines, more and more towards the edges of the image. **Radial** distortion makes the image bulge like a barrel, or pinch in like a pincushion; **tangential** distortion comes from a lens not quite parallel to the sensor. OpenCV describes them with five numbers, `k1, k2, p1, p2, k3`: the `k` for radial, the `p` for tangential. Add to `project.py`:

```python
distortion = np.array([-0.2, 0.05, 0.0, 0.0, 0.0])   # k1, k2, p1, p2, k3
corner = np.array([[0.8, 0.45, 1.0]])                # toward the image's corner
for d in (None, distortion):
    pixels, _ = cv2.projectPoints(corner, np.zeros(3), np.zeros(3), K, d)
    print(pixels.ravel().round(1))                   # [1280. 720.], then [1194.9 672.1]
```

Near the center, a pinhole and a real lens agree; at the corner, this lens moves the point by almost 100 pixels. Ignoring distortion means measuring wrong wherever you look away from the center.

## Extrinsics

A camera usually sees points given in another frame, a room's or an object's. The **extrinsics** are the transformation from that frame to the camera, `world_to_camera` in the naming of the previous guide: a rotation `R` and a translation `t`. The whole camera is then: move the point into the camera's frame, project it, distort it:

```
pixel ~ K · (R · X_world + t)          then the distortion
```

(`~` because of the division by the last number, as above.) OpenCV writes a rotation as a **rotation vector**, three numbers instead of nine: its direction is the axis to turn about and its length the angle, in radians. `cv2.Rodrigues` converts a rotation vector into a 3×3 matrix and back.

## Calibrating

Calibration finds `K` and the distortion, from photos of a **calibration pattern**: an object whose points you know exactly, such as a chessboard with squares of known size. Give the board its own frame, with its origin at a corner, x and y along its edges and z out of it: then its corners are at `(i · side, j · side, 0)`, all known. In each photo, OpenCV finds the corners' pixels. `cv2.calibrateCamera` then looks for the `K`, distortion and board poses that would project the known corners exactly where they were found, in every photo at once.

### A printed board

This script writes `board.png`, a chessboard of 10 × 7 squares. OpenCV looks for its **inner corners**, where four squares meet: 9 × 6 of them. Save as `make_board.py` and run it:

```python
import cv2
import numpy as np

squares_x, squares_y, pixels = 10, 7, 100           # 9 x 6 inner corners
board = np.kron((np.indices((squares_y, squares_x)).sum(axis=0) % 2) * 255,
                np.ones((pixels, pixels))).astype(np.uint8)
board = cv2.copyMakeBorder(board, pixels, pixels, pixels, pixels, cv2.BORDER_CONSTANT, value=255)
cv2.imwrite("board.png", board)
```

`np.indices(...).sum(axis=0) % 2` makes a table of alternating 0 and 1, one per square; `np.kron` blows each number up into a 100 × 100 block of pixels, black or white; `copyMakeBorder` adds a white margin, which helps OpenCV find the board. Print `board.png` at 100% scale, glue it flat to something rigid, such as cardboard, and measure the side of a square with a ruler: 25 mm is used below.

### The photos

Take 15 to 20 photos of the board with the camera you calibrate, saved as `photos/*.png` (a folder `photos`, with PNG files):

- the whole board in every photo, sharp, at different distances;
- tilted in different directions, up to about 45°, not always facing the camera;
- in the center and near the edges and corners of the image, where distortion shows;
- with the camera's settings fixed: the same resolution and focus as when you will use it.

### The calibration

Save as `calibrate.py`:

```python
import glob

import cv2
import numpy as np

columns, rows, square = 9, 6, 0.025                 # inner corners, side in meters
board = np.zeros((rows * columns, 3), np.float32)
board[:, :2] = np.mgrid[0:columns, 0:rows].T.reshape(-1, 2) * square

object_points, image_points = [], []
for path in sorted(glob.glob("photos/*.png")):
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    found, corners = cv2.findChessboardCorners(image, (columns, rows))
    if not found:
        print(path, "board not found")
        continue
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners = cv2.cornerSubPix(image, corners, (11, 11), (-1, -1), criteria)
    object_points.append(board)
    image_points.append(corners)

size = image.shape[::-1]                              # (width, height)
error, K, distortion, rotations, translations = cv2.calibrateCamera(
    object_points, image_points, size, None, None, flags=cv2.CALIB_FIX_K3)
print("views:", len(object_points), "RMS error:", round(error, 3), "px")
print(K.round(1))
print(distortion.ravel().round(3))
np.savez("calibration.npz", K=K, distortion=distortion)
```

- `board` holds the 54 corners in the board's frame: `np.mgrid` makes every pair `(i, j)`, scaled by the square's side, with z left at 0.
- `glob.glob("photos/*.png")` lists the photos; `cv2.imread(..., cv2.IMREAD_GRAYSCALE)` reads each one, in gray, which is all corner detection needs.
- `findChessboardCorners` finds the inner corners, to about a pixel; `cornerSubPix` refines them to a fraction of one, by looking closely at the image around each corner.
- `calibrateCamera` gets, for every photo, the known corners and the found ones. It returns the error, `K`, the distortion, and each photo's board pose.
- `cv2.CALIB_FIX_K3` keeps `k3` at zero: with an ordinary lens, `k2` and `k3` describe almost the same bending, and leaving both free gives unstable values. Leave `k3` free for a wide-angle lens.
- `np.savez` saves the results to `calibration.npz`, for the next steps.

For 15 photos of a 1280 × 720 camera, the output looks like this; these came from synthetic photos, so a real camera's error will be higher:

```
views: 15 RMS error: 0.09 px
[[800.2   0.  640. ]
 [  0.  800.2 361.1]
 [  0.    0.    1. ]]
[-0.2   0.05 -0.    0.    0.  ]
```

### Is it good?

The **RMS reprojection error** is the typical distance, in pixels, between the corners found in the photos and where the calibrated camera would put them (RMS, root mean square, is a kind of average that weighs big errors more). Below about 0.5 px is a good calibration; above 1 px, look for blurred photos, a board that isn't flat, or a wrong square size. A low error doesn't prove everything, though: with photos taken only from the front, a longer focal length and a farther board can explain the same photos, and still fit well. Variety in the photos is what makes the numbers right.

## Where is the camera?

With `K` and the distortion known, a single photo of the board tells where the camera is: `cv2.solvePnP` finds the pose that projects the board's known corners onto the corners found in the photo. PnP is "Perspective-n-Point": the camera's pose from n points. Save as `pose.py`, next to `frames.py`:

```python
import cv2
import numpy as np

from frames import invert

calibration = np.load("calibration.npz")
K, distortion = calibration["K"], calibration["distortion"]

columns, rows, square = 9, 6, 0.025
board = np.zeros((rows * columns, 3), np.float32)
board[:, :2] = np.mgrid[0:columns, 0:rows].T.reshape(-1, 2) * square

image = cv2.imread("photos/00.png", cv2.IMREAD_GRAYSCALE)
found, corners = cv2.findChessboardCorners(image, (columns, rows))
ok, rotation, translation = cv2.solvePnP(board, corners, K, distortion)

board_to_camera = np.eye(4)
board_to_camera[:3, :3], _ = cv2.Rodrigues(rotation)   # rotation vector to 3x3 matrix
board_to_camera[:3, 3] = translation.ravel()
camera_to_board = invert(board_to_camera)
print("camera in board coordinates:", camera_to_board[:3, 3].round(3))

projected, _ = cv2.projectPoints(board, rotation, translation, K, distortion)
errors = np.linalg.norm(projected.reshape(-1, 2) - corners.reshape(-1, 2), axis=1)
print("reprojection error:", errors.mean().round(3), "px")

cv2.imwrite("undistorted.png", cv2.undistort(image, K, distortion))
```

```
camera in board coordinates: [ 0.187  0.091 -0.536]
reprojection error: 0.242 px
```

- `solvePnP` returns the board's pose in the camera as a rotation vector and a translation: put together in a 4×4 matrix, that is `board_to_camera`.
- Its inverse, `camera_to_board`, is the camera's pose in the board's frame; its last column is where the camera is: about 54 cm from the board, on its negative z side, since the board's z axis points away from the camera.
- This is how a camera is placed in a room: put the board where the room's origin should be, and `board_to_camera` is the camera's `world_to_camera`.
- Projecting the corners back with the found pose and comparing with the detected ones gives the reprojection error of this one photo.
- `cv2.undistort` removes the lens distortion from the photo: open `undistorted.png`, and its straight lines are straight again.

OpenCV returns points in different shapes: `(N, 2)`, N rows of two numbers, from one function, and `(N, 1, 2)` from another. Subtracting one from the other gives nonsense without an error, so reshape both to `(N, 2)` first, as above with `.reshape(-1, 2)`.

## What you learned

- An image is a grid of pixels, `u` to the right and `v` down; the camera's frame has z forward, x right and y down.
- The intrinsics `K` divide by depth and turn the result into pixels; the distortion bends it, most at the edges; the extrinsics place the camera.
- Calibration finds `K` and the distortion from varied photos of a chessboard; the reprojection error tells how well it fits.
- With a calibrated camera, `solvePnP` finds its pose from one photo of a known object.
