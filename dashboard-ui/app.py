import os
import requests
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# The internal Kubernetes addresses for our services
MCP_SERVER_URL = "http://mcp-toolbox-service:8080/context"
MARKETING_AGENT_URL = "http://marketing-campaigner-service:8080/latest_ad"
RECOMMENDATION_AGENT_URL = "http://recommendationservice:5001/latest_recommendation"

@app.route('/')
def index():
    """Serves the main HTML dashboard page."""
    return render_template('index.html')

@app.route('/data')
def get_data():
    """An API endpoint that the webpage calls to get the latest data from all agents."""
    
    # --- Fetch data from the MCP Server ---
    mcp_context = []
    try:
        mcp_response = requests.get(MCP_SERVER_URL, timeout=2)
        if mcp_response.ok:
            mcp_context = mcp_response.json()
    except requests.exceptions.RequestException:
        # If the service is down, we just return an empty list
        pass

    # --- Fetch data from the Marketing Agent ---
    latest_ad = {"product_name": "Error", "ad_copy": "Could not connect to Marketing Agent"}
    try:
        marketing_response = requests.get(MARKETING_AGENT_URL, timeout=2)
        if marketing_response.ok:
            latest_ad = marketing_response.json()
    except requests.exceptions.RequestException:
        pass

    # --- Fetch data from the Recommendation Agent ---
    latest_rec = {"input_cart_ids": [], "output_product_names": ["Connecting..."]}
    try:
        rec_response = requests.get(RECOMMENDATION_AGENT_URL, timeout=2)
        if rec_response.ok:
            latest_rec = rec_response.json()
    except requests.exceptions.RequestException:
        pass
    
    # --- Combine all data into a single response ---
    return jsonify({
        "mcp_context": mcp_context,
        "latest_ad": latest_ad,
        "latest_rec": latest_rec
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
