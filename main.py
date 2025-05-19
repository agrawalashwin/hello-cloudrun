from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'I am so so so excited to see you here. you will see a lot more changes'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

