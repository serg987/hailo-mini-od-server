# most of the part is taken from https://github.com/hailo-ai/Hailo-Application-Code-Examples/blob/main/runtime/python/object_detection/object_detection.py
import os
import time
from typing import Optional
from PIL import Image

import numpy as np

from config import config, logger
from utils import HailoInference
from inference_image import InferenceImage
from visualization import visualize


def get_labels(labels_path: str) -> [str]:
    """
    Load labels from a file.

    Args:
        labels_path (str): Path to the labels file.

    Returns:
        list: List of class names.
    """
    with open(labels_path, 'r', encoding="utf-8") as f:
        class_names = f.read().splitlines()
    return class_names


labels = get_labels(config.labels_filename)


def extract_detections(input_data, threshold:float = config.default_confidence_score):
    """
    Extract detections from the input data.

    Args:
        input_data (list): Raw detections from the model.
        threshold (float): Score threshold for filtering detections.

    Returns:
        dict: Filtered detection results.
    """
    boxes, scores, classes = [], [], []
    num_detections = 0

    for i, detection in enumerate(input_data):
        if len(detection) == 0:
            continue

        for det in detection:
            bbox, score = det[:4], det[4]

            if score >= threshold:
                boxes.append(bbox)
                scores.append(score)
                classes.append(i)
                num_detections += 1

    return {
        'detection_boxes': boxes,
        'detection_classes': classes,
        'detection_scores': scores,
        'num_detections': num_detections
    }


def add_labels(detection: dict):
    detection.update({'detection_labels': [labels[dt] for dt in detection['detection_classes']]})


class HailoDevice:
    def __init__(self):
        self.hailo_inference = None
        self.is_initialized = False

    def start_device(self, model_name: Optional[str] = None):
        if not model_name:
            model_name = config.get_current_model_name()
        logger.info('Starting Hailo device init with model %s', model_name)
        config.current_model_name = model_name
        self.hailo_inference = HailoInference(config.get_model_filename())
        self.is_initialized = True

        logger.info('Finished Hailo device init')

    async def change_model(self, model_name: str):
        if model_name != config.get_current_model_name():
            self.stop_device()
            time.sleep(1)
            self.start_device(model_name)
            logger.info("Model was successfully changed to %s", model_name)

    def stop_device(self):
        self.hailo_inference.release_device()
        self.is_initialized = False


hailo_device = HailoDevice()
hailo_device.start_device()


async def do_inference(image: InferenceImage,
                       model_name: str,
                       confidence_score: float = config.default_confidence_score,
                       image_uuid: Optional[str] = None):
    start_process_time = time.perf_counter()
    await hailo_device.change_model(model_name)

    height, width, _ = hailo_device.hailo_inference.get_input_shape()
    image.set_model_input_size(width, height)

    logger.debug('Starting preprocess image')
    infer_images = [image.preprocess()]

    logger.debug('Finished preprocess image; starting inference')
    start_inference_time = time.perf_counter()
    raw_detections = hailo_device.hailo_inference.run(np.array(infer_images))
    logger.debug(raw_detections)

    detections = extract_detections(raw_detections[0], confidence_score)

    inference_ms = int((time.perf_counter() - start_inference_time) * 1000)

    logger.debug(detections)
    image.postprocess(detections)
    add_labels(detections)

    detections.update({"processMs": int((time.perf_counter() - start_process_time) * 1000),
                       "inferenceMs": inference_ms,
                       "success": True})

    if image_uuid:
        image_path = os.path.join(config.output_images_path,f'{image_uuid}_{config.current_model_name}.jpg')
        visualize(labels, detections, image.get_preprocessed_image(), image_path, width, height)
        detections.update({'imagePath': f'{image_path}'})

    return detections

