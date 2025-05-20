import streamlit as st
import copy

# 盤面サイズ設定
BOARD_SIZE = 5
DEFAULT_MAX_VALUE = 20

# セッション状態の初期化
if "selected_cell" not in st.session_state:
    st.session_state.selected_cell = None
if "board_values" not in st.session_state:
    st.session_state.board_values = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
if "max_value" not in st.session_state:
    st.session_state.max_value = DEFAULT_MAX_VALUE

st.title("スマホ対応版 Merge Game Simulator")

# 最大合成値の設定
st.subheader("最大合成値を設定してください")
st.session_state.max_value = st.number_input(
    "最大合成値 (max_value)", min_value=1, value=st.session_state.max_value, key="max_value_input"
)

# 盤面のグリッド表示（5x5のレイアウト）
st.subheader("セルをタップすると編集できます")
for r in range(BOARD_SIZE):
    cols = st.columns(BOARD_SIZE)  # 各行にBOARD_SIZE個のカラムを作成
    for c in range(BOARD_SIZE):
        # ボタンのラベルはシンプルに (r,c): 値 と表示（例: (1,1): 0）
        if cols[c].button(f"({r+1},{c+1}): {st.session_state.board_values[r][c]}", key=f"btn_{r}_{c}"):
            st.session_state.selected_cell = (r, c)

# 編集用ダイアログ：タップしたセルのみスライダー表示
if st.session_state.selected_cell is not None:
    r, c = st.session_state.selected_cell
    st.subheader(f"({r+1},{c+1}) の値を変更")
    new_value = st.slider(
        "値を選択",
        min_value=0,
        max_value=st.session_state.max_value,
        value=st.session_state.board_values[r][c],
        key=f"slider_{r}_{c}"
    )
    # 確定・キャンセルボタンで他のセル編集に戻れる仕組み
    if st.button("確定"):
        st.session_state.board_values[r][c] = new_value
        st.session_state.selected_cell = None
    if st.button("キャンセル"):
        st.session_state.selected_cell = None

# 現在の盤面を表示
st.subheader("入力した盤面")
st.table(st.session_state.board_values)


######################################
# シミュレーションロジック
######################################
class MergeGameSimulator:
    def __init__(self, board, max_value):
        self.board = board  # 盤面 (2次元リスト)
        self.max_value = max_value  # 最大合成値

    def display_board(self, board):
        st.table(board)

    def find_clusters(self, board):
        # 隣接して同じ値のセルが3つ以上つながっているグループを検出
        visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        clusters = []

        def dfs(r, c, value):
            if r < 0 or r >= BOARD_SIZE or c < 0 or c >= BOARD_SIZE:
                return []
            if visited[r][c] or board[r][c] != value:
                return []
            visited[r][c] = True
            cluster = [(r, c)]
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                cluster.extend(dfs(r + dr, c + dc, value))
            return cluster

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if board[r][c] is not None and not visited[r][c]:
                    cluster = dfs(r, c, board[r][c])
                    if len(cluster) >= 3:
                        clusters.append(cluster)
        return clusters

    def merge_clusters(self, board, clusters):
        total_merged_numbers = 0
        for cluster in clusters:
            base_value = board[cluster[0][0]][cluster[0][1]]
            # 合成後の値 = 元の値 + (クラスタのサイズ - 2)
            new_value = base_value + (len(cluster) - 2)
            total_merged_numbers += len(cluster)
            # 最上段かつ最左のセルを合成先とする
            target_r, target_c = min(cluster, key=lambda x: (x[0], x[1]))
            for r, c in cluster:
                board[r][c] = None
            if new_value < self.max_value:
                board[target_r][target_c] = new_value
        return total_merged_numbers

    def apply_gravity(self, board):
        # 各列の上部に空セルを作るために重力処理を実施
        for c in range(BOARD_SIZE):
            column = [board[r][c] for r in range(BOARD_SIZE) if board[r][c] is not None]
            for r in range(BOARD_SIZE - 1, -1, -1):
                board[r][c] = column.pop() if column else None

    def simulate(self):
        board = copy.deepcopy(self.board)
        st.write("Initial Board:")
        self.display_board(board)
        fall_count = 0
        total_merged = 0
        self.apply_gravity(board)
        while True:
            clusters = self.find_clusters(board)
            if not clusters:
                break
            total_merged += self.merge_clusters(board, clusters)
            self.apply_gravity(board)
            fall_count += 1
            st.write(f"After fall {fall_count}:")
            self.display_board(board)
        return fall_count, total_merged, board


######################################
# シミュレーション実行
######################################
if st.button("Simulate"):
    board = copy.deepcopy(st.session_state.board_values)
    # 0は空セルとして扱うためNoneに変換
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == 0:
                board[r][c] = None
    st.write("### 入力盤面")
    st.table(board)
    simulator = MergeGameSimulator(board, st.session_state.max_value)
    fall_count, total_merged, final_board = simulator.simulate()
    st.write(f"**Fall count:** {fall_count}, **Merged count:** {total_merged}")
    st.write("### シミュレーション後の盤面")
    st.table(final_board)
