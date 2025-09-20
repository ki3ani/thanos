import requests  # type: ignore
from fastapi import FastAPI, Request
from fastapi.responses import Response
import os
from urllib.parse import parse_qs

REAL_FRONTEND_URL = "http://frontend-real:8080"
TOOLBOX_URL = (
    f"http://{os.getenv('TOOLBOX_SERVICE_HOST', 'mcp-toolbox-service')}:"
    f"{os.getenv('TOOLBOX_SERVICE_PORT', '8080')}"
)

app = FastAPI()


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])  # type: ignore
async def proxy_request(request: Request, path: str) -> Response:
    """
    This single function handles all incoming requests, acting as a proxy.
    It has special logic to handle the 'POST /cart' request to emit context.
    """
    body = await request.body()
    target_url = f"{REAL_FRONTEND_URL}/{path}"

    if request.method == "POST" and path == "cart":
        print("Intercepted an 'AddItemToCart' request...")

        try:
            form_data = parse_qs(body.decode())
            product_id = form_data.get("product_id", [None])[0]
            quantity = form_data.get("quantity", [None])[0]
            user_id = request.cookies.get("session_id", "unknown_user")

            if product_id:
                event = {
                    "topic": "user-activity",
                    "event": "item_added_to_cart",
                    "data": {
                        "user_id": user_id,
                        "product_id": product_id,
                        "quantity": quantity,
                    },
                }
                requests.post(f"{TOOLBOX_URL}/mcp", json=event, timeout=1)
                print(f"Successfully published event for product: {product_id}")

        except Exception as e:
            print(f"ERROR: Could not process form data or publish event: {e}")

    resp = requests.request(
        method=request.method,
        url=target_url,
        headers={
            key: value for (key, value) in request.headers.items() if key != "host"
        },
        data=body,
        cookies=request.cookies,
        allow_redirects=False,
    )

    return Response(
        content=resp.content, status_code=resp.status_code, headers=dict(resp.headers)
    )
