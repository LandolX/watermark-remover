import os
import sys
import cv2
import numpy as np
import easyocr
import onnxruntime as ort
import tempfile
from PIL import Image
from io import BytesIO
import base64
import json

# 设置CORS头
cors_headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
}

# 获取当前目录
api_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(api_dir)  # 项目根目录
# 添加项目根目录到 Python 路径
sys.path.append(project_root)

# 初始化 EasyOCR reader
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

# 获取 inpaint 模型路径
def get_inpaint_model():
    # 尝试不同的模型路径
    possible_paths = [
        os.path.join(project_root, 'models', 'migan_pipeline_v2.onnx'),
        os.path.join(project_root, 'migan_pipeline_v2.onnx'),
        os.path.join(api_dir, 'models', 'migan_pipeline_v2.onnx')
    ]
    
    for model_path in possible_paths:
        if os.path.exists(model_path):
            return model_path
    
    # 如果没有找到模型，返回默认路径
    return os.path.join(project_root, 'models', 'migan_pipeline_v2.onnx')

# 预处理图像
def preprocess_image(img):
    if len(img.shape) == 3 and img.shape[2] == 3:
        img_rgb = img.copy()
    else:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    img_transposed = img_rgb.transpose(2, 0, 1)
    img_batch = np.expand_dims(img_transposed, axis=0)
    return img_batch.astype(np.uint8)

# 预处理掩码
def preprocess_mask(mask, img_shape):
    mask_resized = cv2.resize(mask, (img_shape[1], img_shape[0]))
    _, mask_binary = cv2.threshold(mask_resized, 127, 255, cv2.THRESH_BINARY)
    mask_batch = np.expand_dims(np.expand_dims(mask_binary, axis=0), axis=0)
    return mask_batch.astype(np.uint8)

# 后处理输出
def postprocess_output(output, img_shape):
    output = output.squeeze(0)
    output = output.transpose(1, 2, 0)
    output = np.clip(output, 0, 255).astype(np.uint8)
    output = cv2.resize(output, (img_shape[1], img_shape[0]))
    return output

# 移除水印
def remove_watermark(image):
    # 读取图像
    img = image
    h, w = img.shape[:2]
    
    # 对整个图像进行 OCR 检测
    right_region = img.copy()
    right_region_w = w
    right_region_h = h
    start_x = 0
    start_y = 0
    
    # 初始化区域列表
    text_regions = []
    doubao_regions = []
    
    # 使用 EasyOCR 进行检测
    results = reader.readtext(right_region)
    
    for (bbox, text, prob) in results:
        # 转换边界框坐标
        (top_left, top_right, bottom_right, bottom_left) = bbox
        top_left = tuple(map(int, top_left))
        bottom_right = tuple(map(int, bottom_right))
        
        # 计算宽高
        w_text = bottom_right[0] - top_left[0]
        h_text = bottom_right[1] - top_left[1]
        
        # 检查是否是水印
        is_watermark = False
        is_variant = False
        
        # 处理常见的变体形式
        variant_patterns = [
            r"豆包.*[AaIi][1l]",  # 豆包A1, 豆包a1, 豆包AI, 豆包Ai
            r"豆.*[AaIi][1l].*生成",  # 豆A1生成, 豆@A1生成
            r"豆包.*[0-9]+",  # 豆包41, 豆包123等
        ]
        import re
        for pattern in variant_patterns:
            if re.search(pattern, text):
                is_watermark = True
                is_variant = True
                break
        
        # 如果不是变体，检查基础水印关键词
        if not is_watermark:
            watermark_keywords = ["豆包", "AI生成", "豆包AI", "AI", "生成"]
            for keyword in watermark_keywords:
                if keyword in text:
                    is_watermark = True
                    break
        
        # 根据水印类型设置不同的置信度阈值
        if is_watermark:
            if is_variant:
                if prob > 0:
                    # 直接使用原始检测到的区域，不进行扩展
                    original_x = top_left[0]
                    original_y = top_left[1]
                    original_w = w_text
                    original_h = h_text
                    
                    # 确保区域在图片边界内
                    original_x = max(0, original_x)
                    original_y = max(0, original_y)
                    original_w = min(original_w, right_region_w - original_x)
                    original_h = min(original_h, right_region_h - original_y)
                    
                    text_regions.append((original_x, original_y, original_w, original_h))
                    doubao_regions.append((original_x, original_y, original_w, original_h))
            else:
                if prob > 0.5:
                    # 直接使用原始检测到的区域，不进行扩展
                    original_x = top_left[0]
                    original_y = top_left[1]
                    original_w = w_text
                    original_h = h_text
                    
                    # 确保区域在图片范围内
                    original_x = max(0, original_x)
                    original_y = max(0, original_y)
                    original_w = min(original_w, right_region_w - original_x)
                    original_h = min(original_h, right_region_h - original_y)
                    
                    text_regions.append((original_x, original_y, original_w, original_h))
                    doubao_regions.append((original_x, original_y, original_w, original_h))
    
    # 创建全局掩码
    mask = np.ones((h, w), dtype=np.uint8) * 255
    
    for (x, y, w_cnt, h_cnt) in text_regions:
        # 转换为原图坐标
        global_x = x + start_x
        global_y = y + start_y
        
        # 确保区域在图片范围内
        global_x = max(0, global_x)
        global_y = max(0, global_y)
        w_cnt = min(w_cnt, w - global_x)
        h_cnt = min(h_cnt, h - global_y)
        
        if w_cnt > 0 and h_cnt > 0:
            # 在掩码上标记水印区域为黑色（0）
            mask[global_y:global_y+h_cnt, global_x:global_x+w_cnt] = 0
    
    # 如果没有检测到水印，直接返回原图
    if not text_regions:
        return img
    
    # 使用 inpaint 模型去除水印
    model_path = get_inpaint_model()
    session = ort.InferenceSession(model_path)
    
    # 预处理图像和掩码
    input_image = preprocess_image(img)
    input_mask = preprocess_mask(mask, img.shape)
    
    # 模型推理
    inputs = {
        session.get_inputs()[0].name: input_image,
        session.get_inputs()[1].name: input_mask
    }
    outputs = session.run(None, inputs)
    
    # 后处理输出
    output_image = postprocess_output(outputs[0], img.shape)
    
    return output_image

# 解析 multipart/form-data 请求
def parse_multipart_form_data(event):
    import urllib.parse
    import email
    from io import BytesIO
    
    body = event.get('body', '')
    content_type = event.get('headers', {}).get('content-type', '')
    
    if not body or 'multipart/form-data' not in content_type:
        return {}
    
    # 解析边界
    boundary = content_type.split('boundary=')[1].encode('utf-8')
    body = base64.b64decode(body) if event.get('isBase64Encoded') else body.encode('utf-8')
    
    # 解析表单数据
    form_data = {}
    message = email.message_from_bytes(b'Content-Type: ' + content_type.encode('utf-8') + b'\n\n' + body)
    
    for part in message.get_payload():
        if part.get_content_maintype() == 'multipart':
            continue
        
        name = part.get_param('name', header='content-disposition')
        filename = part.get_filename()
        
        if name:
            if filename:
                # 文件字段
                form_data[name] = {
                    'filename': filename,
                    'content': part.get_payload(decode=True)
                }
            else:
                # 普通字段
                form_data[name] = part.get_payload(decode=True).decode('utf-8')
    
    return form_data

# Vercel 原生 Serverless 函数
def handler(event, context):
    try:
        # 处理 OPTIONS 请求
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': ''
            }
        
        # 处理 POST 请求
        if event.get('httpMethod') == 'POST':
            # 解析表单数据
            form_data = parse_multipart_form_data(event)
            
            # 检查请求中是否有文件
            if 'image' not in form_data:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'No image file provided'})
                }
            
            # 读取图像文件
            file_data = form_data['image']
            img = cv2.imdecode(np.frombuffer(file_data['content'], np.uint8), cv2.IMREAD_COLOR)
            
            if img is None:
                return {
                    'statusCode': 400,
                    'headers': cors_headers,
                    'body': json.dumps({'error': 'Failed to read image'})
                }
            
            # 移除水印
            result = remove_watermark(img)
            
            # 将结果转换为 base64
            _, buffer = cv2.imencode('.png', result)
            img_str = base64.b64encode(buffer).decode('utf-8')
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'result': img_str})
            }
        
        # 不支持的请求方法
        return {
            'statusCode': 405,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Method not allowed'})
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error: {error_trace}")
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': f'{str(e)} - {error_trace[:200]}'})
        }
