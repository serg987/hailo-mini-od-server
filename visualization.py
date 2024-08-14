# taken from https://github.com/hailo-ai/Hailo-Application-Code-Examples/blob/main/runtime/python/object_detection/object_detection.py
import numpy as np
from PIL import ImageDraw, ImageFont

IMAGE_EXTENSIONS = ('.jpg', '.png', '.bmp', '.jpeg')
LABEL_FONT = "LiberationSans-Regular.ttf"
PADDING_COLOR = (114, 114, 114)
COLORS = np.random.randint(0, 255, size=(100, 3), dtype=np.uint8)


def draw_detection(labels, draw, box, cls, score, color, scale_factor):
    """
    Draw box and label for one detection.

    Args:
        labels (list): List of class labels.
        draw (ImageDraw.Draw): Draw object to draw on the image.
        box (list): Bounding box coordinates.
        cls (int): Class index.
        score (float): Detection score.
        color (tuple): Color for the bounding box.
        scale_factor (float): Scale factor for coordinates.

    Returns:
        str: Detection label.
    """
    label = f"{labels[cls]}: {score:.2f}%"
    ymin, xmin, ymax, xmax = box
    font = ImageFont.truetype(LABEL_FONT, size=15)
    draw.rectangle([(xmin * scale_factor, ymin * scale_factor), (xmax * scale_factor, ymax * scale_factor)],
                   outline=color, width=2)
    draw.text((xmin * scale_factor + 4, ymin * scale_factor + 4), label, fill=color, font=font)


def visualize(labels, detections, image, image_path, width, height, min_score=0.45, scale_factor=1):
    """
    Visualize detections on the image.

    Args:
        labels (list): List of class labels.
        detections (dict): Detection results.
        image (PIL.Image.Image): Image to draw on.
        image_path (Path): Path to save the output image.
        width (int): Image width.
        height (int): Image height.
        min_score (float): Minimum score threshold.
        scale_factor (float): Scale factor for coordinates.
    """
    boxes = detections['detection_boxes']
    classes = detections['detection_classes']
    scores = detections['detection_scores']
    draw = ImageDraw.Draw(image)

    for idx in range(detections['num_detections']):
        if scores[idx] >= min_score:
            color = tuple(int(c) for c in COLORS[classes[idx]])
            scaled_box = [x * width if i % 2 == 0 else x * height for i, x in enumerate(boxes[idx])]
            draw_detection(labels, draw, scaled_box, classes[idx], scores[idx] * 100.0, color, scale_factor)

    image.save(image_path, 'JPEG')
