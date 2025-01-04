from config import args
from flask import Flask
from flask_restful import Api
from resources import (
    CalculateMultiplicativeShare,
    CalculateR,
    Reset,
    SendR,
    SetInitialValues,
    SetR,
    SetShares,
)

app = Flask(__name__)
api = Api(app)

api.add_resource(SetInitialValues, "/api/set-initial-values/")
api.add_resource(SetShares, "/api/set-shares/")
api.add_resource(CalculateR, "/api/calculate-r/")
api.add_resource(SetR, "/api/set-r/")
api.add_resource(SendR, "/api/send-r/")
api.add_resource(CalculateMultiplicativeShare, "/api/calculate-multiplicative-share/")
api.add_resource(Reset, "/api/reset/")


@app.route("/")
def home():
    return "<h1>Aukciszek API</h1>"


if __name__ == "__main__":
    app.run(port=args.port, debug=True)
