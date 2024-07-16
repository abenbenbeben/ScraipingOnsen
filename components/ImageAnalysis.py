# Imports the Google Cloud client library
import os
from google.cloud import vision

def run_quickstart() -> vision.EntityAnnotation:


    # Instantiates a client
    client = vision.ImageAnnotatorClient()

    # The URI of the image file to annotate
    file_uri = "https://saunarium-lava.com/img/pc/main-bg.png"

    image = vision.Image()
    image.source.image_uri = file_uri

    # Performs label detection on the image file
    response = client.label_detection(image=image)
    labels = response.label_annotations

    print("Labels:")
    for label in labels:
        print(label.description)

    return labels


# webスクレイピングで画像取得する場合の実行関数
if __name__ == "__main__":
    # サービスアカウントキーのパスを設定
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abeyuichi/スクレイピング/onsenscraiping-010c634e8f24.json"
    # 環境変数の設定を確認
    print("GOOGLE_APPLICATION_CREDENTIALS:", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    run_quickstart()