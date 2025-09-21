import os
import logging
from flask import Flask, request, jsonify
import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# --- CONFIGURE THE GEMINI CLIENT ---
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    logging.info("Gemini client configured successfully.")
except KeyError:
    logging.error("🔴 FATAL: GOOGLE_API_KEY environment variable not set.")
    exit()

# --- DATABASE CONNECTION FUNCTION ---
def get_db_connection():
    try:
        # Connect to the DB via the Cloud SQL Proxy sidecar
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST', '127.0.0.1'),
            database=os.environ.get('DB_NAME', 'postgres'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD')
        )
        return conn
    except Exception as e:
        logging.error(f"🔴 Error connecting to the database: {e}")
        return None

@app.route('/goal', methods=['POST'])
def handle_a2a_goal():
    """Receives a goal, generates ad copy, and publishes it to the database."""
    a2a_message = request.get_json()
    logging.info(f"Received A2A message: {a2a_message}")

    if not a2a_message or a2a_message.get("goal") != "create_promotional_content":
        return jsonify({"status": "error", "message": "Invalid goal"}), 400

    try:
        product_name = a2a_message['payload']['product_name']
        tone = a2a_message['payload']['tone']

        prompt = f"You are a creative marketing assistant. Write one short, punchy promotional headline for the product '{product_name}'. The tone must be: {tone}."
        logging.info(f"Generating ad copy for: {product_name}")
        response = model.generate_content(prompt)
        ad_copy = response.text.strip().replace("*","")

        logging.info(f"Publishing ad copy to database: '{ad_copy}'")
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO published_ads (product_name, ad_copy) VALUES (%s, %s);",
                (product_name, ad_copy)
            )
            conn.commit()
            cur.close()
            conn.close()
            logging.info("✅ Ad copy successfully published to database!")
        else:
            logging.error("🔴 Failed to publish ad copy due to DB connection error.")
            return jsonify({"status": "error", "message": "Could not connect to DB to publish content"}), 500
        
        return jsonify({"status": "success", "published_ad_copy": ad_copy}), 200

    except Exception as e:
        logging.error(f"🔴 An error occurred while processing the goal: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/latest_ad', methods=['GET'])
def get_latest_ad():
    """Provides the most recently generated ad campaign."""
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT product_name, ad_copy, created_at FROM published_ads ORDER BY created_at DESC LIMIT 1;")
        latest_ad = cur.fetchone()
        cur.close()
        conn.close()
        
        if latest_ad:
            if latest_ad.get('created_at'):
                latest_ad['created_at'] = latest_ad['created_at'].isoformat()
            return jsonify(latest_ad), 200
        else:
            return jsonify({"product_name": "None", "ad_copy": "No campaign active yet."}), 200
    except Exception as e:
        logging.error(f"🔴 Error fetching latest ad: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)