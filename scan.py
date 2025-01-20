import streamlit as st
import cv2
import numpy as np
import easyocr
from PIL import Image

# Streamlitアプリの設定
st.title("数字抽出アプリ")
st.write("画像をアップロードすると、赤枠内の数字を抽出して配列として表示します。")

# EasyOCRのインスタンスを作成
reader = easyocr.Reader(['en'], gpu=False)

# 画像アップロード
uploaded_file = st.file_uploader("画像をアップロードしてください", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 画像を読み込む
    image = Image.open(uploaded_file)
    image = np.array(image)

    # 画像を表示
    st.image(image, caption="アップロードされた画像", use_column_width=True)

    # 赤枠の位置とサイズを定義（固定座標）
    start_x, start_y = 100, 600  # 赤枠の左上の座標（手動で設定）
    cell_width, cell_height = 120, 120  # 各セルの幅と高さ
    grid_size = 5  # 5×5のグリッド

    # 数字を格納するリスト
    numbers = []

    # 赤枠の中の各セルを切り出してOCRで数字を読み取る
    for row in range(grid_size):
        row_numbers = []
        for col in range(grid_size):
            # 各セルの座標を計算
            cell_x = start_x + col * cell_width
            cell_y = start_y + row * cell_height
            cell = image[cell_y:cell_y + cell_height, cell_x:cell_x + cell_width]

            # OCRを適用して数字を抽出
            results = reader.readtext(cell, detail=0)  # detail=0でテキストのみ取得
            if results:
                # 最初の認識結果を数字として格納
                row_numbers.append(results[0])
            else:
                row_numbers.append(None)  # 認識できない場合はNoneを追加
        numbers.append(row_numbers)

    # 抽出した数字を表示
    st.write("抽出された数字:")
    st.write(numbers)
