import streamlit as st
import copy

# 定数設定
BOARD_SIZE = 5
DEFAULT_MAX_VALUE = 20

# セッション状態の初期化（グリッド入力用）
if "grid_board_values" not in st.session_state:
    st.session_state.grid_board_values = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
# セッション状態の初期化（CSV入力用）
if "csv_board_values" not in st.session_state:
    default_csv = "4,5,6,5,6\n5,4,4,3,5\n4,5,3,4,5\n6,2,2,4,3\n2,6,4,3,5"
    st.session_state.csv_board_values = default_csv
# セッション状態の初期化（セル選択用）
if "selected_cell" not in st.session_state:
    st.session_state.selected_cell = None
# 最大合成値のセッション状態
if "max_value" not in st.session_state:
    st.session_state.max_value = DEFAULT_MAX_VALUE

# タイトル表示
st.title("スマホ対応版 Merge Game Simulator")

# 盤面入力方法の選択
input_method = st.radio("盤面の入力方法を選んでください", ("グリッド入力", "カンマ区切りテキスト入力"))

# 最大合成値の設定
st.subheader("最大合成値を設定してください")
st.session_state.max_value = st.number_input(
    "最大合成値 (max_value)", min_value=1, value=st.session_state.max_value, key="max_value_input"
)

# 入力方法に応じた盤面取得
board = None

if input_method == "グリッド入力":
    st.subheader("セルをタップすると編集できます")
    # 5×5のグリッドレイアウトでボタンを配置
    for r in range(BOARD_SIZE):
        cols = st.columns(BOARD_SIZE)
        for c in range(BOARD_SIZE):
            # シンプルなラベル "(r,c): 値" で表示（例: (1,1): 0）
            if cols[c].button(f"({r+1},{c+1}): {st.session_state.grid_board_values[r][c]}", key=f"grid_btn_{r}_{c}"):
                st.session_state.selected_cell = (r, c)
    # セルが選ばれている場合のみ、スライダー表示
    if st.session_state.selected_cell is not None:
        r, c = st.session_state.selected_cell
        st.subheader(f"({r+1},{c+1}) の値を変更")
        new_value = st.slider(
            "値を選択",
            min_value=0,
            max_value=st.session_state.max_value,
            value=st.session_state.grid_board_values[r][c],
            key=f"grid_slider_{r}_{c}"
        )
        if st.button("確定", key=f"grid_confirm_{r}_{c}"):
            st.session_state.grid_board_values[r][c] = new_value
            st.session_state.selected_cell = None
        if st.button("キャンセル", key=f"grid_cancel_{r}_{c}"):
            st.session_state.selected_cell = None
    # グリッド入力の盤面を使用
    board = st.session_state.grid_board_values

else:
    st.subheader("カンマ区切りの5行を入力してください（例）")
    csv_input = st.text_area("カンマ区切りの5行の盤面", value=st.session_state.csv_board_values, height=150)
    st.session_state.csv_board_values = csv_input
    # CSV形式のテキストを解析して盤面リストへ変換
    try:
        lines = csv_input.strip().splitlines()
        parsed_board = []
        for line in lines:
            values = line.strip().split(",")
            if len(values) != BOARD_SIZE:
                st.error("各行に5つの値を入力してください。")
                parsed_board = None
                break
            row = []
            for v in values:
                row.append(int(v.strip()))
            parsed_board.append(row)
        if parsed_board is not None and len(parsed_board) != BOARD_SIZE:
            st.error("5行入力してください。")
            parsed_board = None
    except Exception as e:
        st.error(f"入力の解析エラー: {e}")
        parsed_board = None
    board = parsed_board

# 入力した盤面の表示
if board is not None:
    st.subheader("入力した盤面")
    st.table(board)


########################################
# シミュレーションロジック
########################################
def run_simulation(board, max_value):
    # シミュレーション前の盤面の準備
    sim_board = copy.deepcopy(board)
    # 入力値「0」は空セルとして扱う
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if sim_board[r][c] == 0:
                sim_board[r][c] = None

    class MergeGameSimulator:
        def __init__(self, board, max_value):
            self.board = board
            self.max_value = max_value

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

        def merge_clusters(self, board, clusters):
            total_merged_numbers = 0
            for cluster in clusters:
                base_value = board[cluster[0][0]][cluster[0][1]]
                new_value = base_value + (len(cluster) - 2)
                total_merged_numbers += len(cluster)
                # 合成先は行番号の最小、かつ列番号の最小のセル
                target_r, target_c = min(cluster, key=lambda x: (x[0], x[1]))
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
            local_board = copy.deepcopy(self.board)
            st.write("Initial Board:")
            self.display_board(local_board)
            fall_count = 0
            total_merged = 0
            self.apply_gravity(local_board)
            while True:
                clusters = self.find_clusters(local_board)
                if not clusters:
                    break
                total_merged += self.merge_clusters(local_board, clusters)
                self.apply_gravity(local_board)
                fall_count += 1
                st.write(f"After fall {fall_count}:")
                self.display_board(local_board)
            return fall_count, total_merged, local_board

    simulator = MergeGameSimulator(sim_board, max_value)
    return simulator.simulate()


########################################
# シミュレーション実行
########################################
if st.button("Simulate"):
    if board is None:
        st.error("盤面が正しく入力されていません。")
    else:
        fall_count, total_merged, final_board = run_simulation(board, st.session_state.max_value)
        st.write(f"**Fall count:** {fall_count}, **Merged count:** {total_merged}")
        st.write("### シミュレーション後の盤面")
        st.table(final_board)
