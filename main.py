import os
from google.cloud import secretmanager_v1
from google.cloud import storage
from google.cloud import pubsub_v1
from google.cloud import bigquery
import alpaca_trade_api as tradeapi
from flask import Flask
from flask import request
from zipfile import ZipFile
from TradeBot import TradeBot
from StockCorrelation import StockCorrelation
from os.path import basename
from datetime import date
import json
import base64


app = Flask(__name__)

PRJID="139391369285"

def init_vars():
    client = secretmanager_v1.SecretManagerServiceClient()

    name = f"projects/{PRJID}/secrets/APCA_API_KEY_ID/versions/latest"
    response = client.access_secret_version(request={'name': name})
    print(response)
    os.environ["APCA_API_KEY_ID"] = response.payload.data.decode('UTF-8')
    key = response.payload.data.decode('UTF-8')

    name = f"projects/{PRJID}/secrets/APCA_API_SECRET_KEY/versions/latest"
    response = client.access_secret_version(request={'name': name})
    print(response)
    os.environ["APCA_API_SECRET_ID"] = response.payload.data.decode('UTF-8')
    secret = response.payload.data.decode('UTF-8')
    return (key,secret)



@app.route('/dayend', methods=['POST'])
def daytrade():
    if request.method == 'POST':
        content = request.json
        print(content)
        ticker1 = content['ticker1']
        ticker2 = content['ticker2']
        lot1 = int(content['lot1'])
        lot2 = int(content['lot2'])
        print(ticker1,ticker2,lot1,lot2)
    (API_KEY,API_SECRET) = init_vars()
    lookback = 15
    symbols = (ticker1,ticker2)
    lots = (lot1,lot2)
    bot = TradeBot(symbols[0],symbols[1],lookback,API_KEY,API_SECRET)
    signals = bot.trading_signal()
    for i in range(2):
        print(symbols[i])
        if signals[i] == 1:
            bot.buy(symbols[i],lots[i])
        elif signals[i] == -1:
            bot.sell(symbols[i],lots[i])

    return ('', 204)

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # bucket_name = "your-bucket-name"
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    if blob.exists():
        try:
            ret = blob.download_to_filename(destination_file_name)
            print("download ",destination_file_name,ret)
            if ret is not None:
                print("Blob {} downloaded to {}.".format(source_blob_name, destination_file_name))
                return True
        except:
            return False
    return False


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # bucket_name = "your-bucket-name"
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
