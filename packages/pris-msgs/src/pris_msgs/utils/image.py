"""Convert pris.vision.Image to and from NumPy arrays. Needs pris-msgs[opencv]."""

from __future__ import annotations

import functools
from typing import cast

try:
    import cv2
    import numpy as np
    import numpy.typing as npt
except ImportError as error:  # pragma: no cover
    raise ImportError("pris_msgs.utils.image needs OpenCV: install pris-msgs[opencv]") from error

try:
    import turbojpeg as _tj
except ImportError:  # pragma: no cover
    _tj = None  # type: ignore[assignment]

from pris_msgs.image_pb2 import Image, ImageFormats

_JPEG_START = b"\xff\xd8"


def to_array(
    image: Image,
    gray: bool = False,
    turbojpeg: bool = False,
) -> npt.NDArray[np.uint8]:
    """Decode an image.

    Args:
        image: an image with encoded `data` (JPEG, PNG, WebP, ...).
        gray: decode to gray pixels instead of BGR.
        turbojpeg: decode JPEG with libjpeg-turbo (needs pris-msgs[turbojpeg] and the system
            libturbojpeg); other formats always use OpenCV.

    Returns:
        A new uint8 array, (rows, cols, 3) BGR or (rows, cols) gray.

    Raises:
        ValueError: the data can't be decoded.
        cv2.error: the image has no `data` (it is empty or has a `uri`).
        OSError: libjpeg-turbo fails.
    """
    if turbojpeg and image.data.startswith(_JPEG_START):
        pixels = _turbojpeg().decode(
            jpeg_buf=image.data,
            pixel_format=_tj.TJPF_GRAY if gray else _tj.TJPF_BGR,
        )
        return pixels[:, :, 0] if gray else pixels
    flags = cv2.IMREAD_GRAYSCALE if gray else cv2.IMREAD_COLOR
    pixels = cv2.imdecode(
        np.frombuffer(
            buffer=image.data,
            dtype=np.uint8,
        ),
        flags,
    )
    if pixels is None:
        raise ValueError("image data could not be decoded")
    return cast(npt.NDArray[np.uint8], pixels)


def to_image(
    array: npt.NDArray[np.uint8],
    image_format: ImageFormats = ImageFormats.JPEG,
    compression: float = 0.8,
    turbojpeg: bool = False,
) -> Image:
    """Encode an array as an image.

    Args:
        array: uint8 pixels, (rows, cols, 3) BGR or (rows, cols) gray.
        image_format: JPEG, PNG or WebP.
        compression: from 0 to 1, the quality for JPEG and WebP, the effort for PNG.
        turbojpeg: encode JPEG with libjpeg-turbo, with 4:2:2 chroma subsampling for color.

    Returns:
        An image with the encoded `data`.

    Raises:
        ValueError: `compression` is outside [0, 1], the format is unknown, or nothing was
            encoded.
        cv2.error: OpenCV refuses the array.
        OSError: libjpeg-turbo fails.
    """
    if not 0 <= compression <= 1:
        raise ValueError(f"compression {compression} is not between 0 and 1")
    if image_format == ImageFormats.JPEG:
        if turbojpeg:
            gray = array.ndim == 2
            data = _turbojpeg().encode(
                img_array=array,
                quality=int(compression * 100),
                pixel_format=_tj.TJPF_GRAY if gray else _tj.TJPF_BGR,
                jpeg_subsample=_tj.TJSAMP_GRAY if gray else _tj.TJSAMP_422,
            )
            return Image(data=data)
        extension, params = ".jpeg", [cv2.IMWRITE_JPEG_QUALITY, int(compression * 100)]
    elif image_format == ImageFormats.PNG:
        extension, params = ".png", [cv2.IMWRITE_PNG_COMPRESSION, int(compression * 9)]
    elif image_format == ImageFormats.WebP:
        extension, params = ".webp", [cv2.IMWRITE_WEBP_QUALITY, int(compression * 99 + 1)]
    else:
        raise ValueError(f"unknown image format {image_format}")
    ok, data = cv2.imencode(extension, array, params)
    if not ok:
        raise ValueError("array could not be encoded")
    return Image(data=data.tobytes())


@functools.cache
def _turbojpeg() -> _tj.TurboJPEG:
    """The shared TurboJPEG instance."""
    if _tj is None:
        raise ImportError("turbojpeg=True needs PyTurboJPEG: install pris-msgs[turbojpeg]")
    return _tj.TurboJPEG()
