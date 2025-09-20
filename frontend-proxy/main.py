import requests
from fastapi import FastAPI, Request
from fastapi.responses import Response
import os
from urllib.parse import parse_qs

# --- Configuration ---
# The real frontend service, which we have renamed to this.
REAL_FRONTEND_URL = "http://frontend-real:8080"
# The address of our MCP Toolbox Server, configured via environment variables.
TOOLBOX_URL = f"http://{os.getenv('TOOLBOX_SERVICE_HOST', 'mcp-toolbox-service')}:{os.getenv('TOOLBOX_SERVICE_PORT', '8080')}"

app = FastAPI()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(request: Request, path: str):
    """
    This single function handles all incoming requests, acting as a proxy.
    It has special logic to handle the 'POST /cart' request to emit context.
    """
    # Read the request body ONCE and store it. This is the key fix.
    body = await request.body()
    
    # Construct the full URL to the real frontend service
    target_url = f"{REAL_FRONTEND_URL}/{path}"
    
    # --- Our Special Interception Logic ---
    # We only care about the 'POST /cart' request, which adds an item.
    if request.method == "POST" and path == "cart":
        print("Intercepted an 'AddItemToCart' request...")
        
        try:
            # CORRECT WAY TO PARSE FORM DATA: Use the standard library.
            # This turns 'product_id=X&quantity=Y' into a dictionary.
            form_data = parse_qs(body.decode())
            
            # parse_qs returns a list for each value, so we take the first element.
            product_id = form_data.get("product_id", [None])[0]
            quantity = form_data.get("quantity", [None])[0]
            user_id = request.cookies.get("session_id", "unknown_user")

            if product_id:
                # Publish the event to our MCP Toolbox Server
                event = {
                    "topic": "user-activity",
                    "event": "item_added_to_cart",
                    "data": { "user_id": user_id, "product_id": product_id, "quantity": quantity }
                }
                requests.post(f"{TOOLBOX_URL}/mcp", json=event, timeout=1)
                print(f"Successfully published event for product: {product_id}")

        except Exception as e:
            # If anything goes wrong, we log it but don't crash the proxy.
            print(f"ERROR: Could not process form data or publish event: {e}")
    
    # --- Forward the original request ---
    resp = requests.request(
        method=request.method,
        url=target_url,
        headers={key: value for (key, value) in request.headers.items() if key != 'host'},
        data=body, # Use the stored body
        cookies=request.cookies,
        allow_redirects=False
    )
    
    # Return the response from the real frontend back to the original caller
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

