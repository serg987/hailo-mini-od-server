import io
from PIL import Image
import numpy as np

from config import config


class InferenceImage:
    def __init__(self, image_stream: io.BytesIO):
        self.image_stream = image_stream
        self.image = None
        self.model_w = None
        self.model_h = None
        self.scale = None
        self.new_img_w = None
        self.new_img_h = None
        self.pasted_w = None
        self.pasted_h = None
        self.padded_image = None

    def set_model_input_size(self, model_w, model_h):
        self.model_w = model_w
        self.model_h = model_h

    def preprocess(self):
        """
        Resize image with unchanged aspect ratio using padding.

        Args:
            image (PIL.Image.Image): Input image.
            model_w (int): Model input width.
            model_h (int): Model input height.

        Returns:
            PIL.Image.Image: Preprocessed and padded image.
        """
        self.image = Image.open(self.image_stream)
        img_w, img_h = self.image.size
        # Scale image
        self.scale = min(self.model_w / img_w, self.model_h / img_h)
        self.new_img_w, self.new_img_h = int(img_w * self.scale), int(img_h * self.scale)
        image_resized = self.image.resize((self.new_img_w, self.new_img_h), Image.Resampling.BICUBIC)

        # Create a new padded image
        self.padded_image = Image.new('RGB', (self.model_w, self.model_h), config.padding_color)
        self.pasted_w = (self.model_w - self.new_img_w) // 2
        self.pasted_h = (self.model_h - self.new_img_h) // 2
        self.padded_image.paste(image_resized, (self.pasted_w, self.pasted_h))
        return np.array(self.padded_image)

    def get_preprocessed_image(self):
        return self.padded_image

    def postprocess(self, detection_results: dict):
        # as of now just restore the original coordinates in the image
        boxes = detection_results.get('detection_boxes')
        absolute_boxes = []
        for box in boxes:
            abs_coords = []
            for i, coord in enumerate(box):
                if i % 2 == 0:
                    # height (y) is first coming
                    abs_coord = coord * self.model_h
                    abs_coord -= self.pasted_h
                else:
                    # getting real coordinates first
                    abs_coord = coord * self.model_w
                    # get a coordinate without padding
                    abs_coord -= self.pasted_w
                # restore original coordinates
                abs_coord /= self.scale
                abs_coords.append(int(abs_coord))
            absolute_boxes.append(abs_coords)

        detection_results.update({'absolute_boxes': absolute_boxes})
