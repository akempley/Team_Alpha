from flask import Flask
app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

if __name__ == '__main__':
    app.run()


# App metadata
APP_NAME = "Movie Archiver"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "A web application that archives and reccomends movies"

