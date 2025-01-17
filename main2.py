import streamlit as st
import copy

# 定数
BOARD_SIZE = 5

class MergeGameSimulator:
    def __init__(self, board):
        self.board = board  # 初期盤面を設定

    def display_board(self, board):
        """盤面をHTMLで5×5形式で表示"""
        for row in board:
            st.write(" ".join(f"{cell:2}" if cell else " . " for cell in row))
        st.write("---")

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
        """クラスターを合成する"""
        total_merged_numbers = 0
        for cluster in clusters:
            values = [board[r][c] for r, c in cluster]
            base_value = values[0]
            new_value = base_value + (len(cluster) - 2)
            total_merged_numbers += len(cluster)

            # 合成後の位置を決定
            if user_action and user_action[0] == "add":
                if fall == 0:
                    # ユーザー操作で加算された位置に配置
                    target_r, target_c = user_action[1], user_action[2]
                else:
                    target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))
            else:
                # 一番下の行、同じ高さなら一番左
                target_r, target_c = min(cluster, key=lambda x: (-x[0], x[1]))

            # クラスターを消去
            for r, c in cluster:
                board[r][c] = None

            # 新しい値を配置
            if new_value < max_value:
                board[target_r][target_c] = new_value

        return total_merged_numbers

    def apply_gravity(self, board):
        """数字を下に落下させる"""
        for c in range(BOARD_SIZE):
            column = [board[r][c] for r in range(BOARD_SIZE) if board[r][c] is not None]
            # 下から詰めるように修正
            for r in range(BOARD_SIZE - 1, -1, -1):
                board[r][c] = column.pop() if column else None

    def simulate(self, action, max_value=20, suppress_output=False):
        """1回のユーザー操作をシミュレート"""
        board = copy.deepcopy(self.board)

        if not suppress_output:
            st.write("Initial board:")
            self.display_board(board)

        # ユーザーの動作を適用
        if action[0] == "add":
            r, c = action[1], action[2]
            board[r][c] += 1
        elif action[0] == "remove":
            r, c = action[1], action[2]
            board[r][c] = None

        # 合成と落下処理を繰り返す
        fall_count = 0
        total_merged_numbers = 0

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
    """最適なユーザー操作を探す (左下から右上に向かう順序)"""
    max_fall_count = 0
    max_total_merged_numbers = 0

    best_action_by_fall = None
    best_action_by_merged = None

    # 左下から右上に向かう順序でセルを取得
    for r in range(BOARD_SIZE - 1, -1, -1):  # 行: 下から上
        for c in range(BOARD_SIZE):  # 列: 左から右
            if self.board[r][c] is not None:
                # "add" 動作を試す（出力抑制）
                fall_count, total_merged_numbers, _ = self.simulate(("add", r, c), max_value=max_value, suppress_output=True)

                # 落下回数が最大の操作
                if fall_count > max_fall_count:
                    max_fall_count = fall_count
                    best_action_by_fall = ("add", "上から", r + 1, "左から", c + 1)

                # 合成した数字の個数が最大の操作
                if total_merged_numbers > max_total_merged_numbers:
                    max_total_merged_numbers = total_merged_numbers
                    best_action_by_merged = ("add", "上から", r + 1, "左から", c + 1)

                # "remove" 動作を試す（出力抑制）
                fall_count, total_merged_numbers, _ = self.simulate(("remove", r, c), max_value=max_value, suppress_output=True)

                # 落下回数が最大の操作
                if fall_count > max_fall_count:
                    max_fall_count = fall_count
                    best_action_by_fall = ("remove", "上から", r + 1, "左から", c + 1)

                # 合成した数字の個数が最大の操作
                if total_merged_numbers > max_total_merged_numbers:
                    max_total_merged_numbers = total_merged_numbers
                    best_action_by_merged = ("remove", "上から", r + 1, "左から", c + 1)

    return best_action_by_fall, max_fall_count, best_action_by_merged, max_total_merged_numbers



# Streamlit アプリの設定
st.title("Merge Game Simulator")
st.write("Enter the board row by row (comma-separated):")

# 行ごとに入力
rows = []
for i in range(BOARD_SIZE):
    row = st.text_input(f"Row {i + 1}:", "8,8,6,5,6")
    rows.append(row)

max_value = st.number_input("Enter max value for merging:", min_value=1, value=20)
simulate_button = st.button("Simulate")

if simulate_button:
    try:
        # 入力された行を解析
        initial_board = [list(map(int, row.split(','))) for row in rows]
        if any(len(row) != BOARD_SIZE for row in initial_board):
            st.error(f"Each row must contain exactly {BOARD_SIZE} numbers.")
        else:
            simulator = MergeGameSimulator(initial_board)
            best_action_by_fall, max_fall_count, best_action_by_merged, max_total_merged_numbers = simulator.find_best_action(max_value=max_value)

            st.write(f"Best action by fall count: {best_action_by_fall}, Max fall count: {max_fall_count}")
            st.write(f"Best action by merged numbers: {best_action_by_merged}, Max merged numbers: {max_total_merged_numbers}")
    except ValueError:
        st.error("Invalid input! Please enter integers separated by commas.")
