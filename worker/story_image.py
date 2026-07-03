"""Generates a 1080x1920 JPEG Instagram Story image for a single product.

Instagram Stories published via the Graph API cannot carry a clickable link
sticker (that's an app-only feature), so every image ends with a "link na
bio" call to action instead of a swipe-up link.
"""

import io
import logging
import textwrap

import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

CANVAS_SIZE = (1080, 1920)
BACKGROUND_COLOR = (238, 77, 45)  # Shopee-ish orange
TEXT_COLOR = (255, 255, 255)
PRODUCT_IMAGE_BOX = (80, 320, 1000, 1240)  # left, top, right, bottom

# Common DejaVu font locations on Ubuntu (the GitHub Actions runner image
# ships fonts-dejavu-core preinstalled). Falls back to Pillow's tiny default
# bitmap font if none of these exist, so the pipeline never hard-fails on
# missing fonts — it just looks worse until one of these paths is fixed.
FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
FONT_CANDIDATES_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    logger.warning("No TrueType font found, falling back to Pillow's default bitmap font")
    return ImageFont.load_default()


def _fetch_product_image(image_url: str) -> Image.Image:
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGB")


def _fit_into_box(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    box_w, box_h = box[2] - box[0], box[3] - box[1]
    image_ratio = image.width / image.height
    box_ratio = box_w / box_h

    if image_ratio > box_ratio:
        new_height = box_h
        new_width = int(new_height * image_ratio)
    else:
        new_width = box_w
        new_height = int(new_width / image_ratio)

    resized = image.resize((new_width, new_height))
    left = (new_width - box_w) // 2
    top = (new_height - box_h) // 2
    return resized.crop((left, top, left + box_w, top + box_h))


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    center_x: int,
    top_y: int,
    max_width: int,
    line_spacing: int = 10,
) -> int:
    """Draws centered, wrapped text; returns the y coordinate after the block."""
    avg_char_width = font.getbbox("x")[2] or 10
    wrap_width = max(10, max_width // avg_char_width)
    lines = textwrap.wrap(text, width=wrap_width)[:3]

    y = top_y
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        draw.text((center_x - line_width / 2, y), line, font=font, fill=TEXT_COLOR)
        y += line_height + line_spacing

    return y


def generate_story_image(product: dict, output_path: str) -> str:
    canvas = Image.new("RGB", CANVAS_SIZE, BACKGROUND_COLOR)
    draw = ImageDraw.Draw(canvas)

    try:
        product_image = _fetch_product_image(product["image_url"])
        fitted = _fit_into_box(product_image, PRODUCT_IMAGE_BOX)
        canvas.paste(fitted, (PRODUCT_IMAGE_BOX[0], PRODUCT_IMAGE_BOX[1]))
    except Exception:
        logger.exception("Could not load product image for %s", product.get("id"))

    name_font = _load_font(FONT_CANDIDATES_BOLD, 56)
    price_font = _load_font(FONT_CANDIDATES_BOLD, 84)
    cta_font = _load_font(FONT_CANDIDATES_REGULAR, 48)

    _draw_wrapped_text(
        draw,
        product.get("name", ""),
        name_font,
        center_x=CANVAS_SIZE[0] // 2,
        top_y=1290,
        max_width=920,
    )

    price = product.get("price")
    if price:
        price_text = price if isinstance(price, str) else f"R$ {price}"
        bbox = draw.textbbox((0, 0), price_text, font=price_font)
        price_width = bbox[2] - bbox[0]
        draw.text(
            ((CANVAS_SIZE[0] - price_width) / 2, 1520),
            price_text,
            font=price_font,
            fill=TEXT_COLOR,
        )

    cta_text = "Arraste para cima ou veja o link na bio ↑"
    bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
    cta_width = bbox[2] - bbox[0]
    draw.text(
        ((CANVAS_SIZE[0] - cta_width) / 2, 1750),
        cta_text,
        font=cta_font,
        fill=TEXT_COLOR,
    )

    canvas.save(output_path, "JPEG", quality=90)
    return output_path
