import io
import time
import math
from typing import Optional

from aiohttp import web
from aiohttp.web_routedef import Request

from config import logger, config
from hailo_infer import do_inference
from inference_image import InferenceImage

routes = web.RouteTableDef()


def get_gmt_timestamp():
    return time.strftime("%a, %d %b %Y %I:%M:%S GMT", time.gmtime())


def html_response(document):
    s = open(document, "r")
    return web.Response(text=s.read(), content_type='text/html')


class DetectRequest:
    def __init__(self):
        self.min_confidence: Optional[float] = None
        self.filename: Optional[str] = None
        self.file_content: Optional[bytearray] = None

    def is_valid(self):
        return (self.filename is not None
                and self.file_content is not None
                and len(self.filename) > 0
                and len(self.file_content) > 0)

    def get_confidence_score(self):
        return self.min_confidence if self.min_confidence else config.default_confidence_score


def log_request(request: Request):
    logger.debug(request)
    logger.debug(f"path: {request.path}")
    logger.debug(f"headers: {request.headers}")
    logger.debug(f"app: {request.app}")
    logger.debug(f"content: {request.content}")
    logger.debug(f"content_type: {request.content_type}")
    logger.debug(f"config_dict: {request.config_dict}")
    logger.debug(f"can_read_body: {request.can_read_body}")
    logger.debug(f"body_exists: {request.body_exists}")


@routes.get('/')
async def index_handler(request):
    logger.debug('Got request on / path')
    return html_response('./web/index.html')


@routes.get('/v1/server/status/ping')
async def ping_handler(request):
    # will not implement all the fields from CodeProject ping as it is not CodeProject
    logger.debug('Got request on /v1/server/status/ping path')
    response_json = {"code": 200, "hostname": "hailoserver", "success": True}
    return web.json_response(response_json)


@routes.get('/v1/status/updateavailable')
async def ping_handler(request):
    # this endpoint is needed for BlueIris
    # has to implement all the fields from CodeProject ping as BlueIris complains AI is not available
    logger.debug('Got request on /v1/status/updateavailable path')
    version_response = {"major": 0,
                        "minor": 1,
                        "patch": 0,
                        "preRelease": "",
                        "securityUpdate": False,
                        "build": 0,
                        "file": "https://www.codeproject.com/ai/latest.aspx",
                        "releaseNotes": "First Hailo simple release."}
    response_json = {"code": 200,
                     "hostname": "hailoserver",
                     "success": True,
                     "updateAvailable": "False",
                     "latest": version_response,
                     "current": version_response,
                     "version": version_response}
    return web.json_response(response_json)


@routes.post('/v1/vision/custom/list')
async def list_custom_handler(request):
    start_time = time.perf_counter()
    response_json = config.get_common_response()
    print(response_json)
    response_json.update({"code": 200,
                          "success": True,
                          "models": config.get_model_list(),
                          "assets": config.get_model_list(),
                          "command": "list-custom",
                          "analysisRoundTripMs": math.ceil((time.perf_counter() - start_time) * 1000),
                          "timestampUTC": get_gmt_timestamp()})
    print(response_json)
    return web.json_response(response_json)


async def parse_detection_request(request: Request) -> DetectRequest:
    dr = DetectRequest()
    m_p = await request.multipart()
    m_p_next = await m_p.next()
    while m_p_next:
        if m_p_next.name == 'min_confidence':
            m_c = await m_p_next.form()
            dr.min_confidence = float(m_c[0][0])
        if m_p_next.name == 'image':
            dr.filename = m_p_next.filename
            dr.file_content = await m_p_next.read()
        m_p_next = await m_p.next()
    await m_p.release()
    return dr


def format_detection_response(detection: dict, response_dict: dict = config.get_common_response()):
    num_detections = detection['num_detections']
    labels = detection["detection_labels"]
    detection_scores = detection["detection_scores"]
    detection_boxes = detection["absolute_boxes"]
    response_dict.update({"command": "detect",
                          "count": num_detections,
                          'inferenceMs': detection['inferenceMs'],
                          'processMs': detection['processMs']})
    if detection.get('success'):
        response_dict.update({'success': detection.get('success')})
    if detection.get('error'):
        response_dict.update({'error': detection.get('error')})
    if detection.get('imagePath'):
        response_dict.update({'imagePath': detection.get('imagePath')})
    if num_detections == 0:
        message = 'No objects found'
    else:
        deduped_labels = list(set(labels))
        if len(deduped_labels) == 1:
            message = f'Found {deduped_labels[0]}'
        else:
            message = f'Found {", ".join(deduped_labels)}'
            message = message[:config.detect_msg_len]
            comma_ind = message.rfind(',')
            if comma_ind > config.detect_msg_len - 3:
                message = message[:comma_ind]
                comma_ind = message.rfind(',')
                message = f'{message[:comma_ind]}...'
    predictions = []
    for i in range(num_detections):
        prediction = {"confidence": float(detection_scores[i]),
                      "label": labels[i],
                      "x_min": detection_boxes[i][1],
                      "y_min": detection_boxes[i][0],
                      "x_max": detection_boxes[i][3],
                      "y_max": detection_boxes[i][2]
                      }
        predictions.append(prediction)
    response_dict.update({'message': message, 'predictions': predictions})

    return response_dict


async def handle_detection_request(request: Request,
                                   model_name: Optional[str] = None,
                                   do_visualization: Optional[bool] = None):
    start_time = time.perf_counter()
    web_response = config.get_common_response()
    if not model_name:
        model_name = config.get_current_model_name()
    if request.content_type != 'multipart/form-data':
        return web.Response(text=f'{request.content_type} is not supported', status=400, content_type='text/html')

    dr: DetectRequest = await parse_detection_request(request)
    if not dr.is_valid():
        return web.Response(text='Submitted form is invalid', status=400, content_type='text/html')

    logger.debug('Got image stream')
    image = InferenceImage(io.BytesIO(dr.file_content))
    logger.debug('Processed image stream')
    infer_result = await do_inference(image,
                                      confidence_score=dr.get_confidence_score(),
                                      model_name=model_name,
                                      image_uuid=web_response['requestId'] if do_visualization else None)
    if model_name:
        updated_response_new_model = config.get_common_response()
        web_response['moduleId'] = updated_response_new_model['moduleId']
        web_response['moduleName'] = updated_response_new_model['moduleName']
    detection_result = format_detection_response(infer_result, web_response)
    logger.debug(f'Detection result: %s', detection_result)

    code = 400 if detection_result.get('error') or not detection_result.get('success') else 200
    detection_result.update({"code": code,
                             "analysisRoundTripMs": math.ceil((time.perf_counter() - start_time) * 1000)
                             })
    logger.info("Request ID: %s; %s; roundtrip, ms: %d; inference, ms: %d",
                detection_result['requestId'],
                detection_result['message'],
                detection_result['analysisRoundTripMs'],
                detection_result['inferenceMs'])
    return web.json_response(detection_result)


@routes.post('/v1/vision/detection')
async def vision_detection_handler(request):
    return await handle_detection_request(request)


@routes.post('/v1/vision/custom/{model_name}')
async def custom_model_detection_response(request):
    model_name = request.match_info['model_name']
    if model_name not in config.get_model_list():
        return web.Response(status=404, text=f'Model {model_name} is not available')
    return await handle_detection_request(request, model_name=model_name)


@routes.post('/v1/visualization/custom/{model_name}')
async def visualization_response(request):
    model_name = request.match_info['model_name']
    if model_name not in config.get_model_list():
        return web.Response(status=404, text=f'Model {model_name} is not available')
    return await handle_detection_request(request, model_name=model_name, do_visualization=True)


def run_server():
    logger.info('Starting Web Server')
    app = web.Application()
    app.add_routes(routes)
    app.add_routes([web.static('/', './web'),
                    web.static('/output_images', './output_images')])
    web.run_app(app, access_log=logger)
