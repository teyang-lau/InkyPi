from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageOps, ImageFilter
from io import BytesIO
import logging
import os
import requests
import random
from datetime import datetime

logger = logging.getLogger(__name__)

def list_files_in_folder(folder_path):
    """Return a list of image file paths in the given folder, excluding hidden files."""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    return [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if (
            os.path.isfile(os.path.join(folder_path, f))
            and f.lower().endswith(image_extensions)
            and not f.startswith('.')
        )
    ]

def grab_image(image_path, dimensions, pad_image):
    """Load an image from disk, auto-orient it, and resize to fit within the specified dimensions, preserving aspect ratio."""
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)  # Correct orientation using EXIF
        img = ImageOps.contain(img, dimensions, Image.LANCZOS)

        if pad_image:
            bkg = ImageOps.fit(img, dimensions)
            bkg = bkg.filter(ImageFilter.BoxBlur(8))
            img_size = img.size
            bkg.paste(img, ((dimensions[0] - img_size[0]) // 2, (dimensions[1] - img_size[1]) // 2))
            img = bkg
        return img
    except Exception as e:
        logger.error(f"Error loading image from {image_path}: {e}")
        return None

class ImageFolderByDay(BasePlugin):
    def generate_image(self, settings, device_config):
        folder_path = settings.get('folder_path')
        pad_image = settings.get('padImage', False)
        if not folder_path:
            raise RuntimeError("Folder path is required.")
        
        if not os.path.exists(folder_path):
            raise RuntimeError(f"Folder does not exist: {folder_path}")
        
        if not os.path.isdir(folder_path):
            raise RuntimeError(f"Path is not a directory: {folder_path}")

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]

        logger.info(f"Grabbing an image for today from: {folder_path}")

        image_files = list_files_in_folder(folder_path)
        if not image_files:
            raise RuntimeError(f"No image files found in folder: {folder_path}")

        # Get the current day of the month (1-31)
        current_day = datetime.now()
        current_hour, day_of_month = current_day.hour, current_day.day
        morning_afternoon = "morning" if current_hour < 12 else "afternoon"
        if current_day.weekday() >= 5: # skip if today is weekend
            raise RuntimeError("Today is a weekend, skipping image selection.")
        today_image_file = f"{day_of_month}_{morning_afternoon}.png"
        image_url = [f for f in image_files if today_image_file in f][0]
        logger.info(f"Image selected for day {day_of_month} {morning_afternoon}: {image_url}")

        image = grab_image(image_url, dimensions, pad_image)

        if not image:
            raise RuntimeError("Failed to load image, please check logs.")

        return image
