#!/usr/bin/env python3
"""
Simple HTTP server for the classification tool with save functionality
"""

import http.server
import socketserver
import os
import json

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        # Log the request
        print(f"GET request for: {self.path}")
        super().do_GET()
    
    def do_POST(self):
        """Handle POST requests for saving review data"""
        if self.path == '/save_review':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                filename = data.get('filename', 'review_data.json')
                review_data = data.get('data', [])
                
                # Save to project directory
                filepath = os.path.join(os.getcwd(), filename)
                with open(filepath, 'w') as f:
                    json.dump(review_data, f, indent=2)
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'success', 'message': f'Saved {len(review_data)} items'}
                self.wfile.write(json.dumps(response).encode())
                
                print(f"✓ Saved {len(review_data)} reviewed characters to {filename}")
                
            except Exception as e:
                # Send error response
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'error', 'message': str(e)}
                self.wfile.write(json.dumps(response).encode())
                print(f"Error saving review data: {e}")
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.end_headers()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"Server running at http://localhost:{PORT}/")
    print(f"Open http://localhost:{PORT}/classify_individual.html in your browser")
    print("Press Ctrl+C to stop the server")
    httpd.serve_forever()