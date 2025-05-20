import streamlit as st
import copy

# 定数
BOARD_SIZE = 5
DEFAULT_MAX_VALUE = 20

# ----------------------------
# MergeGameSimulator クラス
# ----------------------------
class MergeGameSimulator:
    def __init__(self, board):
        self.board = board  # 初期盤面

    def display_board(self, board):
        """盤面をテキスト形式で表示"""
        for row in board:
            st.write(" ".join(f"{cell:2}" if cell is not None else " . " for cell in row))
        st.write("---")

    def find_clusters(self, board):
        """隣接する同じ数字のクラスターを探す"""
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

    def merge_clusters(self, board, clusters, fall, user_action=None, max_value=20):
        """検出したクラスターを合成する"""
        total_merged_numbers = 0
        for cluster in clusters:
            values = [board[r][c] for r, c in cluster]
            base_value = values[0]
            new_value = base_value + (len(cluster) - 2)
            total_merged_numbers += len(cluster)
            
            # 合成先のセルの決定
            if user_action and user_action[0] == "add":
                if fall == 0:
                    # ユーザー操作として加算対象のセルに反映（初回の場合）
                    target_r, target_c = user_action[1], user_action[2]
                else:
                    target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))
            else:
                # remove 操作のときまたは user_action がない場合は、行番号が大きい（下）もの、同じなら左寄せ
                target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))
            
            # クラスター内のセルを削除
            for r, c in cluster:
                board[r][c] = None
            # 新しい値を配置（max_value未満なら）
            if new_value < max_value:
                board[target_r][target_c] = new_value

        return total_merged_numbers

    def apply_gravity(self, board):
        """各列ごとに数字を下に落下させる"""
        for c in range(BOARD_SIZE):
            column = [board[r][c] for r in range(BOARD_SIZE) if board[r][c] is not None]
            for r in range(BOARD_SIZE - 1, -1, -1):
                board[r][c] = column.pop() if column else None

    def simulate(self, action, max_value=20, suppress_output=False):
        """
        指定した user_action（("add", r, c) または ("remove", r, c)）を盤面に適用し、
        連鎖処理（合成＋落下）をシミュレートする。
        """
        board = copy.deepcopy(self.board)
        if not suppress_output:
            st.write("Initial board:")
            self.display_board(board)

        # ユーザー操作の適用
        if action[0] == "add":
            r, c = action[1], action[2]
            # もしセルが None なら適用不可、通常は数字が入っている前提
            if board[r][c] is not None:
                board[r][c] += 1
        elif action[0] == "remove":
            r, c = action[1], action[2]
            board[r][c] = None

        fall_count = 0
        total_merged_numbers = 0
        self.apply_gravity(board)

        while True:
            clusters = self.find_clusters(board)
            if not clusters:
                break
            total_merged_numbers += self.merge_clusters(board, clusters, fall_count, user_action=action, max_value=max_value)
            self.apply_gravity(board)
            fall_count += 1
            if not suppress_output:
                st.write(f"After fall {fall_count}:")
                self.display_board(board)

        return fall_count, total_merged_numbers, board

    def find_best_action(self, max_value=20):
        """
        盤面全体に対して、「add」と「remove」の各操作を試行し、
        連鎖（落下回数）と合成されたセルの個数から最適な操作を見つける。
        """
        max_fall_count = 0
        max_total_merged_numbers = 0

        best_action_by_fall = None
        best_action_by_merged = None
        fall_merge_n = 0
        merge_fall_n = 0

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r][c] is not None:
                    # "add" 動作を試行
                    fall_count, total_merged_numbers, _ = self.simulate(("add", r, c), max_value=max_value, suppress_output=True)
                    if fall_count >= max_fall_count:
                        max_fall_count = fall_count
                        best_action_by_fall = ("add", r, c)
                        fall_merge_n = total_merged_numbers

                    if total_merged_numbers >= max_total_merged_numbers:
                        max_total_merged_numbers = total_merged_numbers
                        best_action_by_merged = ("add", r, c)
                        merge_fall_n = fall_count

                    # "remove" 動作を試行
                    fall_count, total_merged_numbers, _ = self.simulate(("remove", r, c), max_value=max_value, suppress_output=True)
                    if fall_count >= max_fall_count:
                        max_fall_count = fall_count
                        best_action_by_fall = ("remove", r, c)
                        fall_merge_n = total_merged_numbers

                    if total_merged_numbers >= max_total_merged_numbers:
                        max_total_merged_numbers = total_merged_numbers
                        best_action_by_merged = ("remove", r, c)
                        merge_fall_n = fall_count

        return best_action_by_fall, max_fall_count, best_action_by_merged, max_total_merged_numbers, fall_merge_n, merge_fall_n

# ----------------------------
# Streamlit アプリ本体
# ----------------------------
st.title("Merge Game Simulator v2")

# 盤面の入力方法選択
input_method = st.radio("盤面の入力方法を選んでください", ("グリッド入力", "カンマ区切りテキスト入力"))

# セッション状態の初期化（グリッド入力用）
if "grid_board_values" not in st.session_state:
    st.session_state.grid_board_values = [[8] * BOARD_SIZE for _ in range(BOARD_SIZE)]
# セッション状態の初期化（CSV入力用）
if "csv_board_values" not in st.session_state:
    default_csv = "8,8,6,5,6\n8,8,6,5,6\n8,8,6,5,6\n8,8,6,5,6\n8,8,6,5,6"
    st.session_state.csv_board_values = default_csv
# セッション状態の初期化（セル選択用、グリッド入力時）
if "selected_cell" not in st.session_state:
    st.session_state.selected_cell = None
# 最大合成値
if "max_value" not in st.session_state:
    st.session_state.max_value = DEFAULT_MAX_VALUE

# 最大合成値の設定
st.subheader("最大合成値の設定")
st.session_state.max_value = st.number_input("最大合成値 (max_value)", min_value=1, value=st.session_state.max_value, key="max_value_input")

# 入力盤面の選択
board = None
if input_method == "グリッド入力":
    st.subheader("グリッド入力（セルをタップして編集）")
    # 5×5のグリッドでボタンを配置
    for r in range(BOARD_SIZE):
        cols = st.columns(BOARD_SIZE)
        for c in range(BOARD_SIZE):
            # ボタンのラベルはシンプルに (r,c): 値 と表示（例: (1,1): 8）
            if cols[c].button(f"({r+1},{c+1}): {st.session_state.grid_board_values[r][c]}", key=f"grid_btn_{r}_{c}"):
                st.session_state.selected_cell = (r, c)
    # セルがタップされた場合、スライダーで編集
    if st.session_state.selected_cell is not None:
        r, c = st.session_state.selected_cell
        st.subheader(f"({r+1},{c+1}) の値を変更")
        new_value = st.slider("新しい値を選択", min_value=0, max_value=st.session_state.max_value, value=st.session_state.grid_board_values[r][c], key=f"grid_slider_{r}_{c}")
        if st.button("確定", key=f"grid_confirm_{r}_{c}"):
            st.session_state.grid_board_values[r][c] = new_value
            st.session_state.selected_cell = None
        if st.button("キャンセル", key=f"grid_cancel_{r}_{c}"):
            st.session_state.selected_cell = None
    board = st.session_state.grid_board_values

else:
    st.subheader("カンマ区切りテキスト入力")
    csv_input = st.text_area("5行のカンマ区切りで盤面を入力してください", value=st.session_state.csv_board_values, height=150)
    st.session_state.csv_board_values = csv_input
    try:
        lines = csv_input.strip().splitlines()
        parsed_board = []
        for line in lines:
            values = line.strip().split(",")
            if len(values) != BOARD_SIZE:
                st.error("各行に5つの数値を入力してください。")
                parsed_board = None
                break
            row = [int(v.strip()) for v in values]
            parsed_board.append(row)
        if parsed_board is not None and len(parsed_board) != BOARD_SIZE:
            st.error("5行入力してください。")
            parsed_board = None
    except Exception as e:
        st.error(f"入力内容の解析エラー: {e}")
        parsed_board = None
    board = parsed_board

# 入力盤面の表示
if board is not None:
    st.subheader("入力された盤面")
    st.table(board)

# ----------------------------
# シミュレーション実行
# ----------------------------
simulate_button = st.button("Simulate (最適アクション評価＆連鎖シミュレーション)")

if simulate_button:
    if board is None:
        st.error("盤面が正しく入力されていません。")
    else:
        try:
            simulator = MergeGameSimulator(board)
            max_value = st.session_state.max_value

            # 最適なアクションを評価
            best_action_by_fall, max_fall_count, best_action_by_merged, max_total_merged_numbers, fall_merge_n, merge_fall_n = simulator.find_best_action(max_value=max_value)
            if best_action_by_fall:
                r, c = best_action_by_fall[1], best_action_by_fall[2]
                st.write(f"【落下回数最大の操作】: {best_action_by_fall[0]} ({r+1},{c+1}) → Fall count: {max_fall_count}, Merged count: {fall_merge_n}")
            if best_action_by_merged:
                r, c = best_action_by_merged[1], best_action_by_merged[2]
                st.write(f"【合成セル数最大の操作】: {best_action_by_merged[0]} ({r+1},{c+1}) → Fall count: {merge_fall_n}, Merged count: {max_total_merged_numbers}")

            # シミュレーション結果の表示
            if best_action_by_fall:
                st.write("-----")
                st.write("【シミュレーション結果：落下回数最大の操作】")
                simulator.simulate(best_action_by_fall, max_value=max_value, suppress_output=False)
            if best_action_by_merged:
                st.write("-----")
                st.write("【シミュレーション結果：合成セル数最大の操作】")
                simulator.simulate(best_action_by_merged, max_value=max_value, suppress_output=False)
        except Exception as e:
            st.error(f"シミュレーション実行時のエラー: {e}")
