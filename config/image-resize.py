from PIL import Image
import base64
from io import BytesIO
import logging


def resize_image(base64_image_str, size, maintain_aspect_ratio=False):
    """
    Resize a base64 encoded image to the specified size.

    :param base64_image_str: Base64 encoded image string
    :param size: Tuple (width, height) specifying the new size
    :return: resized image or original image object in case of an error
    """
    try:
        # Decode base64 string to image
        image_data = base64.b64decode(base64_image_str)
        image = Image.open(BytesIO(image_data))

        width, height = image.size
        format = image.format
        logging.info(f'Original size - width: {width}, height: {height}')
        logging.info(f'Original format: {format}')

        # Check if the image is a GIF and convert to PNG
        if image.format == "GIF":
            logging.info("Image is a GIF. Converting to PNG.")
            image = image.convert("RGBA")

        if maintain_aspect_ratio:
            logging.info("Resizing image maintaining aspect ratio.")
            image.thumbnail(size)
        else:
            logging.info("Resizing image without maintaining aspect ratio.")
            image = image.resize(size)

        img_resized = image

        output_buffer = BytesIO()
        img_resized.save(output_buffer, format="PNG")
        output_buffer.seek(0)

        img_resized_png = Image.open(output_buffer)
        logging.info(
            f'New size - width: {img_resized_png.width}, '
            f'height: {img_resized_png.height}'
        )
        logging.info(f'New image format: {img_resized_png.format}')

        return img_resized_png

    except Exception as e:
        logging.info(f"Returning original Image as an error occurred: {e}")
        return image
