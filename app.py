import os
from flask import Flask, render_template, request, jsonify
import logging
import requests

# Setup logging
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__, static_url_path='/static')
app.secret_key = os.getenv("FLASK_SECRET_KEY") or "een_geheime_sleutel"

bpm_percentage = 0.377
btw_percentage = 0.21


def calculate_bpm(totale_cataloguswaarde,
                  brandstof_type,
                  afschrijving,
                  bruto_bpm=0):
    """Calculate BPM based on given parameters."""
    try:
        logging.debug("Starting BPM calculation with params:")
        logging.debug(f"totale_cataloguswaarde: {totale_cataloguswaarde}")
        logging.debug(f"brandstof_type: {brandstof_type}")
        logging.debug(f"afschrijving: {afschrijving}")
        logging.debug(f"bruto_bpm: {bruto_bpm}")
        # Convert to float and validate
        totale_cataloguswaarde = float(totale_cataloguswaarde)
        afschrijving = float(afschrijving)

        if totale_cataloguswaarde < 0 or afschrijving < 0 or afschrijving > 100:
            logging.error("Invalid input values detected")
            return None

        if bruto_bpm == 0:
            # Calculate netto cataloguswaarde and bruto BPM
            # total = net + 0.21net + 0.377net => total = net1.587 => net = total / 1.587
            netto_cataloguswaarde = totale_cataloguswaarde / (1 + bpm_percentage + btw_percentage)
            logging.debug(f"Calculated netto_cataloguswaarde (before BPM): {netto_cataloguswaarde}")
            bpm_base = netto_cataloguswaarde * bpm_percentage
        else:
            # Convert to float and validate
            bruto_bpm = float(bruto_bpm)
            if bruto_bpm < 0 or afschrijving < 0 or afschrijving > 100:
                logging.error("Invalid input values detected")
                return None
                # Calculate netto cataloguswaarde and bruto BPM
            # total = net + 0.21net + bruto_bpm => total - bruto_bpm = 1.21net => net = (total - bruto_bpm) / 1.21
            netto_cataloguswaarde = (totale_cataloguswaarde - bruto_bpm) / (1 + btw_percentage)
            bpm_base = bruto_bpm

        logging.debug(f"bpm_base: {bpm_base}")
        logging.debug(f"netto_cataloguswaarde: {netto_cataloguswaarde}")

        # Calculate initial BPM based on fuel type
        verhoogd_bedrag = 237 if brandstof_type == 'diesel' else -1283
        bpm = bpm_base + verhoogd_bedrag

        logging.debug("BPM calculation details:")
        logging.debug(f"verhoogd_bedrag: {verhoogd_bedrag}")
        logging.debug(f"Total BPM before depreciation: {bpm}")

        # Apply depreciation to calculate final BPM
        te_betalen = bpm - (bpm * (afschrijving / 100))
        logging.debug(f"Final te_betalen after {afschrijving}% depreciation: {te_betalen}")

        return {
            'netto_cataloguswaarde': round(netto_cataloguswaarde, 2),
            'verhoogd_bedrag': round(verhoogd_bedrag, 2),
            'bruto_bpm': round(bpm_base, 2),
            'te_betalen': round(te_betalen, 2)
        }
    except (ValueError, TypeError) as e:
        logging.error(f"Error in BPM calculation: {str(e)}")
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/lookup_kenteken', methods=['POST'])
def lookup_kenteken():
    try:
        data = request.get_json()
        kenteken = data.get('kenteken')

        if not kenteken:
            return jsonify({'error': 'Kenteken is required'}), 400

        # Clean up kenteken (remove dashes and spaces, convert to uppercase)
        kenteken = kenteken.replace('-', '').replace(' ', '').upper()

        # RDW API endpoint
        api_token = os.getenv('RDW_API_TOKEN')
        if not api_token:
            logging.error("RDW API token not found in environment variables")
            return jsonify({'error': 'API configuration error'}), 500

        headers = {'x-api-key': api_token, 'Accept': 'application/json'}

        # Log the API request
        logging.debug(f"Making request to RDW API for kenteken: {kenteken}")

        # Make request to RDW API
        response = requests.get(
            f'https://opendata.rdw.nl/resource/m9d7-ebf2.json?kenteken={kenteken}',
            headers=headers)

        # Log the response status and headers
        logging.debug(f"RDW API Response Status (vehicle data lookup): {response.status_code}")
        logging.debug(f"RDW API Response Headers (vehicle data lookup): {response.headers}")

        if response.status_code != 200:
            logging.error(f"RDW API error: {response.status_code} - {response.text}")
            return jsonify({'error': 'Failed to fetch vehicle data'}), response.status_code

        vehicle_data = response.json()

        # Log the complete response data for debugging
        logging.debug(f"RDW API Response Data (vehicle data lookup): {vehicle_data}")

        if not vehicle_data:
            logging.warning(f"No data found for kenteken: {kenteken}")
            return jsonify({'error': 'Kenteken not found'}), 404

        # Extract relevant data from API response
        cataloguswaarde = float(vehicle_data[0].get('catalogusprijs', 0))
        bruto_bpm = float(vehicle_data[0].get('bruto_bpm', 0))

        # Log the extracted data
        logging.debug(f"Extracted cataloguswaarde: {cataloguswaarde}")
        logging.debug(f"Extracted bruto_bpm: {bruto_bpm}")

        # Another request to find out the fuel type
        response_fuel = requests.get(
            f'https://opendata.rdw.nl/resource/8ys7-d773.json?kenteken={kenteken}',
            headers=headers)
        # Log the response status and headers
        logging.debug(f"RDW API Response Status (fuel type lookup): {response_fuel.status_code}")
        logging.debug(f"RDW API Response Headers (fuel type lookup): {response_fuel.headers}")

        if response_fuel.status_code != 200:
            logging.error(f"RDW API error: {response_fuel.status_code} - {response_fuel.text}")
            return jsonify({'error': 'Failed to fetch vehicle fuel type'}), response_fuel.status_code

        fuel_data = response_fuel.json()
        if not fuel_data:
            logging.warning(f"No fuel type found for kenteken: {kenteken}")
            return jsonify({'error': f'Fuel type not found for {kenteken}'}), 404

        # Extract relevant data from API response
        fuel_type = fuel_data[0].get('brandstof_omschrijving', 0)

        return jsonify(
            {'cataloguswaarde': cataloguswaarde, 'bruto_bpm': bruto_bpm, 'brandstof_omschrijving': fuel_type})

    except requests.RequestException as e:
        logging.error(f"Request error: {str(e)}")
        return jsonify({'error': 'Failed to connect to RDW API'}), 503
    except Exception as e:
        logging.error(f"Error looking up data: {str(e)}")
        return jsonify({'error': 'Failed to lookup RDW data'}), 500


@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        logging.debug(f"Received calculation request with data: {data}")

        # Validate required fields
        required_fields = ['cataloguswaarde', 'brandstof', 'afschrijving']
        if not all(field in data for field in required_fields):
            logging.error(f"Missing required fields in request: {data}")
            return jsonify({'error': 'Missing required fields'}), 400

        # Calculate BPM
        result = calculate_bpm(data['cataloguswaarde'], data['brandstof'],
                               data['afschrijving'], data.get('bruto_bpm', 0))

        if result is None:
            logging.error("BPM calculation returned None")
            return jsonify({'error': 'Invalid input values'}), 400

        logging.debug(f"Calculation result: {result}")
        return jsonify(result)

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
