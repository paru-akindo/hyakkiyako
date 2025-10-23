# app.py
import io
import cv2
import numpy as np
from PIL import Image
import pandas as pd
import streamlit as st
import easyocr

st.set_page_config(layout="wide")
st.title("自動グリッド OCR → CSV (アップロードのみで自動検出)")

# ----- 固定設定（必要ならここを 5,5 に変更） -----
ROWS = 5
COLS = 5
OCR_LANGS = ["ja", "en"]  # easyocr の言語リスト
# --------------------------------------------------

uploaded = st.file_uploader("画像をアップロード", type=["png", "jpg", "jpeg"])
debug = st.checkbox("デバッグ表示", value=False)

# easyocr reader
_reader = None
def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(OCR_LANGS, gpu=False)
    return _reader

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

def detect_quad_candidates(img, max_candidates=8):
    h,w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    edged = cv2.Canny(blur, 40, 150)
    cnts, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    quads = []
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02*peri, True)
        if len(approx) == 4:
            area = cv2.contourArea(approx)
            if area < 0.003 * w * h:
                continue
            quads.append((area, approx.reshape(4,2)))
    quads.sort(key=lambda x: x[0], reverse=True)
    results = []
    for a, q in quads[:max_candidates]:
        rect = order_points(q)
        warped = four_point_warp(img, rect)
        results.append((rect, warped))
    # フォールバック候補（画面下部のいくつかの切り出し）
    if len(results) < 3:
        for frac in [0.30, 0.40, 0.50]:
            y1 = int(h * frac)
            rect = np.array([[0,y1],[w-1,y1],[w-1,h-1],[0,h-1]], dtype="float32")
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

def ocr_cell_easyocr(cell, reader):
    if cell is None or cell.size == 0:
        return "", 0.0
    img_rgb = cv2.cvtColor(cell, cv2.COLOR_BGR2RGB)
    h,w = img_rgb.shape[:2]
    if max(h,w) < 60:
        img_rgb = cv2.resize(img_rgb, (0,0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LINEAR)
    try:
        # detail=1 を使って bbox と confidence を取得し信頼度評価に使う
        raw = reader.readtext(img_rgb, detail=1)
    except Exception:
        raw = []
    texts = []
    confs = []
    for box, text, conf in raw:
        texts.append(text)
        confs.append(conf)
    combined = " ".join(texts)
    digits = "".join(ch for ch in combined if ch.isdigit())
    avg_conf = float(np.mean(confs)) if confs else 0.0
    return digits, avg_conf

def score_candidate_by_grid(warped, r, c, reader):
    cells = split_cells(warped, r, c)
    total_digits = 0
    confs = []
    # 短時間OCR（信頼度と数字の有無でスコア化）
    for i in range(r):
        for j in range(c):
            cell = cells[i][j]
            val, conf = ocr_cell_easyocr(cell, reader)
            if val != "":
                total_digits += 1
            confs.append(conf)
    # 格子均一性スコア: 各セルサイズの分散は基本0なのでここでは warp 内で均等分割だから1.0 固定
    digit_ratio = total_digits / (r*c)
    avg_conf = float(np.mean(confs)) if confs else 0.0
    # 総合スコア：数字検出率と平均信頼度の重み和
    score = 0.7 * digit_ratio + 0.3 * (avg_conf / 100.0)
    return score, digit_ratio, avg_conf

def automatic_select_best_region(img, r, c):
    reader = get_reader()
    candidates = detect_quad_candidates(img, max_candidates=8)
    scored = []
    for rect, warped in candidates:
        score, ratio, avg_conf = score_candidate_by_grid(warped, r, c, reader)
        scored.append((score, ratio, avg_conf, rect, warped))
    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0] if scored else None
    return best, scored

def extract_table_from_warped(warped, r, c):
    reader = get_reader()
    cells = split_cells(warped, r, c)
    table = []
    conf_table = []
    for i in range(r):
        rowvals = []
        rowconfs = []
        for j in range(c):
            val, conf = ocr_cell_easyocr(cells[i][j], reader)
            rowvals.append(val)
            rowconfs.append(conf)
        table.append(rowvals)
        conf_table.append(rowconfs)
    return table, conf_table, cells

# Main flow
if uploaded:
    img = to_bgr(uploaded)
    st.subheader("アップロード画像")
    st.image(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), use_column_width=True)

    st.subheader("自動検出中...")
    best, all_scored = automatic_select_best_region(img, ROWS, COLS)
    if best is None:
        st.error("候補が見つかりませんでした。別の画像を試してください。")
    else:
        score, ratio, avg_conf, rect, warped = best
        st.write(f"選択された候補スコア {score:.3f} 数字検出率 {ratio:.2f} 平均信頼度 {avg_conf:.1f}")
        st.image(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB), caption="自動選択された抽出領域", use_column_width=True)

        table, conf_table, cells = extract_table_from_warped(warped, ROWS, COLS)
        df = pd.DataFrame(table)
        st.subheader("抽出結果プレビュー")
        st.dataframe(df)

        st.download_button("CSV をダウンロード", data=pd.DataFrame(table).to_csv(index=False, header=False).encode("utf-8"), file_name="grid_autodetect.csv", mime="text/csv")

        if debug:
            st.subheader("候補一覧とスコア")
            for idx, (s, rratio, aconf, rect, warped_cand) in enumerate(all_scored):
                st.write(f"候補 {idx+1} スコア {s:.3f} 検出率 {rratio:.2f} 平均conf {aconf:.1f}")
                st.image(cv2.cvtColor(warped_cand, cv2.COLOR_BGR2RGB), width=240)
            st.subheader("セル単位プレビュー")
            for i in range(ROWS):
                cols_ui = st.columns(ROWS)
                for j in range(COLS):
                    with cols_ui[j]:
                        img_small = cv2.cvtColor(cells[i][j], cv2.COLOR_BGR2RGB)
                        st.image(img_small, width=80, caption=f"R{i+1}C{j+1} → {table[i][j]} conf {conf_table[i][j]:.1f}")
