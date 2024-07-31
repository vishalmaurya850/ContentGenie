from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
import os
import csv
import pandas as pd
from flask_cors import CORS
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='build/static', template_folder='build')
bcrypt=Bcrypt(app)
CORS(app)
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
users_csv='data/users.csv'
CSV_FILE_PATH='data/personaliai.csv'

client = AzureOpenAI(api_key=AZURE_OPENAI_KEY, azure_endpoint=AZURE_OPENAI_ENDPOINT, api_version='2024-05-13')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required"}), 400
        
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    if not os.path.exists(users_csv):
        df = pd.DataFrame(columns=['email', 'password'])
    else:
        df = pd.read_csv(users_csv)

    if email in df['email'].values:
        return jsonify({"error": "Username already exists"}), 400

    new_user = pd.DataFrame([[email, hashed_password]], columns=['email', 'password'])
    df=df._append(new_user, ignore_index=True)
    df.to_csv(users_csv, index=False)

    return jsonify({"message": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password are required"}), 400

    df = pd.read_csv(users_csv)
    user = df[df['email'] == email]
    if user.empty or not bcrypt.check_password_hash(user.iloc[0]['password'], password):
        return jsonify({"error": "Invalid username or password"}), 400

    return jsonify({"message": "Login successful"}), 200

@app.route('/generate_content', methods=['POST'])
def generate_content():
    data = request.get_json()
    customer_id = data.get('customer_id')

    if not customer_id:
        return jsonify({"error": "customer_id is required"}), 400

    df=pd.read_csv('data/personaliai.csv')
    customer = df[df['customer_id']==customer_id]

    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    
    with open("data/personaliai.csv","r") as source:
        reader = csv.reader(source)
        data = []
        for row in reader:
            data.append(row)
    customer_name=data[customer_id][2]
    preferences=data[customer_id][3]
    purchase_history=data[customer_id][4]

    prompt = f"Generate personalized content for customer {customer_name} who has preferences: {preferences} and purchase_history of items: {purchase_history} in 200 lines of structured format."
    response = client.chat.completions.create(
        model="gpt-4o",
        prompt=prompt,
        max_tokens=200
    )
    content=response.choices[0].text
        
    return jsonify({"content": content}), 200

if __name__ == '__main__':
    app.run(debug=True)