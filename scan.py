import streamlit as st
import copy

# 定数
BOARD_SIZE = 5

# ユーティリティ：盤面を表示するための関数
def display_board(board):
    """盤面をデータフレーム形式で表示する（固定幅フォントが使われる）"""
    # 文字列で整形した盤面をテーブル表示
    board_str = [[f"{cell:2}" if cell is not None else " . " for cell in row] for row in board]
    st.table(board_str)

class MergeGameSimulator:
    def __init__(self, board):
        self.board = board  # 初期盤面を設定

    def find_clusters(self, board):
        """隣接する同じ数字のクラスターを探す"""
        visited = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        clusters = []
        
        def dfs(r, c, value):
            """深さ優先探索でクラスターを探す"""
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
        """クラスターを合成する。合成したセル数の総和を返す"""
        total_merged_numbers = 0
        for cluster in clusters:
            values = [board[r][c] for r, c in cluster]
            base_value = values[0]
            new_value = base_value + (len(cluster) - 2)
            total_merged_numbers += len(cluster)
            # 合成後の配置位置（ユーザー操作の場合は操作したセル、そうでなければ最下位かつ左を選ぶ）
            if user_action and user_action[0] == "add":
                if fall == 0:
                    target_r, target_c = user_action[1], user_action[2]
                else:
                    target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))
            else:
                target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))

            for r, c in cluster:
                board[r][c] = None

            if new_value < max_value:
                board[target_r][target_c] = new_value
        return total_merged_numbers

    def apply_gravity(self, board):
        """数字を下に落下させる"""
        for c in range(BOARD_SIZE):
            column = [board[r][c] for r in range(BOARD_SIZE) if board[r][c] is not None]
            for r in range(BOARD_SIZE - 1, -1, -1):
                board[r][c] = column.pop() if column else None

    def simulate(self, action, max_value=20, suppress_output=False):
        """1回のユーザー操作をシミュレートし、連鎖回数と合成セル数、最終盤面を返す"""
        board = copy.deepcopy(self.board)

        if not suppress_output:
            st.write("Initial board:")
            display_board(board)

        if action[0] == "add":
            r, c = action[1], action[2]
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
                display_board(board)

        return fall_count, total_merged_numbers, board

    def find_best_action(self, max_value=20):
        """最適なユーザー操作を探し、落下回数と合成セル数ごとに評価する"""
        max_fall_count = 0
        max_total_merged_numbers = 0
        best_action_by_fall = None
        best_action_by_merged = None
        best_action_by_fall_hr = None
        best_action_by_merged_hr = None
        fall_merge_n = 0
        merge_fall_n = 0

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if self.board[r][c] is not None:
                    # "add" 動作
                    fall_count, total_merged_numbers, _ = self.simulate(("add", r, c), max_value=max_value, suppress_output=True)
                    if fall_count >= max_fall_count:
                        max_fall_count = fall_count
                        best_r, best_c = r + 1, c + 1
                        best_action_by_fall = ("add", r, c)
                        best_action_by_fall_hr = ("add", "上から", best_r, "左から", best_c)
                        fall_merge_n = total_merged_numbers
                    if total_merged_numbers >= max_total_merged_numbers:
                        max_total_merged_numbers = total_merged_numbers
                        best_r, best_c = r + 1, c + 1
                        best_action_by_merged = ("add", r, c)
                        best_action_by_merged_hr = ("add", "上から", best_r, "左から", best_c)
                        merge_fall_n = fall_count

                    # "remove" 動作
                    fall_count, total_merged_numbers, _ = self.simulate(("remove", r, c), max_value=max_value, suppress_output=True)
                    if fall_count >= max_fall_count:
                        max_fall_count = fall_count
                        best_r, best_c = r + 1, c + 1
                        best_action_by_fall = ("remove", r, c)
                        best_action_by_fall_hr = ("remove", "上から", best_r, "左から", best_c)
                        fall_merge_n = total_merged_numbers
                    if total_merged_numbers >= max_total_merged_numbers:
                        max_total_merged_numbers = total_merged_numbers
                        best_r, best_c = r + 1, c + 1
                        best_action_by_merged = ("remove", r, c)
                        best_action_by_merged_hr = ("remove", "上から", best_r, "左から", best_c)
                        merge_fall_n = fall_count

        return (best_action_by_fall, max_fall_count, best_action_by_merged, max_total_merged_numbers,
                best_action_by_fall_hr, best_action_by_merged_hr, fall_merge_n, merge_fall_n)

# -------------------- Streamlit UI 部分 --------------------

st.title("Merge Game Simulator v2 (Improved UI)")

st.write("盤面を各セルごとに入力してください。")

# 盤面入力のグリッド
initial_board = []
for r in range(BOARD_SIZE):
    cols = st.columns(BOARD_SIZE)
    row_values = []
    for c in range(BOARD_SIZE):
        # 各セルの入力を数値入力で取得。ここでは例として初期値 8,8,6,5,6 を各行同じにしています。
        default_value = [8, 8, 6, 5, 6][c]
        value = cols[c].number_input(f"R{r+1} C{c+1}", min_value=0, max_value=100, value=default_value, key=f"{r}_{c}")
        row_values.append(value)
    initial_board.append(row_values)

max_value = st.number_input("最大合成数 (max_value):", min_value=1, value=20)

simulate_button = st.button("シミュレーション実行")

if simulate_button:
    # 入力された盤面を用いてシミュレーション開始
    simulator = MergeGameSimulator(initial_board)
    best_action_by_fall, max_fall_count, best_action_by_merged, max_total_merged_numbers, best_action_by_fall_hr, best_action_by_merged_hr, fall_merge_n, merge_fall_n = simulator.find_best_action(max_value=max_value)

    st.write(f"Best action by fall count: {best_action_by_fall_hr}, Max fall count: {max_fall_count}, Merged numbers: {fall_merge_n}")
    st.write(f"Best action by merged: {best_action_by_merged_hr}, Fall count: {merge_fall_n}, Max merged numbers: {max_total_merged_numbers}")

    if best_action_by_fall:
        st.write("\nシミュレーション (Best action by fall count):")
        simulator.simulate(best_action_by_fall, max_value=max_value, suppress_output=False)

    if best_action_by_merged:
        st.write("\nシミュレーション (Best action by merged numbers):")
        simulator.simulate(best_action_by_merged, max_value=max_value, suppress_output=False)
