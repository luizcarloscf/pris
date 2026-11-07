import cv2
import numpy as np
import pytest
from turbojpeg import TurboJPEG

from pris_msgs.image_pb2 import Image, ImageFormats
from pris_msgs.utils.image import to_array, to_image


def pixels(gray=False):
    """A smooth 32x48 picture: lossy formats keep it close."""
    rows, cols = np.mgrid[0:32, 0:48]
    gray_pixels = (rows * 4 + cols * 2).astype(np.uint8)
    if gray:
        return gray_pixels
    return np.dstack([gray_pixels, 255 - gray_pixels, np.full_like(gray_pixels, 90)])


@pytest.mark.parametrize("gray", [False, True])
def test_png_round_trip_is_exact(gray):
    array = pixels(gray)
    np.testing.assert_array_equal(to_array(to_image(array, ImageFormats.PNG), gray=gray), array)


@pytest.mark.parametrize("image_format", [ImageFormats.JPEG, ImageFormats.WebP])
@pytest.mark.parametrize("gray", [False, True])
def test_lossy_round_trip_is_close(image_format, gray):
    array = pixels(gray)
    back = to_array(to_image(array, image_format, compression=0.95), gray=gray)
    assert back.shape == array.shape
    assert np.abs(back.astype(int) - array).mean() < 3


def test_compression_follows_the_format():
    small = to_image(pixels(), ImageFormats.JPEG, compression=0.1)
    large = to_image(pixels(), ImageFormats.JPEG, compression=1.0)
    assert len(small.data) < len(large.data)


@pytest.mark.parametrize("gray", [False, True])
def test_turbojpeg_round_trip(gray):
    try:
        TurboJPEG()
    except RuntimeError:
        pytest.skip("libturbojpeg is not installed")
    array = pixels(gray)
    image = to_image(array, ImageFormats.JPEG, compression=0.95, turbojpeg=True)
    back = to_array(image, gray=gray, turbojpeg=True)
    assert back.shape == array.shape
    assert np.abs(back.astype(int) - array).mean() < 3


@pytest.mark.parametrize("image, error", [
    (Image(), cv2.error),
    (Image(uri="http://camera/frame.jpeg"), cv2.error),
    (Image(data=b"not an image"), ValueError),
])
def test_to_array_errors(image, error):
    with pytest.raises(error):
        to_array(image)


@pytest.mark.parametrize("compression", [-0.1, 1.1])
def test_compression_out_of_range(compression):
    with pytest.raises(ValueError, match="between 0 and 1"):
        to_image(pixels(), ImageFormats.JPEG, compression=compression)


def test_unknown_format():
    with pytest.raises(ValueError, match="unknown image format"):
        to_image(pixels(), 7)
