# app.py
import io
import cv2
import numpy as np
from PIL import Image
import pandas as pd
import streamlit as st
import easyocr

st.set_page_config(layout="wide")
st.title("可変グリッド OCR → CSV (Streamlit Cloud 対応)")

# UI: upload / params
uploaded = st.file_uploader("画像をアップロード", type=["png", "jpg", "jpeg"])
rows = st.number_input("グリッド行数", value=6, min_value=1, max_value=20, step=1)
cols = st.number_input("グリッド列数", value=6, min_value=1, max_value=20, step=1)
langs = st.text_input("OCR 言語コード（カンマ区切り）", value="ja,en")
show_cells = st.checkbox("セルプレビューを表示", value=True)
debug = st.checkbox("デバッグ表示（候補の輪郭など）", value=False)

# Initialize EasyOCR reader (CPU)
_reader = None
def get_reader(lang_list):
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(lang_list, gpu=False)
    return _reader

# Helpers
def to_bgr(file) -> np.ndarray:
    img = Image.open(file).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

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
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxW = max(int(widthA), int(widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxH = max(int(heightA), int(heightB))
    dst = np.array([[0,0],[maxW-1,0],[maxW-1,maxH-1],[0,maxH-1]], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, (maxW, maxH))
    return warped

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
            if area < 0.005 * w * h:
                continue
            quads.append((area, approx.reshape(4,2)))
    quads.sort(key=lambda x: x[0], reverse=True)
    results = []
    for a, q in quads[:max_candidates]:
        rect = order_points(q)
        warped = four_point_warp(img, rect)
        results.append((rect, warped))
    if not results:
        for y_frac in [0.35, 0.45, 0.55]:
            y1 = int(h * y_frac)
            rect = np.array([[0, y1], [w-1, y1], [w-1, h-1], [0, h-1]], dtype="float32")
            warped = img[y1:h, 0:w]
            results.append((rect, warped))
    return results

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
            cell = warped[y1:y2, x1:x2]
            row.append(cell)
        cells.append(row)
    return cells

def ocr_digits_easyocr(cell, reader):
    if cell is None or cell.size == 0:
        return ""
    img_rgb = cv2.cvtColor(cell, cv2.COLOR_BGR2RGB)
    h, w = img_rgb.shape[:2]
    if max(h,w) < 60:
        img_rgb = cv2.resize(img_rgb, (0,0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)
    try:
        results = reader.readtext(img_rgb, detail=0)
    except Exception:
        results = []
    combined = " ".join(results)
    digits = "".join(ch for ch in combined if ch.isdigit())
    return digits

# Main
if uploaded:
    img = to_bgr(uploaded)
    st.subheader("アップロード画像")
    st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_column_width=True)

    st.subheader("自動候補領域（候補を選択）")
    candidates = auto_candidates(img, max_candidates=6)
    cols_ui = st.columns(len(candidates))
    chosen_idx = st.session_state.get("chosen_idx", None)
    for idx, (rect, warped) in enumerate(candidates):
        with cols_ui[idx]:
            st.image(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB), caption=f"候補 {idx+1}", use_column_width=True)
            if st.button(f"選択 {idx+1}", key=f"sel_{idx}"):
                chosen_idx = idx
                st.session_state["chosen_idx"] = idx

    if chosen_idx is None:
        chosen_idx = 0
    rect, warped = candidates[chosen_idx]

    st.subheader("領域微調整（%オフセット）")
    left = st.slider("左オフセット (%)", 0.0, 40.0, 0.0, step=0.5)
    right = st.slider("右オフセット (%)", 0.0, 40.0, 0.0, step=0.5)
    top = st.slider("上オフセット (%)", 0.0, 40.0, 0.0, step=0.5)
    bottom = st.slider("下オフセット (%)", 0.0, 40.0, 0.0, step=0.5)

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
        lang_list = [l.strip() for l in langs.split(",") if l.strip()]
        reader = get_reader(lang_list)
        cells = split_cells(cropped, int(rows), int(cols))
        table = []
        for r in range(int(rows)):
            rowvals = []
            for c_ in range(int(cols)):
                val = ocr_digits_easyocr(cells[r][c_], reader)
                rowvals.append(val)
            table.append(rowvals)
        df = pd.DataFrame(table)
        st.subheader("抽出結果プレビュー")
        st.dataframe(df)

        if show_cells:
            st.subheader("セル単位プレビュー")
            for i in range(int(rows)):
                cols_preview = st.columns(int(cols))
                for j in range(int(cols)):
                    with cols_preview[j]:
                        img_small = cv2.cvtColor(cells[i][j], cv2.COLOR_BGR2RGB)
                        st.image(img_small, width=80, caption=f"R{i+1}C{j+1} → {table[i][j]}")

        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False, header=False)
        st.download_button("CSV をダウンロード", data=csv_buf.getvalue().encode("utf-8"), file_name="grid.csv", mime="text/csv")

    if debug:
        st.subheader("デバッグ情報")
        h, w = img.shape[:2]
        st.write(f"元画像サイズ: {w} x {h}")
        st.write(f"ワーピング後サイズ: {warped.shape[1]} x {warped.shape[0]}")
