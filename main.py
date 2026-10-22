from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>COMS W4111 Cloud Run Test</h1><p>It works!</p>"
