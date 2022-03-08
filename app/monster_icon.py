from flask import Flask, Response, request, abort, jsonify
import requests
import hashlib
import socket
import redis
import os
import logging

LOGLEVEL = os.environ.get("LOGLEVEL", "INFO").upper()
logging.basicConfig(level=LOGLEVEL)

app = Flask(__name__)
cache = redis.StrictRedis(host="redis", port=6379, db=0)
salt = "UNIQUE_SALT"
default_name = "toi"


@app.route("/", methods=["GET", "POST"])
def mainpage():

    name = default_name
    if request.method == "POST":
        name = request.form["name"]

    try:
        visits = cache.incr("counter")
    except redis.RedisError:
        visits = "&#128565;"  # 😵
        logging.warning("Cache redis injoignable, compteur désactivé")

    salted_name = salt + name
    name_hash = hashlib.sha256(salted_name.encode()).hexdigest()
    header = "<html><head><title>Identidock</title></head><body>"
    body = """<form method="POST">
                Salut <input type="text" name="name" value="{name}"> !
                <input type="submit" value="submit">
                </form>
                <p>Tu ressembles à ça :
                <img src="/monster/{name_hash}"/>
                </p>
                <br>
               """.format(
        name=name, name_hash=name_hash
    )

    footer = """ <h4>Infos container :</h4>
          <ul>
           <li>Hostname: {hostname}</li>
           <li>Visits: {visits}</li>
          </ul>
        </body></html>
        """.format(
        hostname=socket.gethostname(), visits=visits
    )
    return header + body + footer


@app.route("/monster/<name>")
def get_identicon(name):
    found_in_cache = False

    try:
        image = cache.get(name)
        redis_unreachable = False
        if image is not None:
            found_in_cache = True
            logging.info("Image trouvée dans le cache")
    except:
        redis_unreachable = True
        logging.warning("Cache redis injoignable")

    if not found_in_cache:
        logging.info("Image non trouvée dans le cache")
        try:
            r = requests.get("http://dnmonster:8080/monster/" + name + "?size=80")
            image = r.content
            logging.info("Image générée grâce au service dnmonster")

            if not redis_unreachable:
                cache.set(name, image)
                logging.info("Image enregistrée dans le cache redis")
        except:
            logging.critical("Le service dnmonster est injoignable !")
            abort(503)

    return Response(image, mimetype="image/png")


@app.route("/healthz")
def healthz():
    try:
        requests.get("http://dnmonster:8080/monster/test?size=80")
        dnmonster_ready = True
    except:
        logging.critical("Le service dnmonster est injoignable !")
        dnmonster_ready = False

    try:
        cache.incr("test")
        redis_ready = True
    except redis.RedisError:
        logging.warning("Le cache redis est injoignable !")
        redis_ready = False

    monstericon_ready = dnmonster_ready
    data = {
        "monstericon_ready": str(monstericon_ready),
        "dnmonster_ready": str(dnmonster_ready),
        "redis_ready": str(redis_ready),
    }
    
    return jsonify(data), 200 if monstericon_ready else 503


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
