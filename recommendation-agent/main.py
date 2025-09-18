# main.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import grpc

# --- NEW: Import CORS Middleware ---
from fastapi.middleware.cors import CORSMiddleware
# ------------------------------------

# Import the generated gRPC client stubs we created
import pb.demo_pb2 as demo_pb2
import pb.demo_pb2_grpc as demo_pb2_grpc

# --- Gemini API Configuration ---
# The API key is read from the environment variable set by the Kubernetes secret.
try:
    api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except KeyError:
    raise RuntimeError("GEMINI_API_KEY environment variable not set.")
# --------------------------------

# The internal gRPC address for the product catalog service
PRODUCT_CATALOG_SERVICE_ADDR = "productcatalogservice:3550"

# --- Dynamic Product List ---
# This will be populated on startup by the gRPC sync.
VALID_PRODUCT_NAMES = []
# -----------------------------

app = FastAPI()

# --- NEW: Add the CORS Middleware to the app ---
# This allows any origin (*) to make requests, which is perfect for our demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------------------------

@app.on_event("startup")
def sync_product_catalog():
    """
    On startup, make a gRPC call to the productcatalogservice to get all products.
    """
    print("Syncing product catalog via gRPC...")
    try:
        # Establish a gRPC channel to the product catalog service
        channel = grpc.insecure_channel(PRODUCT_CATALOG_SERVICE_ADDR)
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
        
        # Make the ListProducts RPC call with an Empty request message
        response = stub.ListProducts(demo_pb2.Empty())
        
        # Populate the list with the names from the response
        global VALID_PRODUCT_NAMES
        VALID_PRODUCT_NAMES = [p.name for p in response.products]
        
        if VALID_PRODUCT_NAMES:
            print(f"Successfully synced {len(VALID_PRODUCT_NAMES)} products.")
        else:
            print("Warning: Product catalog sync resulted in an empty list.")
    except Exception as e:
        print(f"FATAL: Could not sync product catalog on startup: {e}")

# Pydantic model for the request body
class RecommendRequest(BaseModel):
    session_id: str
    viewed_products: list[str]

def get_product_from_catalog(product_name: str) -> dict:
    """Makes a gRPC call to the productcatalogservice to search for a product."""
    try:
        channel = grpc.insecure_channel(PRODUCT_CATALOG_SERVICE_ADDR)
        stub = demo_pb2_grpc.ProductCatalogServiceStub(channel)
        
        # Create the request object for the SearchProducts RPC
        search_request = demo_pb2.SearchProductsRequest(query=product_name)
        response = stub.SearchProducts(search_request)

        if not response.results:
            return None
            
        # Convert the protobuf Product object to a dictionary for the JSON response
        product = response.results[0]
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "picture": product.picture,
            "priceUsd": {
                "currencyCode": product.price_usd.currency_code,
                "units": product.price_usd.units,
                "nanos": product.price_usd.nanos
            }
        }
    except Exception as e:
        print(f"Error calling product catalog service: {e}")
        return None

@app.get("/health", status_code=200)
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "Recommendation agent is healthy"}

@app.post("/recommend")
def get_recommendation(request: RecommendRequest):
    """
    Receives user context, gets a recommendation from Gemini, and fetches its details.
    """
    if not request.viewed_products:
        raise HTTPException(status_code=400, detail="Viewed products list cannot be empty.")
    if not VALID_PRODUCT_NAMES:
        raise HTTPException(status_code=503, detail="Product catalog not available. Please try again later.")

    product_list_str = ", ".join(request.viewed_products)
    valid_names_str = ", ".join(VALID_PRODUCT_NAMES)
    prompt = (
        "You are an expert e-commerce sales assistant. "
        f"A customer is interested in the following items: [{product_list_str}]. "
        f"From the following list of available products, recommend one single complementary product: [{valid_names_str}]. "
        "Return only the exact name of the product from the list, and nothing else."
    )
    try:
        response = model.generate_content(prompt)
        recommended_product_name = response.text.strip()

        product_details = get_product_from_catalog(recommended_product_name)

        if not product_details:
             raise HTTPException(status_code=404, detail=f"Recommended product '{recommended_product_name}' not found in catalog.")

        return {"recommended_product": product_details}
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendation.")

