from web_server import run_server
from hailo_infer import hailo_device
from config import logger

if __name__ == '__main__':
    init_result = True
    if init_result:
        try:
            run_server()
        finally:
            logger.critical('Something bad happened, trying to release Hailo device')
            if hailo_device and hailo_device.is_initialized:
                hailo_device.stop_device()
                logger.info('Hailo device released')
            else:
                logger.info('No Hailo device was initialized, nothing to release')
