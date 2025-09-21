import os
import logging
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

# --- NEW IMPORTS for gRPC ---
import grpc
import demo_pb2
import demo_pb2_grpc

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# --- NEW gRPC Client Setup ---
# Get the address of the product catalog service from an environment variable
PRODUCT_CATALOG_SERVICE_ADDR = os.environ.get("PRODUCT_CATALOG_SERVICE_ADDR", "productcatalogservice:3550")
# Set up a gRPC channel
channel = grpc.insecure_channel(PRODUCT_CATALOG_SERVICE_ADDR)
product_catalog_stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            database=os.environ.get('DB_NAME', 'postgres'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD')
        )
        return conn
    except Exception as e:
        logging.error(f"Error connecting to the database: {e}")
        return None

@app.route('/mcp', methods=['POST'])
def handle_mcp_event():
    event_data = request.get_json()
    if not event_data or 'data' not in event_data or 'product_id' not in event_data['data']:
        logging.warning(f"Request failed on payload check. Payload: {event_data}")
        return jsonify({"status": "error", "message": "Invalid payload"}), 400

    product_id = event_data['data']['product_id']
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (product_id, event_type) VALUES (%s, %s);",
            (product_id, 'ADD_TO_CART')
        )
        conn.commit()
        logging.info(f"Successfully logged ADD_TO_CART event for product_id: {product_id}")
        cur.close()
        conn.close()
        return jsonify({"status": "success", "message": "Event logged"}), 200
    except Exception as e:
        logging.error(f"An error occurred during DB write operation: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/context', methods=['GET'])
def get_context():
    """Provides context by fetching events and enriching them with product names."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT product_id, created_at FROM events ORDER BY created_at DESC LIMIT 10;")
        recent_events = cur.fetchall()
        cur.close()
        conn.close()

        enriched_events = []
        # 2. For each event, ask the Product Catalog service for the product's name
        for event in recent_events:
            product_id = event['product_id']
            try:
                # Make the gRPC call to the other microservice
                request_message = demo_pb2.GetProductRequest(id=product_id)
                product_details = product_catalog_stub.GetProduct(request_message)
                
                # 3. Combine the data
                enriched_events.append({
                    'created_at': event['created_at'].isoformat(),
                    'product_id': product_id,
                    'product_name': product_details.name
                })
            except grpc.RpcError as e:
                logging.warning(f"Could not get product details for {product_id}: {e.details()}")
                # Still include the event, just without the name
                enriched_events.append({
                    'created_at': event['created_at'].isoformat(),
                    'product_id': product_id,
                    'product_name': 'Unknown'
                })

        logging.info(f"Fetched and enriched {len(enriched_events)} events for context.")
        return jsonify(enriched_events), 200
        
    except Exception as e:
        logging.error(f"An error occurred during context retrieval: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)