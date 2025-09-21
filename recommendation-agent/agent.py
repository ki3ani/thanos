import os
import logging
import grpc
from concurrent import futures
import threading
from flask import Flask, jsonify
import google.generativeai as genai
import requests
import demo_pb2
import demo_pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

last_recommendation_cache = {"input_cart_names": [], "output_product_names": ["Agent has not run yet."]}
app = Flask(__name__)

@app.route('/latest_recommendation')
def get_latest_recommendation():
    return jsonify(last_recommendation_cache)

try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except KeyError:
    logging.error("🔴 FATAL: GOOGLE_API_KEY environment variable not set.")
    exit()

PRODUCT_CATALOG_SERVICE_ADDR = os.environ.get("PRODUCT_CATALOG_SERVICE_ADDR", "productcatalogservice:3550")
MARKETING_AGENT_URL = os.environ.get("MARKETING_AGENT_URL", "http://marketing-campaigner-service:8080/latest_ad")
catalog_channel = grpc.insecure_channel(PRODUCT_CATALOG_SERVICE_ADDR)
product_catalog_stub = demo_pb2_grpc.ProductCatalogServiceStub(catalog_channel)

class RecommendationAgentService(demo_pb2_grpc.RecommendationServiceServicer):
    
    def get_product_name_from_id(self, product_id):
        """A tool to get a product's name from its ID."""
        try:
            return product_catalog_stub.GetProduct(demo_pb2.GetProductRequest(id=product_id)).name
        except grpc.RpcError:
            return "Unknown Product"

    def ListRecommendations(self, request, context):
        global last_recommendation_cache
        cart_product_ids = list(request.product_ids)
        logging.info(f"gRPC: Received request for cart: {cart_product_ids}")

        cart_product_names = [self.get_product_name_from_id(pid) for pid in cart_product_ids]
        logging.info(f"gRPC: Enriched cart names: {cart_product_names}")

        promoted_product = "None"
        try:
            response = requests.get(MARKETING_AGENT_URL, timeout=2)
            if response.ok: promoted_product = response.json().get('product_name', 'None')
        except requests.exceptions.RequestException: pass

        try:
            catalog_response = product_catalog_stub.ListProducts(demo_pb2.Empty())
            all_product_names = [p.name for p in catalog_response.products]
        except grpc.RpcError: return demo_pb2.ListRecommendationsResponse()

        prompt = f"""
        You are a smart recommendation engine for an e-commerce store.
        Your goal is to recommend 3 products to a user based on their cart, the full product catalog, and the current marketing campaign.

        User's Cart contains: {cart_product_names}
        The Marketing department is currently promoting the product: '{promoted_product}'
        The full catalog of product names is: {all_product_names}

        Based on all this information, suggest 3 relevant product names from the catalog that are NOT already in the user's cart.
        Respond with a comma-separated list of the 3 product names, and nothing else.
        """
        
        try:
            response = model.generate_content(prompt)
            recommended_names = [name.strip() for name in response.text.split(',')]
            logging.info(f"gRPC: AI recommended products: {recommended_names}")
            
            last_recommendation_cache = {
                "input_cart_names": cart_product_names,
                "output_product_names": recommended_names
            }
        except Exception:
            logging.error("Error generating recommendations, falling back to original logic.")
            return demo_pb2.ListRecommendationsResponse(product_ids=[p.id for p in catalog_response.products[:4] if p.id not in cart_product_ids])

        recommended_product_ids = [p.id for p in catalog_response.products if p.name in recommended_names]
        logging.info(f"gRPC: Returning recommended product IDs: {recommended_product_ids}")
        return demo_pb2.ListRecommendationsResponse(product_ids=recommended_product_ids)

def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    demo_pb2_grpc.add_RecommendationServiceServicer_to_server(RecommendationAgentService(), server)
    port = os.environ.get('PORT', '8080')
    server.add_insecure_port(f'[::]:{port}')
    logging.info(f"gRPC server started on port {port}")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5001))
    flask_thread.daemon = True
    flask_thread.start()
    serve_grpc()