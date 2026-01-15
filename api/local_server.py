#!/usr/bin/env python3
"""
本地测试服务器，用于模拟Vercel运行时环境，测试Serverless函数
"""

import http.server
import socketserver
import json
import base64
from io import BytesIO
from api.index import handler

PORT = 5000

class VercelLocalHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, headers=None):
        self.send_response(status_code)
        
        # 设置CORS头
        cors_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
        
        # 合并自定义头
        if headers:
            cors_headers.update(headers)
        
        # 发送所有头
        for key, value in cors_headers.items():
            self.send_header(key, value)
        
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
    
    def do_OPTIONS(self):
        """处理OPTIONS请求"""
        self._set_headers(200)
        self.wfile.write(b'')
    
    def do_POST(self):
        """处理POST请求"""
        try:
            # 读取请求体
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            
            # 构建Vercel事件对象
            event = {
                'httpMethod': 'POST',
                'headers': {
                    'content-type': self.headers.get('Content-Type', ''),
                    'content-length': self.headers.get('Content-Length', ''),
                    'host': self.headers.get('Host', ''),
                    'user-agent': self.headers.get('User-Agent', '')
                },
                'body': body.decode('utf-8') if isinstance(body, bytes) else body,
                'isBase64Encoded': False,
                'path': self.path,
                'queryStringParameters': {},
                'requestContext': {
                    'http': {
                        'method': 'POST',
                        'path': self.path,
                        'headers': dict(self.headers)
                    }
                }
            }
            
            # 处理multipart/form-data请求
            if 'multipart/form-data' in self.headers.get('Content-Type', ''):
                # 对于multipart/form-data，body需要是base64编码
                event['body'] = base64.b64encode(body).decode('utf-8')
                event['isBase64Encoded'] = True
            
            # 调用Vercel handler函数
            response = handler(event, None)
            
            # 发送响应
            self._set_headers(response['statusCode'], response.get('headers', {}))
            self.wfile.write(response['body'].encode('utf-8') if isinstance(response['body'], str) else response['body'])
        
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error: {error_trace}")
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': f'{str(e)} - {error_trace[:200]}'}).encode('utf-8'))

# 启动服务器
if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), VercelLocalHandler) as httpd:
        print(f"本地测试服务器启动，监听端口 {PORT}")
        print(f"访问地址: http://localhost:{PORT}")
        print("按 Ctrl+C 停止服务器")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器停止")
            httpd.shutdown()
