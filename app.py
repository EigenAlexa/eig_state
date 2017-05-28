from flask import Flask

app = Flask("eig_state_manager")

@app.route('/')
def hello():
    return 'Hello world'

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8080)
