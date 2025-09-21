import os
import logging
from flask import Flask, request, jsonify
import google.generativeai as genai

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    logging.info("Gemini client configured successfully.")
except KeyError:
    logging.error("🔴 FATAL: GOOGLE_API_KEY environment variable not set.")
    exit()

@app.route('/goal', methods=['POST'])
def handle_a2a_goal():
    """Receives and processes a goal from another agent."""
    
    a2a_message = request.get_json()
    logging.info(f"Received A2A message: {a2a_message}")

    if not a2a_message or a2a_message.get("goal") != "create_promotional_content":
        logging.warning("Received an invalid or irrelevant goal.")
        return jsonify({"status": "error", "message": "Invalid goal"}), 400

    try:
        product_name = a2a_message['payload']['product_name']
        tone = a2a_message['payload']['tone']

        prompt = f"""
        You are a creative marketing assistant for an online boutique.
        Your task is to write a short, punchy promotional headline for a product that is currently trending.

        Product: {product_name}
        Required Tone: {tone}

        Generate one headline only.
        """

        logging.info(f"Generating ad copy for: {product_name}")
        response = model.generate_content(prompt)
        
        ad_copy = response.text.strip()
        
        logging.info("--- GENERATED MARKETING CONTENT ---")
        logging.info(ad_copy)
        logging.info("---------------------------------")
        
        return jsonify({"status": "success", "ad_copy": ad_copy}), 200

    except Exception as e:
        logging.error(f"🔴 An error occurred while processing the goal: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)