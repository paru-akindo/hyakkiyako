import streamlit as st
import copy

# **盤面サイズ**
BOARD_SIZE = 5

# **最大合成値のデフォルト設定**
DEFAULT_MAX_VALUE = 20

# **状態管理**
if "selected_cell" not in st.session_state:
    st.session_state.selected_cell = None
if "board_values" not in st.session_state:
    st.session_state.board_values = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
if "max_value" not in st.session_state:
    st.session_state.max_value = DEFAULT_MAX_VALUE

st.title("スマホ対応版 Merge Game Simulator")

# **最大合成値の設定**
st.subheader("最大合成値を設定してください")
st.session_state.max_value = st.number_input(
    "最大合成値 (max_value)", min_value=1, value=st.session_state.max_value, key="max_value_input"
)

# **盤面をリスト形式で表示**
st.subheader("セルをタップすると編集できます")
for r in range(BOARD_SIZE):
    for c in range(BOARD_SIZE):
        if st.button(f"セル ({r+1}, {c+1}): {st.session_state.board_values[r][c]}", key=f"btn_{r}_{c}"):
            st.session_state.selected_cell = (r, c)

# **セル編集ダイアログ**
if st.session_state.selected_cell is not None:
    r, c = st.session_state.selected_cell
    st.subheader(f"セル ({r+1}, {c+1}) の値を変更")
    new_value = st.slider("値を選択", min_value=0, max_value=st.session_state.max_value, value=st.session_state.board_values[r][c], key=f"slider_{r}_{c}")
    if st.button("確定"):
        st.session_state.board_values[r][c] = new_value
        st.session_state.selected_cell = None
    if st.button("キャンセル"):
        st.session_state.selected_cell = None

# **入力後の盤面を表示**
st.subheader("入力した盤面")
st.table(st.session_state.board_values)


######################################
# シミュレーションロジック
######################################
class MergeGameSimulator:
    def __init__(self, board, max_value):
        self.board = board  # 盤面情報（2次元リスト）
        self.max_value = max_value  # 最大合成値

    def display_board(self, board):
        st.table(board)

    def find_clusters(self, board):
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

    def merge_clusters(self, board, clusters, fall):
        total_merged_numbers = 0
        for cluster in clusters:
            values = [board[r][c] for r, c in cluster]
            base_value = values[0]
            new_value = base_value + (len(cluster) - 2)
            total_merged_numbers += len(cluster)
            target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))
            for r, c in cluster:
                board[r][c] = None
            if new_value < self.max_value:
                board[target_r][target_c] = new_value
        return total_merged_numbers

    def apply_gravity(self, board):
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
        self
