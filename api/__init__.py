from config import args
from flask import Flask
from flask_restful import Api
from resources import (
    CalculateMultiplicativeShare,
    CalculateR,
    FactoryReset,
    Reset,
    ResonstructSecret,
    SendRToParties,
    SetInitialValues,
    SetSharedRFromParty,
    SetShares,
    Status,
)

app = Flask(__name__)
api = Api(app)

api.add_resource(Status, "/api/status/")
api.add_resource(SetInitialValues, "/api/initial-values/")
api.add_resource(SetShares, "/api/set-shares/")
api.add_resource(CalculateR, "/api/calculate-r/")
api.add_resource(SetSharedRFromParty, "/api/set-shared-r/")
api.add_resource(SendRToParties, "/api/send-r-to-parties/")
api.add_resource(CalculateMultiplicativeShare, "/api/calculate-multiplicative-share/")
api.add_resource(ResonstructSecret, "/api/reconstruct-secret/")
api.add_resource(Reset, "/api/reset/")
api.add_resource(FactoryReset, "/api/factory-reset/")


@app.route("/")
def home():
    return "<h1>Aukciszek API</h1>"


if __name__ == "__main__":
    app.run(port=args.port, debug=True)
