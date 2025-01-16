import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image

# 定数
BOARD_SIZE = 5

def preprocess_image(image):
    """画像を前処理してOCR精度を向上"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # グレースケール変換
    _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)  # 二値化
    return binary

def extract_numbers(image):
    """画像から数字を抽出して配列に変換"""
    # OCRで文字認識
    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
    text = pytesseract.image_to_string(image, config=custom_config)
    
    # テキストを行ごとに分割し、配列に変換
    lines = text.strip().split("\n")
    board = []
    for line in lines:
        # 数字をスペースやカンマで分割してリストに変換
        numbers = [int(num) for num in line.split() if num.isdigit()]
        if numbers:
            board.append(numbers)
    
    # 配列のサイズを5×5に調整
    if len(board) == BOARD_SIZE and all(len(row) == BOARD_SIZE for row in board):
        return board
    else:
        return None

st.title("OCR Number Recognition for Merge Game")

# 画像アップロード
uploaded_file = st.file_uploader("Upload an image containing a 5x5 grid of numbers", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 画像の読み込み
    image = Image.open(uploaded_file)
    image_np = np.array(image)
    
    # 画像の前処理
    preprocessed_image = preprocess_image(image_np)
    
    # OCRで数字を抽出
    board = extract_numbers(preprocessed_image)
    
    # 結果の表示
    st.subheader("Uploaded Image")
    st.image(image, caption="Uploaded Image", use_column_width=True)
    
    if board:
        st.subheader("Recognized Board (5x5)")
        for row in board:
            st.write(" ".join(map(str, row)))
    else:
        st.error("Could not recognize a valid 5x5 board. Please try again with a clearer image.")
