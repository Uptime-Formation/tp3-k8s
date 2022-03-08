from flask import Flask, Response, request
from flask import jsonify
import requests
import hashlib
import redis
import socket

app = Flask(__name__)
redis_cache = redis.StrictRedis(host='redis', port=6379, socket_connect_timeout=2, socket_timeout=2, db=0)
salt = "UNIQUE_SALT"
default_name = 'John Doe'

@app.route('/', methods=['GET', 'POST'])
def mainpage():

    try:
        visits = redis_cache.incr("counter")
    except redis.RedisError:
        visits = "<i>cannot connect to Redis, counter disabled</i>"

    name = default_name
    if request.method == 'POST':
        name = request.form['name']
    salted_name = salt + name
    name_hash = hashlib.sha256(salted_name.encode()).hexdigest()

    page = '''
        <html>
          <head>
            <title>Monster Icon</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/skeleton/2.0.4/skeleton.css">
          </head>
          <body style="text-align: center">
                <h1>Monster Icon</h1>
                <form method="POST">
                <strong>Hello dear <input type="text" name="name" value="{name}">
                <input type="submit" value="submit"> !
                </form>
                <div>
                  <h4>Here is your monster icon :</h4>
                  <img src="/monster/{name_hash}"/>
                <div>

          </br></br><h4> container info: </h4>
          <ul>
           <li>Hostname: {hostname}</li>
           <li>Visits: {visits} </li>
          </ul></strong>
        </body>
       </html>
    '''.format(name=name, name_hash=name_hash, hostname=socket.gethostname(), visits=visits)

    return page


@app.route('/monster/<name>')
def get_identicon(name):
    image = redis_cache.get(name)
    if image is None:
        print ("Cache miss: picture icon not found in Redis", flush=True)
        r = requests.get('http://dnmonster:8080/monster/' + name + '?size=80')
        image = r.content
    redis_cache.set(name, image)

    return Response(image, mimetype='image/png')

@app.route('/healthz')
def healthz():
    data = {'ready': 'true'}
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

