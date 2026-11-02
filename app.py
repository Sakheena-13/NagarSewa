import os
import json
from flask import Flask, render_template,request,jsonify,send_from_directory
from google import genai
from google.genai import types
from supabase import create_client, Client

app = Flask(__name__)

# Folder to save uploaded images locally
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# -------------------------------------------------------------
# 1. CONFIGURATION (Replace with your actual keys)
# -------------------------------------------------------------
GEMINI_API_KEY = "AQ.Ab8RN6KMt58v9SRf9qtUg6TICh0qZzYN8pv7fHkPEV61QxOx0A"
SUPABASE_URL = "https://zurqnyapycanhccfaxpr.supabase.co/rest/v1/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp1cnFueWFweWNhbmhjY2ZheHByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTM2Mjc5NzksImV4cCI6MjEwOTIwMzk3OX0.1hrz6BIXod8RpICO3mOK4Bj280q20rqqzBiVu5om7Tc"

# Initialize Gemini AI Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# -------------------------------------------------------------
# 2. ROUTES / ENDPOINTS
# -------------------------------------------------------------

# Main route to display frontend webpage
@app.route('/')
def home():
    return send_from_directory('templates', 'index.html')



# Endpoint to handle photo upload, AI analysis, and Supabase database entry
@app.route('/analyze-hazard', methods=['POST'])
def analyze_hazard():
    try:
        # Get uploaded image file and GPS location from request
        image_file = request.files.get('image')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        if not image_file:
            return jsonify({"error": "No image uploaded"}), 400

        # Save image locally inside 'static/uploads/'
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file.filename)
        image_file.save(image_path)

        # --- CALL GOOGLE GEMINI VISION API ---
        with open(image_path, 'rb') as img_f:
            image_bytes = img_f.read()

        prompt = """
        Analyze this image carefully. Is it a road or civic hazard (such as a Pothole, Open Drain, Garbage Dump, or Damaged Streetlight)?
        Respond ONLY with a valid JSON object in this exact format:
        {
            "is_hazard": true,
            "category": "Pothole",
            "severity": 4,
            "description": "Deep dangerous pothole on road."
        }
        """

        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                prompt
            ]
        )

        # Clean JSON text response from AI
        clean_text = response.text.replace('```json', '').replace('```', '').strip()
        ai_data = json.loads(clean_text)

        # --- SAVE ENTRY TO SUPABASE DATABASE ---
        report_data = {
            "category": ai_data.get("category", "Unknown Hazard"),
            "severity": ai_data.get("severity", 3),
            "description": ai_data.get("description", ""),
            "latitude": float(latitude) if latitude else 0.0,
            "longitude": float(longitude) if longitude else 0.0,
            "image_url": f"/{image_path}"
        }

        db_response = supabase.table('reports').insert(report_data).execute()

        return jsonify({
            "status": "success",
            "ai_result": ai_data,
            "db_entry": db_response.data
        })

    except Exception as e:
        print("Error processing request:", str(e))
        return jsonify({"error": str(e)}), 500


# Endpoint to fetch all reports from Supabase to plot on the Leaflet Map
@app.route('/get-reports', methods=['GET'])
def get_reports():
    try:
        # Fetch all rows from your Supabase table
        response = supabase.table("reports").select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        print("Error fetching reports:", str(e))
        return jsonify([]), 500



if __name__ == '__main__':
    # Run Flask server locally
    app.run(debug=True, port=5001)