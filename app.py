from flask import Flask
<<<<<<< HEAD
app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

if __name__ == '__main__':
    app.run()
=======

app = Flask(__name__)

# App metadata
APP_NAME = "Movie Archiver"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "A web application that archives and reccomends movies"

@app.route("/")
def home():
    return "Hello Team Alpha!"

if __name__ == "__main__":
    app.run(debug=True)
>>>>>>> main
