# Imports the Google Cloud client library
import os
from google.cloud import vision

# 画像のラベルを検査する関数
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

# 画像の物体検出
def run_checkobject(file_uri) -> bool:
    # Instantiates a client
    client = vision.ImageAnnotatorClient()

    # The URI of the image file to annotate
    # file_uri = "https://saunarium-lava.com/img/pc/main-bg.png"
    # file_uri = "https://www.tanita-hw.co.jp/amenomichi/wp-content/uploads/2022/10/07.jpg"

    image = vision.Image()
    image.source.image_uri = file_uri

    # Performs object detection on the image file
    response = client.object_localization(image=image)
    objects = response.localized_object_annotations

    # Check if any of the detected objects is a person
    for object_ in objects:
        if object_.name.lower() == "person":
            return True

    return False


# webスクレイピングで画像取得する場合の実行関数
if __name__ == "__main__":
    # サービスアカウントキーのパスを設定
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/abeyuichi/スクレイピング/onsenscraiping-010c634e8f24.json"
    # 環境変数の設定を確認
    print("GOOGLE_APPLICATION_CREDENTIALS:", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    # run_quickstart()
    contains_person = run_checkobject()
    if contains_person:
        print("The image contains a person.")
    else:
        print("The image does not contain a person.")