import streamlit as st
import easyocr
import numpy as np
import cv2
from PIL import Image

# Streamlitアプリのタイトル
st.title("OCRで画像から数字を取得")

# EasyOCRのリーダーを初期化
reader = easyocr.Reader(['en'], gpu=False)  # GPUが不要な場合はgpu=False

# ファイルアップロード
uploaded_file = st.file_uploader("画像をアップロードしてください", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # アップロードされた画像を表示
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_column_width=True)

    # 画像をNumPy配列に変換
    image_np = np.array(image)

    # OpenCVで画像をグレースケールに変換
    gray_image = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)

    # OCRを実行して結果を取得
    st.write("OCR処理中...")
    results = reader.readtext(gray_image)

    # 結果をフィルタリングして数字のみ抽出
    detected_numbers = []
    for (bbox, text, prob) in results:
        if text.isdigit():  # 数字のみを抽出
            detected_numbers.append(text)

    # 結果を表示
    if detected_numbers:
        st.write("検出された数字:", detected_numbers)
    else:
        st.write("数字が検出されませんでした。")
