import streamlit as st
import copy

# 定数
BOARD_SIZE = 5

class MergeGameSimulator:
    def __init__(self, board):
        self.board = board  # 初期盤面を設定

    def display_board(self, board):
        """盤面をHTMLで表示"""
        st.write("\n".join(" ".join(str(cell) if cell else "." for cell in row) for row in board))
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
        for cluster in clusters:
            values = [board[r][c] for r, c in cluster]
            base_value = values[0]
            new_value = base_value + (len(cluster) - 2)

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

    def apply_gravity(self, board):
        """数字を下に落下させる"""
        for c in range(BOARD_SIZE):
            column = [board[r][c] for r in range(BOARD_SIZE) if board[r][c] is not None]
            # 下から詰めるように修正
            for r in range(BOARD_SIZE - 1, -1, -1):
                board[r][c] = column.pop() if column else None

    def simulate(self, action, max_value=20):
        """1回のユーザー操作をシミュレート"""
        board = copy.deepcopy(self.board)

        st.write("Input board:")
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
        st.write("Initial board:")
        self.display_board(board)

        while True:
            clusters = self.find_clusters(board)
            if not clusters:
                break
            self.merge_clusters(board, clusters, fall_count, user_action=action, max_value=max_value)
            self.apply_gravity(board)
            fall_count += 1

            st.write(f"After fall {fall_count}:")
            self.display_board(board)

        return fall_count, board


# Streamlit アプリの設定
st.title("Merge Game Simulator")
input_data = st.text_input("Enter initial board as a comma-separated string:", "8,8,6,5,6,6,7,8,6,5,9,9,11,5,9,7,8,9,11,8,7,11,8,6,7")
max_value = st.number_input("Enter max value for merging:", min_value=1, value=20)
simulate_button = st.button("Simulate")

if simulate_button:
    input_numbers = list(map(int, input_data.split(',')))
    if len(input_numbers) != BOARD_SIZE * BOARD_SIZE:
        st.error(f"Input must contain exactly {BOARD_SIZE * BOARD_SIZE} numbers.")
    else:
        initial_board = [input_numbers[i:i + BOARD_SIZE] for i in range(0, len(input_numbers), BOARD_SIZE)]
        simulator = MergeGameSimulator(initial_board)
        best_action, max_fall_count = simulator.simulate(("add", 0, 0), max_value=max_value)
        st.write(f"Best action: {best_action}, Max fall count: {max_fall_count}")
