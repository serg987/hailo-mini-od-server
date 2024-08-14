import logging
import sys
import uuid
from os import listdir
from os.path import isfile, join


class LoggerWriter:
    def __init__(self, level):
        # self.level is really like using log.debug(message)
        # at least in my case
        self.level = level

    def write(self, message):
        # if statement reduces the amount of newlines that are
        # printed to the logger
        if message != '\n':
            self.level(message)

    def flush(self):
        # create a flush method so things can be flushed when
        # the system wants to. Not sure if simply 'printing'
        # sys.stderr is the correct way to do it, but it seemed
        # to work properly for me.
        self.level(sys.stderr)


logging.basicConfig(format='%(asctime)s.%(msecs)03d [%(filename)s:%(lineno)d] %(levelname)s:%(message)s',
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()
sys.stdout = LoggerWriter(logger.debug)
sys.stderr = LoggerWriter(logger.warning)


class Config:
    def __init__(self):
        self.labels_filename = "models/coco.txt"
        self.output_images_path = "output_images"
        self.batch_size = 1  # default to 1 then decide if we want to handle multiple (doubtful)
        self.padding_color = (114, 114, 114)
        self.default_confidence_score = 0.6
        self.model_folder = 'models'
        self.default_model_name = 'yolov7e6'
        self.current_model_name = None
        self.model_filename_dict = dict()
        self.detect_msg_len = 25

        self._collect_local_models()

    def get_current_model_name(self):
        if not self.current_model_name:
            self.current_model_name = self.default_model_name
        return self.current_model_name

    def _collect_local_models(self):
        model_files = [f for f in listdir(self.model_folder)
                       if isfile(join(self.model_folder, f)) and f.endswith('.hef')]
        self.model_filename_dict = {f[:-4].replace('.', '_'): f'{self.model_folder}/{f}' for f in model_files}

    def get_api_module_name(self):
        return f'Object Detection ({self.current_model_name})'

    def get_api_module_id(self):
        return f'ObjectDetection{self.current_model_name.upper()}'

    def get_model_filename(self):
        return self.model_filename_dict[self.current_model_name]

    def get_model_list(self):
        return list(self.model_filename_dict.keys())

    def get_common_response(self):
        return dict({"requestId": str(uuid.uuid4()),
                     "moduleId": self.get_api_module_id(),
                     "moduleName": self.get_api_module_name(),
                     "executionProvider": "TPU",
                     "inferenceDevice": "TPU",
                     "processedBy": "localhost",
                     "canUseGPU": False})


config = Config()
