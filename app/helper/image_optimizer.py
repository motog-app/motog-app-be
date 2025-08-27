from PIL import Image, UnidentifiedImageError
import io
import subprocess
import tempfile
import os

async def optimize_image(file, max_size=(1024, 1024), quality=85):
    """
    Optimizes an image by resizing, converting to JPEG, and compressing it.
    Handles HEIC files by converting them to JPEG using the `heif-convert` command-line tool.

    :param file: A file-like object containing the image data.
    :param max_size: A tuple representating the maximum width and height of the image.
    :param quality: An integer representing the quality of the compressed image (1-95).
    :return: A file-like object comtaining the optimized image data.
    """

    img_data = await file.read()

    # Use a temporary file to store the uploaded image
    with tempfile.NamedTemporaryFile(delete=False) as temp_in:
        temp_in.write(img_data)
        temp_in_path = temp_in.name

    # Use a temporary file for the output JPEG
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_out:
        temp_out_path = temp_out.name

    try:
        # Try to convert with heif-convert. This will work for HEIC/HEIF.
        # If it's not a HEIC file, heif-convert will fail, and we'll fall back to Pillow.
        subprocess.run(['heif-convert', temp_in_path, temp_out_path], check=True, capture_output=True)
        image = Image.open(temp_out_path)
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If heif-convert fails, try to open with Pillow directly.
        try:
            image = Image.open(io.BytesIO(img_data))
        except UnidentifiedImageError:
            return {"error": "Cannot identify image file"}
    finally:
        # Clean up the temporary files
        os.unlink(temp_in_path)
        if os.path.exists(temp_out_path):
            os.unlink(temp_out_path)


    # Resize the image
    image.thumbnail(max_size)

    # Convert to RGB if it has an alpha channel
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Save the optimize image to a byte stream as JPEG
    optimize_image_io = io.BytesIO()
    image.save(optimize_image_io, format='JPEG', quality=quality)
    optimize_image_io.seek(0)

    return optimize_image_io