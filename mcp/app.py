import os
import logging
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor # Used to get JSON-like results

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Function to get a database connection
def get_db_connection():
    try:
        # With the Cloud SQL Proxy, we always connect to localhost (127.0.0.1)
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
    """Receives an 'add to cart' event and WRITES it to the events table."""
    
    event_data = request.get_json()
    
    # --- THIS IS THE CORRECTED LOGIC ---
    # Check if 'data' exists, and if 'product_id' exists inside 'data'
    if not event_data or 'data' not in event_data or 'product_id' not in event_data['data']:
        logging.warning(f"Request failed because payload was not valid or was missing nested 'product_id'. Payload: {event_data}")
        return jsonify({"status": "error", "message": "Invalid payload"}), 400

    # Access the product_id from the nested 'data' object
    product_id = event_data['data']['product_id']
    # --- END OF CORRECTION ---

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    try:
        cur = conn.cursor()
        
        # Insert the event into our new events table
        cur.execute(
            "INSERT INTO events (product_id, event_type) VALUES (%s, %s);",
            (product_id, 'ADD_TO_CART')
        )
        # Commit the transaction to save the data
        conn.commit()
        logging.info(f"Successfully logged ADD_TO_CART event for product_id: {product_id}")
        
        cur.close()
        conn.close()
        return jsonify({"status": "success", "message": "Event logged"}), 200
    except Exception as e:
        logging.error(f"An error occurred during DB write operation: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

# NEW ENDPOINT FOR AGENTS
@app.route('/context', methods=['GET'])
def get_context():
    """Provides the last 10 'add to cart' events as context for agents."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
        
    try:
        # Using RealDictCursor makes the output a list of dictionaries (like JSON)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # This powerful query joins events with products to get meaningful context
        cur.execute("""
            SELECT 
                e.created_at, 
                e.product_id, 
                p.name as product_name
            FROM 
                events e
            JOIN 
                products p ON e.product_id = p.id
            WHERE
                e.event_type = 'ADD_TO_CART'
            ORDER BY 
                e.created_at DESC
            LIMIT 10;
        """)
        
        recent_events = cur.fetchall()
        cur.close()
        conn.close()
        
        logging.info(f"Fetched {len(recent_events)} events for context.")
        return jsonify(recent_events), 200
        
    except Exception as e:
        logging.error(f"An error occurred during DB read operation: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)