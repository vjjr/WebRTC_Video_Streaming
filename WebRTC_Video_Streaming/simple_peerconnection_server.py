#!/usr/bin/env python3
"""
Simple PeerConnection Server implementation in Python
This provides basic signaling functionality for WebRTC peer connections.
"""

import http.server
import socketserver
import json
import threading
import time
from urllib.parse import parse_qs, urlparse
import os

class PeerConnectionHandler(http.server.BaseHTTPRequestHandler):
    # Class variables to store connected peers and messages
    peers = {}  # peer_id -> {'name': name, 'last_seen': timestamp}
    pending_messages = {}  # peer_id -> [messages]
    next_peer_id = 1
    
    def do_GET(self):
        """Handle GET requests for signaling"""
        url_parts = urlparse(self.path)
        path = url_parts.path
        query_params = parse_qs(url_parts.query)
        
        print(f"GET request: {path} with params: {query_params}")
        
        # Serve the test HTML file
        if path == '/server_test.html' or path == '/':
            self.serve_html()
        elif path == '/sign_in':
            self.handle_sign_in(query_params)
        elif path == '/sign_out':
            self.handle_sign_out(query_params)
        elif path == '/wait':
            self.handle_wait(query_params)
        else:
            self.send_error(404, "Not found")
    
    def do_POST(self):
        """Handle POST requests for message passing"""
        url_parts = urlparse(self.path)
        path = url_parts.path
        query_params = parse_qs(url_parts.query)
        
        if path == '/message':
            content_length = int(self.headers.get('Content-Length', 0))
            message_data = self.rfile.read(content_length).decode('utf-8')
            self.handle_message(query_params, message_data)
        else:
            self.send_error(404, "Not found")
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Send CORS headers to allow cross-origin requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')
    
    def serve_html(self):
        """Serve the HTML test page"""
        html_content = """<!DOCTYPE html>
<html>
<head>
<title>PeerConnection server test page</title>
<script>
var request = null;
var hangingGet = null;
var localName;
var server;
var my_id = -1;
var other_peers = {};
var message_counter = 0;

function trace(txt) {
  var elem = document.getElementById("debug");
  elem.innerHTML += txt + "<br>";
}

function handleServerNotification(data) {
  trace("Server notification: " + data);
  var parsed = data.split(',');
  if (parseInt(parsed[2]) != 0)
    other_peers[parseInt(parsed[1])] = parsed[0];
}

function handlePeerMessage(peer_id, data) {
  ++message_counter;
  var str = "Message from '" + other_peers[peer_id] + "'&nbsp;";
  str += "<span id='toggle_" + message_counter + "' onclick='toggleMe(this);' ";
  str += "style='cursor: pointer'>+</span><br>";
  str += "<blockquote id='msg_" + message_counter + "' style='display:none'>";
  str += data + "</blockquote>";
  trace(str);
  if (document.getElementById("loopback").checked) {
    if (data.search("offer") != -1) {
      if (data.search("fingerprint") != -1)
        data = data.replace("offer", "offer-loopback");
      else
        data = data.replace("offer", "answer");
    }
    sendToPeer(peer_id, data);
  }
}

function GetIntHeader(r, name) {
  var val = r.getResponseHeader(name);
  return val != null && val.length ? parseInt(val) : -1;
}

function hangingGetCallback() {
  try {
    if (hangingGet.readyState != 4)
      return;
    if (hangingGet.status != 200) {
      trace("server error: " + hangingGet.statusText);
      disconnect();
    } else {
      var peer_id = GetIntHeader(hangingGet, "Pragma");
      if (peer_id == my_id) {
        handleServerNotification(hangingGet.responseText);
      } else {
        handlePeerMessage(peer_id, hangingGet.responseText);
      }
    }

    if (hangingGet) {
      hangingGet.abort();
      hangingGet = null;
    }

    if (my_id != -1)
      window.setTimeout(startHangingGet, 0);
  } catch (e) {
    trace("Hanging get error: " + e.description);
  }
}

function startHangingGet() {
  try {
    hangingGet = new XMLHttpRequest();
    hangingGet.onreadystatechange = hangingGetCallback;
    hangingGet.ontimeout = onHangingGetTimeout;
    hangingGet.open("GET", server + "/wait?peer_id=" + my_id, true);
    hangingGet.send();  
  } catch (e) {
    trace("error" + e.description);
  }
}

function onHangingGetTimeout() {
  trace("hanging get timeout. issuing again.");
  hangingGet.abort();
  hangingGet = null;
  if (my_id != -1)
    window.setTimeout(startHangingGet, 0);
}

function signInCallback() {
  try {
    if (request.readyState == 4) {
      if (request.status == 200) {
        var peers = request.responseText.split("\\n");
        my_id = parseInt(peers[0].split(',')[1]);
        trace("My id: " + my_id);
        for (var i = 1; i < peers.length; ++i) {
          if (peers[i].length > 0) {
            trace("Peer " + i + ": " + peers[i]);
            var parsed = peers[i].split(',');
            other_peers[parseInt(parsed[1])] = parsed[0];
          }
        }
        startHangingGet();
        request = null;
      }
    }
  } catch (e) {
    trace("error: " + e.description);
  }
}

function signIn() {
  try {
    request = new XMLHttpRequest();
    request.onreadystatechange = signInCallback;
    request.open("GET", server + "/sign_in?" + localName, true);
    request.send();
  } catch (e) {
    trace("error: " + e.description);
  }
}

function sendToPeer(peer_id, data) {
  if (my_id == -1) {
    alert("Not connected");
    return;
  }
  if (peer_id == my_id) {
    alert("Can't send a message to oneself :)");
    return;
  }
  var r = new XMLHttpRequest();
  r.open("POST", server + "/message?peer_id=" + my_id + "&to=" + peer_id, false);
  r.setRequestHeader("Content-Type", "text/plain");
  r.send(data);
  r = null;
}

function connect() {
  localName = document.getElementById("local").value.toLowerCase();
  server = document.getElementById("server").value.toLowerCase();
  if (localName.length == 0) {
    alert("I need a name please.");
    document.getElementById("local").focus();
  } else {
    document.getElementById("connect").disabled = true;
    document.getElementById("disconnect").disabled = false;
    document.getElementById("send").disabled = false;
    signIn();
  }
}

function disconnect() {
  if (request) {
    request.abort();
    request = null;
  }
  
  if (hangingGet) {
    hangingGet.abort();
    hangingGet = null;
  }

  if (my_id != -1) {
    request = new XMLHttpRequest();
    request.open("GET", server + "/sign_out?peer_id=" + my_id, false);
    request.send();
    request = null;
    my_id = -1;
  }

  document.getElementById("connect").disabled = false;
  document.getElementById("disconnect").disabled = true;
  document.getElementById("send").disabled = true;
}

window.onbeforeunload = disconnect;

function send() {
  var text = document.getElementById("message").value;
  var peer_id = parseInt(document.getElementById("peer_id").value);
  if (!text.length || peer_id == 0) {
    alert("No text supplied or invalid peer id");
  } else {
    sendToPeer(peer_id, text);
  }
}

function toggleMe(obj) {
  var id = obj.id.replace("toggle", "msg");
  var t = document.getElementById(id);
  if (obj.innerText == "+") {
    obj.innerText = "-";
    t.style.display = "block";
  } else {
    obj.innerText = "+";
    t.style.display = "none";
  }
}
</script>
</head>
<body>
Server: <input type="text" id="server" value="http://localhost:8888" /><br>
<input type="checkbox" id="loopback" checked="checked"/> Loopback (just send received messages right back)<br>
Your name: <input type="text" id="local" value="my_name"/>
<button id="connect" onclick="connect();">Connect</button>
<button disabled="true" id="disconnect" onclick="disconnect();">Disconnect</button>
<br>
<table><tr><td>
Target peer id: <input type="text" id="peer_id" size="3"/></td><td>
Message: <input type="text" id="message"/></td><td>
<button disabled="true" id="send" onclick="send();">Send</button>
</td></tr></table>
<button onclick="document.getElementById('debug').innerHTML='';">Clear log</button>

<pre id="debug">
</pre>
<br><hr>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def handle_sign_in(self, query_params):
        """Handle peer sign-in"""
        # Extract peer name from query string - it's sent as part of the URL path
        url_parts = urlparse(self.path)
        if '?' in self.path:
            peer_name = self.path.split('?')[1] or 'anonymous'
        else:
            peer_name = 'anonymous'
        
        # Assign new peer ID
        peer_id = self.next_peer_id
        PeerConnectionHandler.next_peer_id += 1
        
        # Store peer info
        PeerConnectionHandler.peers[peer_id] = {
            'name': peer_name,
            'last_seen': time.time()
        }
        PeerConnectionHandler.pending_messages[peer_id] = []
        
        print(f"Peer signed in: {peer_name} with ID {peer_id}")
        
        # Build response with peer list
        response_lines = [f"{peer_name},{peer_id},1"]
        for pid, pinfo in PeerConnectionHandler.peers.items():
            if pid != peer_id:
                response_lines.append(f"{pinfo['name']},{pid},1")
        
        response = '\n'.join(response_lines)
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))
    
    def handle_sign_out(self, query_params):
        """Handle peer sign-out"""
        peer_id = int(query_params.get('peer_id', [0])[0])
        if peer_id in PeerConnectionHandler.peers:
            del PeerConnectionHandler.peers[peer_id]
            if peer_id in PeerConnectionHandler.pending_messages:
                del PeerConnectionHandler.pending_messages[peer_id]
            print(f"Peer {peer_id} signed out")
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(b'')
    
    def handle_wait(self, query_params):
        """Handle long-polling wait request"""
        peer_id = int(query_params.get('peer_id', [0])[0])
        
        if peer_id not in PeerConnectionHandler.peers:
            self.send_error(404, "Peer not found")
            return
        
        # Update last seen
        PeerConnectionHandler.peers[peer_id]['last_seen'] = time.time()
        
        # Check for pending messages
        messages = PeerConnectionHandler.pending_messages.get(peer_id, [])
        if messages:
            message = messages.pop(0)
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Pragma', str(message['from_peer']))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(message['data'].encode('utf-8'))
        else:
            # Send notification about peer list changes
            peer_list = []
            for pid, pinfo in PeerConnectionHandler.peers.items():
                peer_list.append(f"{pinfo['name']},{pid},1")
            
            notification = ','.join([peer_list[0] if peer_list else ""])
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Pragma', str(peer_id))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(notification.encode('utf-8'))
    
    def handle_message(self, query_params, message_data):
        """Handle message forwarding between peers"""
        from_peer = int(query_params.get('peer_id', [0])[0])
        to_peer = int(query_params.get('to', [0])[0])
        
        if to_peer not in PeerConnectionHandler.peers:
            self.send_error(404, "Target peer not found")
            return
        
        # Queue message for target peer
        PeerConnectionHandler.pending_messages[to_peer].append({
            'from_peer': from_peer,
            'data': message_data
        })
        
        print(f"Message from peer {from_peer} to peer {to_peer}: {message_data[:50]}...")
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(b'')

def run_server(port=8888):
    """Run the PeerConnection server"""
    print(f"Starting PeerConnection server on port {port}")
    print(f"Open http://localhost:{port}/ in your browser to test")
    
    with socketserver.TCPServer(("", port), PeerConnectionHandler) as httpd:
        print(f"Server listening on port {port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped by user")
            httpd.shutdown()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Simple PeerConnection Signaling Server')
    parser.add_argument('--port', type=int, default=8888, help='Port to listen on (default: 8888)')
    args = parser.parse_args()
    
    run_server(args.port)
