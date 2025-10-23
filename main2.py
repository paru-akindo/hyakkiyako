# app.py
import io
import cv2
import numpy as np
from PIL import Image
import pytesseract
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")
st.title("可変グリッド OCR → CSV")

# --- UI: upload / params
uploaded = st.file_uploader("画像をアップロード", type=["png","jpg","jpeg"])
rows = st.number_input("グリッド行数", value=6, min_value=1, max_value=20, step=1)
cols = st.number_input("グリッド列数", value=6, min_value=1, max_value=20, step=1)
ocr_lang = st.text_input("Tesseract 言語コード", value="jpn", help="必要なら eng 等を追加")
show_cells = st.checkbox("セルプレビューを表示", value=True)
debug = st.checkbox("デバッグ表示（候補の輪郭など）", value=False)

# --- helpers
def to_bgr(file) -> np.ndarray:
    img = Image.open(file).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

def auto_candidates(img, max_candidates=6):
    h,w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edged = cv2.Canny(blur, 50, 150)
    cnts, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    quads = []
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02*peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area < 0.01*w*h: 
                continue
            quads.append((area, approx))
    quads.sort(key=lambda x: x[0], reverse=True)
    results = []
    for a, q in quads[:max_candidates]:
        rect = order_points(q.reshape(4,2))
        warped = four_point_warp(img, rect)
        results.append((rect, warped))
    # fallback: lower portion crops (3 candidates)
    if not results:
        for y_frac in [0.35, 0.45, 0.55]:
            y1 = int(h*y_frac)
            results.append((np.array([[0,y1],[w-1,y1],[w-1,h-1],[0,h-1]], dtype="float32"), img[y1:h,0:w]))
    return results

def order_points(pts):
    pts = np.array(pts, dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect = np.zeros((4,2), dtype="float32")
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def four_point_warp(img, rect):
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br-bl)
    widthB = np.linalg.norm(tr-tl)
    maxW = max(int(widthA), int(widthB))
    heightA = np.linalg.norm(tr-br)
    heightB = np.linalg.norm(tl-bl)
    maxH = max(int(heightA), int(heightB))
    dst = np.array([[0,0],[maxW-1,0],[maxW-1,maxH-1],[0,maxH-1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (maxW, maxH))
    return warped

def split_cells(warped, r, c):
    h,w = warped.shape[:2]
    ch = h // r
    cw = w // c
    cells = []
    for i in range(r):
        row = []
        for j in range(c):
            y1 = i*ch; x1 = j*cw
            y2 = y1 + ch; x2 = x1 + cw
            row.append(warped[y1:y2, x1:x2])
        cells.append(row)
    return cells

def ocr_digits_from_cell(cell, lang):
    gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
    # enhance
    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    config = "--psm 6 -c tessedit_char_whitelist=0123456789"
    try:
        txt = pytesseract.image_to_string(th, lang=lang, config=config)
    except Exception:
        txt = pytesseract.image_to_string(th, config=config)
    digits = "".join([ch for ch in txt if ch.isdigit()])
    return digits if digits != "" else ""

# --- main flow
if uploaded:
    img = to_bgr(uploaded)
    st.subheader("アップロード画像")
    st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_column_width=True)

    st.subheader("自動候補領域（候補を選択 → 微調整）")
    candidates = auto_candidates(img, max_candidates=6)
    cols_ui = st.columns(len(candidates))
    chosen_idx = None
    for idx, (rect, warped) in enumerate(candidates):
        with cols_ui[idx]:
            st.image(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB), caption=f"候補 {idx+1}", use_column_width=True)
            if st.button(f"この候補を選択 ({idx+1})", key=f"sel_{idx}"):
                chosen_idx = idx

    if chosen_idx is None:
        chosen_idx = 0

    rect, warped = candidates[chosen_idx]
    h,w = img.shape[:2]
    # provide sliders for fine-tune in original-image coordinates (normalized)
    st.subheader("領域微調整（スライダーで調整）")
    left = st.slider("左オフセット (%)", 0.0, 100.0, 0.0, step=0.5)
    right = st.slider("右オフセット (%)", 0.0, 100.0, 0.0, step=0.5)
    top = st.slider("上オフセット (%)", 0.0, 100.0, 0.0, step=0.5)
    bottom = st.slider("下オフセット (%)", 0.0, 100.0, 0.0, step=0.5)

    # apply adjustments to warped image crop by expanding/contracting margins
    wh_h, wh_w = warped.shape[:2]
    lx = int(wh_w * (left/100.0))
    rx = int(wh_w * (1 - right/100.0))
    ty = int(wh_h * (top/100.0))
    by = int(wh_h * (1 - bottom/100.0))
    lx = max(0, lx); rx = max(lx+1, rx)
    ty = max(0, ty); by = max(ty+1, by)
    cropped = warped[ty:by, lx:rx]

    st.image(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB), caption="最終抽出領域プレビュー", use_column_width=True)

    if st.button("OCR 実行して CSV 出力"):
        cells = split_cells(cropped, int(rows), int(cols))
        table = []
        for r in range(int(rows)):
            rowvals = []
            for c_ in range(int(cols)):
                val = ocr_digits_from_cell(cells[r][c_], ocr_lang)
                rowvals.append(val)
            table.append(rowvals)
        df = pd.DataFrame(table)
        st.subheader("抽出結果プレビュー")
        st.dataframe(df)

        if show_cells:
            st.subheader("セル単位プレビュー")
            cols_preview = st.columns(int(cols))
            for i in range(int(rows)):
                for j in range(int(cols)):
                    with cols_preview[j]:
                        st.image(cv2.cvtColor(cells[i][j], cv2.COLOR_BGR2RGB), width=80, caption=f"R{i+1}C{j+1} → {table[i][j]}")

        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False, header=False)
        st.download_button("CSV をダウンロード", data=csv_buf.getvalue().encode("utf-8"), file_name="grid.csv", mime="text/csv")

    if debug:
        st.subheader("デバッグ情報")
        st.write(f"元画像サイズ: {w} x {h}")
        st.write(f"ワーピング後サイズ: {warped.shape[1]} x {warped.shape[0]}")
