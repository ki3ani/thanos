import os
import requests
import json
import logging
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BusinessAnalystAgent:
    def __init__(self):
        """Initializes the agent, its tools, and the LLM."""
        try:
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logging.info("Gemini client configured successfully.")
        except KeyError:
            logging.error("🔴 FATAL: GOOGLE_API_KEY environment variable not set.")
            exit()
            
        self.mcp_server_url = os.environ.get("MCP_SERVER_URL", "http://mcp-toolbox-service:8080/context")
        self.marketing_agent_url = os.environ.get("MARKETING_AGENT_URL", "http://marketing-campaigner-service:8080/goal")

    def tool_fetch_mcp_context(self):
        """This is the agent's 'tool' for getting data."""
        logging.info(f"Fetching context from MCP server at {self.mcp_server_url}...")
        try:
            response = requests.get(self.mcp_server_url, timeout=10)
            response.raise_for_status()
            logging.info("✅ Context received successfully!")
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"🔴 Error fetching context: {e}")
            return None

    def send_a2a_goal(self, product_name):
        """Sends a goal to the Marketing agent via the A2A protocol."""
        a2a_message = {
            "a2a_version": "0.1",
            "from_agent": "business-analyst",
            "to_agent": "marketing-campaigner",
            "goal": "create_promotional_content",
            "payload": {
                "product_name": product_name,
                "reason": "High recent add-to-cart velocity detected.",
                "tone": "Exciting and urgent"
            }
        }
        logging.info(f"Sending A2A goal to Marketing agent: {a2a_message}")
        try:
            # In a real system, the Marketing agent would be listening at this URL
            response = requests.post(self.marketing_agent_url, json=a2a_message, timeout=10)
            response.raise_for_status()
            logging.info("✅ A2A goal sent successfully!")
        except requests.exceptions.RequestException as e:
            # We log an error but don't crash, as the Marketing agent might not be deployed yet.
            logging.error(f"🔴 Could not send A2A goal to Marketing agent: {e}")

    def run(self):
        """The main sense-think-act loop for the agent."""
        # 1. SENSE: Get the latest data from the environment
        context_data = self.tool_fetch_mcp_context()
        if not context_data:
            logging.info("Agent cannot proceed without data. Shutting down.")
            return

        # 2. THINK: Use the LLM to analyze the data and decide on an action
        context_json_string = json.dumps(context_data, indent=2)
        prompt = f"""
        Analyze the following JSON data of recent 'add to cart' events. Your task is to identify if a single product is trending. A product is 'trending' if it appears 3 or more times in this list.

        If a product is trending, respond with a simple JSON object:
        {{"is_trending": true, "product_name": "Name of the Product"}}

        If no product appears 3 or more times, respond with:
        {{"is_trending": false, "product_name": null}}

        Here is the data:
        ```json
        {context_json_string}
        ```
        """

        logging.info("Sending data to Gemini for trend analysis...")
        try:
            response = self.model.generate_content(prompt)
            # Clean up the response to get valid JSON
            analysis_text = response.text.strip().replace("```json", "").replace("```", "")
            analysis_result = json.loads(analysis_text)
            logging.info(f"Analysis result: {analysis_result}")
        except Exception as e:
            logging.error(f"🔴 Failed to analyze data with Gemini: {e}")
            return
            
        # 3. ACT: Based on the analysis, delegate a task to another agent
        if analysis_result.get("is_trending"):
            product = analysis_result.get("product_name")
            logging.info(f"Trend detected for product: {product}. Delegating to Marketing agent.")
            self.send_a2a_goal(product)
        else:
            logging.info("No significant trends detected. No action needed.")

if __name__ == "__main__":
    agent = BusinessAnalystAgent()
    agent.run()