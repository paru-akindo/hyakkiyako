import streamlit as st
import easyocr
import numpy as np
import cv2
from PIL import Image

# EasyOCR Readerの初期化
reader = easyocr.Reader(['en'], gpu=False)

# Streamlitアプリのタイトル
st.title("カメラからリアルタイムで数字を認識")

# カメラ入力
img_file_buffer = st.camera_input("カメラで撮影してください")

if img_file_buffer is not None:
    # 撮影された画像をPIL形式で読み込み
    image = Image.open(img_file_buffer)

    # PIL画像をNumPy配列に変換（EasyOCRがNumPy配列を必要とするため）
    image_np = np.array(image)

    # EasyOCRでテキスト認識を実行
    st.write("認識中...")
    results = reader.readtext(image_np)

    # 認識結果を表示
    st.write("認識結果:")
    for (bbox, text, prob) in results:
        st.write(f"テキスト: {text}, 信頼度: {prob:.2f}")

    # 認識結果を画像に描画
    for (bbox, text, prob) in results:
        # バウンディングボックスの座標を取得
        (top_left, top_right, bottom_right, bottom_left) = bbox
        top_left = tuple(map(int, top_left))
        bottom_right = tuple(map(int, bottom_right))

        # バウンディングボックスとテキストを描画
        cv2.rectangle(image_np, top_left, bottom_right, (0, 255, 0), 2)
        cv2.putText(image_np, text, (top_left[0], top_left[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # 描画結果を表示
    st.image(image_np, caption="認識結果付きの画像", use_column_width=True)
