import os
import logging
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
import grpc
import demo_pb2
import demo_pb2_grpc
from uuid import uuid4

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

# --- CONFIGURE CLIENTS ---
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except KeyError:
    logging.error("🔴 FATAL: GOOGLE_API_KEY environment variable not set.")
    exit()

PRODUCT_CATALOG_SERVICE_ADDR = os.environ.get("PRODUCT_CATALOG_SERVICE_ADDR", "productcatalogservice:3550")
channel = grpc.insecure_channel(PRODUCT_CATALOG_SERVICE_ADDR)
product_catalog_stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)

# --- NEW: Simple in-memory session storage ---
SESSIONS = {}

# --- AGENT LOGIC ---
def get_all_product_names():
    """Tool to get a list of all products from the catalog."""
    try:
        response = product_catalog_stub.ListProducts(demo_pb2.Empty())
        return [p.name for p in response.products]
    except grpc.RpcError as e:
        logging.error(f"Could not list products: {e}")
        return []

@app.route('/')
def index():
    """Serves the chat UI."""
    return render_template('chat.html')

@app.route('/ask', methods=['POST'])
def ask_agent():
    """Handles a user's question, now with session memory."""
    data = request.get_json()
    question = data.get('question')
    session_id = data.get('session_id')

    if not question or not session_id:
        return jsonify({"answer": "Sorry, I received an invalid request."})

    # Initialize session if it's new
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {'last_product_name': None}

    # 1. THINK: Identify the product.
    product_names = get_all_product_names()
    prompt_for_product_id = f"""
    Given the user's question and a list of available products, identify which product they are asking about.
    Respond with the single product name only. If the question seems to be a follow-up that does not mention a product, respond with "None".

    User Question: "{question}"
    Available Products: {', '.join(product_names)}
    """
    try:
        response = model.generate_content(prompt_for_product_id)
        identified_product_name = response.text.strip()
    except Exception as e:
        return jsonify({"answer": "Sorry, I had trouble understanding your question."})

    target_product_name = None
    if identified_product_name != "None":
        # User mentioned a new product
        target_product_name = identified_product_name
        SESSIONS[session_id]['last_product_name'] = target_product_name
    elif SESSIONS[session_id]['last_product_name']:
        target_product_name = SESSIONS[session_id]['last_product_name']
    else:
        return jsonify({"answer": "I'm sorry, I'm not sure which product you're asking about. Could you be more specific?"})

    # 2. SENSE: Get product details from the catalog service.
    try:
        search_response = product_catalog_stub.SearchProducts(demo_pb2.SearchProductsRequest(query=target_product_name))
        if not search_response.results:
            return jsonify({"answer": f"Sorry, I couldn't find details for '{target_product_name}'."})
        
        product = search_response.results[0]
        product_context = {
            "name": product.name,
            "description": product.description,
            "price": f"{product.price_usd.units}.{product.price_usd.nanos // 10000000:02d} {product.price_usd.currency_code}"
        }
    except grpc.RpcError:
        return jsonify({"answer": "Sorry, I was unable to retrieve product information."})

    # 3. ACT: Generate the final answer using the context.
    final_prompt = f"""
    You are a friendly customer support agent. Answer the user's question based ONLY on the product data provided.

    User's Question: "{question}"
    Product Data: "{product_context}"
    """
    try:
        final_response = model.generate_content(final_prompt)
        return jsonify({"answer": final_response.text})
    except Exception:
        return jsonify({"answer": "Sorry, I'm having trouble formulating a response."})


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)