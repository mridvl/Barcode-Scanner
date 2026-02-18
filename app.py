from flask import Flask, Response, render_template, redirect, url_for, session, jsonify, request
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import base64
import logging
import json
import os
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "barcode_scanner_secret_key"

# API endpoints and keys
OPEN_FOOD_FACTS_API = "https://world.openfoodfacts.org/api/v0/product/{}.json"
NUTRITIONIX_API_ENDPOINT = "https://trackapi.nutritionix.com/v2/search/item"
NUTRITIONIX_APP_ID = "your_nutritionix_app_id"  # Replace with your actual App ID
NUTRITIONIX_API_KEY = "your_nutritionix_api_key"  # Replace with your actual API key

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect_barcode', methods=['POST'])
def detect_barcode():
    try:
        # Get the image data from the request
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'error': 'No image data received'}), 400
        
        # Remove the data URL prefix and decode base64
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode the base64 image
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({'error': 'Failed to decode image'}), 400
        
        # Process the image for barcode detection
        barcodes = decode(img)
        results = []
        
        for barcode in barcodes:
            # Decode barcode data
            data = barcode.data.decode('utf-8')
            barcode_type = barcode.type
            
            # Get polygon points
            polygon_points = []
            for point in barcode.polygon:
                polygon_points.append({'x': int(point.x), 'y': int(point.y)})
            
            # Get rectangle coordinates
            rect = {
                'x': barcode.rect.left,
                'y': barcode.rect.top,
                'width': barcode.rect.width,
                'height': barcode.rect.height
            }
            
            results.append({
                'data': data,
                'type': barcode_type,
                'polygon': polygon_points,
                'rect': rect
            })
        
        if results:
            # Store the first barcode data in session
            session['barcode_data'] = results[0]['data']
            return jsonify({'detected': True, 'results': results})
        else:
            return jsonify({'detected': False})
            
    except Exception as e:
        logger.error(f"Error in barcode detection: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/result')
def result():
    # Get barcode data from session
    barcode_data = session.get('barcode_data', None)
    
    if barcode_data:
        # Try to fetch product information from APIs
        product_info = fetch_product_info(barcode_data)
        
        if product_info:
            # Calculate percentage of daily values for the template
            sugar_percentage = min(product_info['nutrition']['added_sugar'] / 25 * 100, 100)
            trans_fat_percentage = min(product_info['nutrition']['trans_fat'] / 2 * 100, 100)
            
            return render_template('product_info.html', 
                                  barcode=barcode_data,
                                  product=product_info,
                                  sugar_percentage=sugar_percentage,
                                  trans_fat_percentage=trans_fat_percentage)
        else:
            # Product not found in any API
            return render_template('not_found.html', barcode=barcode_data)
    else:
        return redirect(url_for('index'))

def fetch_product_info(barcode):
    """
    Fetch product information from multiple APIs.
    Try Open Food Facts first, then Nutritionix as a backup.
    """
    try:
        # First try Open Food Facts (free and no API key needed)
        off_product = fetch_from_open_food_facts(barcode)
        if off_product:
            return off_product
            
        # If not found in Open Food Facts, try Nutritionix
        nutritionix_product = fetch_from_nutritionix(barcode)
        if nutritionix_product:
            return nutritionix_product
            
        # If product not found in any API
        return None
            
    except Exception as e:
        logger.error(f"Error fetching product info: {str(e)}")
        return None

def fetch_from_open_food_facts(barcode):
    """
    Fetch product information from Open Food Facts API with enhanced nutritional data
    """
    try:
        url = OPEN_FOOD_FACTS_API.format(barcode)
        response = requests.get(url)
        data = response.json()
        
        if data.get('status') == 1 and data.get('product'):
            product = data['product']
            
            # Extract nutrition data
            nutrients = product.get('nutriments', {})
            
            # Check processing level - NOVA classification system from Open Food Facts
            nova_group = product.get('nova_group', None)
            processing_level = "Unknown"
            if nova_group == 1:
                processing_level = "Unprocessed"
            elif nova_group == 2:
                processing_level = "Processed Culinary Ingredients"
            elif nova_group == 3:
                processing_level = "Processed"
            elif nova_group == 4:
                processing_level = "Ultra-Processed"
            
            # Extract additives
            additives_count = 0
            if 'additives_tags' in product:
                additives_count = len(product['additives_tags'])
            
            # Build enhanced product info structure
            product_info = {
                "name": product.get('product_name', 'Unknown Product'),
                "brand": product.get('brands', 'Unknown Brand'),
                "image_url": product.get('image_url', ''),
                "processing_level": processing_level,
                "additives_count": additives_count,
                "nutrition": {
                    "serving_size": product.get('serving_size', 'N/A'),
                    "calories": nutrients.get('energy-kcal_100g', nutrients.get('energy-kcal', 0)),
                    "fat": nutrients.get('fat_100g', 0),
                    "saturated_fat": nutrients.get('saturated-fat_100g', 0),
                    "trans_fat": nutrients.get('trans-fat_100g', 0),
                    "sodium": nutrients.get('sodium_100g', 0) * 1000,  # Convert to mg
                    "carbs": nutrients.get('carbohydrates_100g', 0),
                    "fiber": nutrients.get('fiber_100g', 0),
                    "sugar": nutrients.get('sugars_100g', 0),
                    "added_sugar": nutrients.get('added_sugars_100g', 
                                               nutrients.get('sugars_100g', 0) * 0.5),  # Estimate if not available
                    "protein": nutrients.get('proteins_100g', 0)
                },
                "nutrition_score": {
                    "score": product.get('nutriscore_score', 0),
                    "grade": product.get('nutriscore_grade', 'C'),
                    "value": float(2.0),  # Default value if not available
                    "label": "Poor"       # Default label if not available
                }
            }
            
            # Set nutrition score label based on grade if available
            if product_info['nutrition_score']['grade']:
                grade = product_info['nutrition_score']['grade'].upper()
                if grade == 'A':
                    product_info['nutrition_score']['value'] = 5.0
                    product_info['nutrition_score']['label'] = "Excellent"
                elif grade == 'B':
                    product_info['nutrition_score']['value'] = 4.0
                    product_info['nutrition_score']['label'] = "Good"
                elif grade == 'C':
                    product_info['nutrition_score']['value'] = 3.0
                    product_info['nutrition_score']['label'] = "Average"
                elif grade == 'D':
                    product_info['nutrition_score']['value'] = 2.0
                    product_info['nutrition_score']['label'] = "Poor"
                elif grade == 'E':
                    product_info['nutrition_score']['value'] = 1.0
                    product_info['nutrition_score']['label'] = "Bad"
            
            return product_info
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching from Open Food Facts: {str(e)}")
        return None


def fetch_from_nutritionix(barcode):
    """
    Fetch product information from Nutritionix API with enhanced nutritional data
    """
    try:
        # Skip if API keys aren't set
        if not NUTRITIONIX_APP_ID or not NUTRITIONIX_API_KEY or NUTRITIONIX_APP_ID == "your_nutritionix_app_id":
            return None
            
        headers = {
            'x-app-id': NUTRITIONIX_APP_ID,
            'x-app-key': NUTRITIONIX_API_KEY,
            'Content-Type': 'application/json'
        }
        
        data = {
            'upc': barcode
        }
        
        response = requests.post(NUTRITIONIX_API_ENDPOINT, headers=headers, json=data)
        result = response.json()
        
        if 'foods' in result and len(result['foods']) > 0:
            food = result['foods'][0]
            
            # Estimate processing level based on ingredients count (simplified)
            processing_level = "Unknown"
            ingredients_list = food.get('nf_ingredient_statement', '')
            ingredients_count = len(ingredients_list.split(',')) if ingredients_list else 0
            
            if ingredients_count <= 3:
                processing_level = "Unprocessed"
            elif ingredients_count <= 5:
                processing_level = "Processed"
            else:
                processing_level = "Ultra-Processed"
            
            # Estimate additives count based on ingredient names (simplified)
            additives_count = 0
            common_additives = ['acid', 'agent', 'artificial', 'color', 'dye', 'e-', 'emulsifier', 
                               'flavor', 'gum', 'preservative', 'stabilizer', 'sweetener']
            
            for additive in common_additives:
                if additive in ingredients_list.lower():
                    additives_count += 1
            
            # Estimate added sugar (50% of total sugars as a fallback)
            total_sugar = food.get('nf_sugars', 0)
            added_sugar = total_sugar * 0.5
            
            # Set trans fat (may not be available in all cases)
            trans_fat = food.get('nf_trans_fatty_acid', 0.1)
            
            # Build enhanced product info structure
            product_info = {
                "name": food.get('food_name', 'Unknown Product'),
                "brand": food.get('brand_name', 'Unknown Brand'),
                "image_url": food.get('photo', {}).get('highres', ''),
                "processing_level": processing_level,
                "additives_count": additives_count,
                "nutrition": {
                    "serving_size": f"{food.get('serving_qty', '')} {food.get('serving_unit', '')}",
                    "calories": food.get('nf_calories', 0),
                    "fat": food.get('nf_total_fat', 0),
                    "saturated_fat": food.get('nf_saturated_fat', 0),
                    "trans_fat": trans_fat,
                    "sodium": food.get('nf_sodium', 0),
                    "carbs": food.get('nf_total_carbohydrate', 0),
                    "fiber": food.get('nf_dietary_fiber', 0),
                    "sugar": food.get('nf_sugars', 0),
                    "added_sugar": added_sugar,
                    "protein": food.get('nf_protein', 0)
                },
                "nutrition_score": {
                    "score": 0,
                    "grade": "C",
                    "value": 2.0,
                    "label": "Poor"
                }
            }
            
            # Simple scoring calculation based on nutritional qualities
            score = 0
            if food.get('nf_sugars', 0) < 5:
                score += 1
            if food.get('nf_saturated_fat', 0) < 2:
                score += 1
            if food.get('nf_sodium', 0) < 400:
                score += 1
            if food.get('nf_dietary_fiber', 0) > 3:
                score += 1
            if food.get('nf_protein', 0) > 5:
                score += 1
                
            # Set nutrition score based on simple calculation
            if score >= 4:
                product_info['nutrition_score']['value'] = 5.0
                product_info['nutrition_score']['label'] = "Excellent"
                product_info['nutrition_score']['grade'] = "A"
            elif score == 3:
                product_info['nutrition_score']['value'] = 4.0
                product_info['nutrition_score']['label'] = "Good"
                product_info['nutrition_score']['grade'] = "B"
            elif score == 2:
                product_info['nutrition_score']['value'] = 3.0
                product_info['nutrition_score']['label'] = "Average"
                product_info['nutrition_score']['grade'] = "C"
            elif score == 1:
                product_info['nutrition_score']['value'] = 2.0
                product_info['nutrition_score']['label'] = "Poor"
                product_info['nutrition_score']['grade'] = "D"
            else:
                product_info['nutrition_score']['value'] = 1.0
                product_info['nutrition_score']['label'] = "Bad"
                product_info['nutrition_score']['grade'] = "E"
            
            return product_info
            
        return None
        
    except Exception as e:
        logger.error(f"Error fetching from Nutritionix: {str(e)}")
        return None

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    # This function is no longer needed but kept for backward compatibility
    # It could be repurposed to let users submit product information to Open Food Facts
    return redirect(url_for('index'))

if __name__ == '__main__':
    logger.info("Starting nutrition scanner application")
    app.run(debug=True, host='0.0.0.0')