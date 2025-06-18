from PIL import Image
import base64
from io import BytesIO
import logging


def process_image(base64_image_str, output_size, output_format=None):
    """
    Process a base64 encoded image by resizing if necessary and optionally
    converting format.

    The image is only resized if any dimension exceeds the specified
    output_size.
    Aspect ratio is always maintained during resizing.

    :param base64_image_str: Base64 encoded image string
    :param output_size: Maximum size (width, height) for the output image
    :param output_format: Optional format to convert the image to
                         (e.g., 'PNG', 'JPEG')
                         If None, the original format is preserved
    :return: Processed image or original image object in case of an error
    """
    # Log input parameters for debugging
    logging.info(f'Requested output_size: {output_size}')
    logging.info(f'Requested output_format: {output_format}')

    try:
        # Decode base64 string to image
        image_data = base64.b64decode(base64_image_str)
        image = Image.open(BytesIO(image_data))

        width, height = image.size
        original_format = image.format
        logging.info(f'Original size - width: {width}, height: {height}')
        logging.info(f'Original format: {original_format}')

        # Determine if resizing is needed
        needs_resize = (width > output_size[0] or
                        height > output_size[1])

        # Determine output format
        target_format = output_format if output_format else original_format

        # Process the image
        if needs_resize:
            logging.info("Image needs resizing (maintaining aspect ratio).")
            image.thumbnail(output_size)
        else:
            logging.info("Image dimensions are within limits, no resizing "
                         "needed.")

        # Prepare the output
        img_processed = image
        output_buffer = BytesIO()

        # Save with the appropriate format
        img_processed.save(output_buffer, format=target_format)
        output_buffer.seek(0)

        final_image = Image.open(output_buffer)
        logging.info(
            f'Final size - width: {final_image.width}, '
            f'height: {final_image.height}'
        )
        logging.info(f'Final image format: {final_image.format}')

        return final_image

    except Exception:
        logging.exception("Image processing error")
        raise
