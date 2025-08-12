from PIL import Image, GifImagePlugin
import base64
from io import BytesIO
import logging
import math
from typing import Optional, Literal


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

        if original_format == 'GIF':
            logging.info("Converting GIF into a collage.")
            image = gif_to_collage(image, max_frames=9)

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


def gif_to_collage(
    gif: Image.Image,
    max_frames: Optional[int] = None,
    grid_cols: Optional[int] = None,
    sample_method: Literal['interval', 'sequential'] = 'interval'
) -> Image.Image:
    """
    Convert a GIF to a PNG collage showing multiple frames.

    Args:
        gif: original GIF Image object
        max_frames: Maximum number of frames to include (None = all frames)
        grid_cols: Number of columns in grid
            (None = auto-calculate square-ish grid)
        sample_method: 'interval' (evenly spaced)
            or 'sequential' (first N frames)
    Returns:
        Collage Image object in RGB mode
    """

    # Set loading strategy for consistent RGB mode
    GifImagePlugin.LOADING_STRATEGY = GifImagePlugin.LoadingStrategy.RGB_ALWAYS

    # First pass: count total frames
    total_frames = 0
    try:
        while True:
            gif.seek(total_frames)
            total_frames += 1
    except EOFError:
        pass

    logging.info(f"Total frames in GIF: {total_frames}")

    # Determine which frames to extract
    if max_frames is None or max_frames >= total_frames:
        frame_indices = list(range(total_frames))
    elif sample_method == 'interval':
        # Sample frames at equal intervals across the entire GIF
        if max_frames == 1:
            frame_indices = [total_frames // 2]  # Middle frame
        else:
            # Calculate interval to spread frames evenly
            interval = (total_frames - 1) / (max_frames - 1)
            frame_indices = [round(i * interval) for i in range(max_frames)]
            # Ensure we don't exceed bounds and remove duplicates
            frame_indices = sorted(
                list(
                    set([min(idx, total_frames - 1) for idx in frame_indices])
                    )
            )
    else:  # sequential
        frame_indices = list(range(min(max_frames, total_frames)))

    logging.info(f"Extracting frames at indices: {frame_indices}")

    # Second pass: extract the selected frames
    frames = []
    for frame_idx in frame_indices:
        gif.seek(frame_idx)
        frame = gif.convert('RGB')
        frames.append(frame.copy())

    if not frames:
        raise ValueError("No frames found in GIF")

    # Calculate grid dimensions
    total_frames = len(frames)
    if grid_cols is None:
        grid_cols = math.ceil(math.sqrt(total_frames))
    grid_rows = math.ceil(total_frames / grid_cols)

    # Get frame dimensions
    frame_width, frame_height = frames[0].size

    # Create collage canvas
    collage_width = frame_width * grid_cols
    collage_height = frame_height * grid_rows
    collage = Image.new('RGB', (collage_width, collage_height), 'white')

    # Paste frames into grid
    for i, frame in enumerate(frames):
        row = i // grid_cols
        col = i % grid_cols
        x = col * frame_width
        y = row * frame_height
        collage.paste(frame, (x, y))

    logging.info(f"Converted GIG into a collage of {len(frames)} frames")
    return collage
