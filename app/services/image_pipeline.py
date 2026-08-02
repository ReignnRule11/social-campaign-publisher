from PIL import Image


def resize_image(src_path: str, dest_path: str, size: tuple):
    """Simple resize pipeline: open, resize (LANCZOS), save."""
    img = Image.open(src_path).convert("RGB")
    img = img.resize(size, Image.LANCZOS)
    img.save(dest_path, format="JPEG")
